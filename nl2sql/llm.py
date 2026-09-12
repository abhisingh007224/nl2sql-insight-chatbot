"""Thin Gemini client shared by answer generation and the SQL planner."""

import re
import time
from functools import lru_cache

from .config import GEMINI_MODEL, gemini_api_key

# Wait and retry automatically when Gemini asks us to back off for at most this long.
MAX_RATE_LIMIT_WAIT_SECONDS = 10


class LLMRateLimitError(RuntimeError):
    """Gemini quota exhausted (the free tier allows only a few requests per minute)."""


def llm_available(api_key: str | None = None) -> bool:
    return bool(api_key or gemini_api_key())


@lru_cache(maxsize=2)
def _client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def _retry_delay(exc: Exception) -> float | None:
    match = re.search(r"retry in ([\d.]+)s", str(exc))
    return float(match.group(1)) if match else None


def ask_gemini(system_prompt: str, prompt: str, attempts: int = 3, api_key: str | None = None) -> str:
    """`api_key` overrides the app-wide key (e.g. a visitor's own key); defaults to GEMINI_API_KEY."""
    from google.genai import errors, types

    api_key = api_key or gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    for attempt in range(attempts):
        try:
            response = _client(api_key).models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.0),
            )
            return (response.text or "").strip()
        except errors.ServerError:  # 5xx, e.g. 503 "model is experiencing high demand" - usually transient
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
        except errors.ClientError as exc:
            if getattr(exc, "code", None) != 429:
                raise
            delay = _retry_delay(exc)
            if attempt < attempts - 1 and delay is not None and delay <= MAX_RATE_LIMIT_WAIT_SECONDS:
                time.sleep(delay + 0.5)
                continue
            wait = f", try again in about {round(delay)}s" if delay else ""
            raise LLMRateLimitError(f"Gemini free-tier rate limit reached{wait}") from None
    return ""


def verify_api_key(api_key: str) -> str | None:
    """Check a key with a cheap model-list call (no generation quota used). Returns None if valid, else a reason."""
    from google.genai import errors

    try:
        next(iter(_client(api_key).models.list(config={"page_size": 1})), None)
    except errors.ClientError as exc:
        if exc.code == 429:  # authenticated fine, just rate limited
            return None
        if exc.code in (400, 401, 403):
            return "the key is not valid or has no access to the Gemini API"
        return f"Gemini returned {exc.code} {exc.status}"
    except Exception as exc:  # network problems etc.
        return f"could not reach Gemini ({exc.__class__.__name__})"
    return None
