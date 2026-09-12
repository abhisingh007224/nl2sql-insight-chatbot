"""Thin Gemini client shared by answer generation and the SQL planner."""

import re
import time
from functools import lru_cache

from .config import GEMINI_MODEL, gemini_api_key

# Wait and retry automatically when Gemini asks us to back off for at most this long.
MAX_RATE_LIMIT_WAIT_SECONDS = 10


class LLMRateLimitError(RuntimeError):
    """Gemini quota exhausted (the free tier allows only a few requests per minute)."""


def llm_available() -> bool:
    return bool(gemini_api_key())


@lru_cache(maxsize=2)
def _client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def _retry_delay(exc: Exception) -> float | None:
    match = re.search(r"retry in ([\d.]+)s", str(exc))
    return float(match.group(1)) if match else None


def ask_gemini(system_prompt: str, prompt: str, attempts: int = 3) -> str:
    from google.genai import errors, types

    api_key = gemini_api_key()
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
