"""Central paths and settings. Values can be overridden with environment variables or a .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "data" / "northwind.db"
DESCRIPTIONS_PATH = ROOT / "descriptions.csv"
INDEX_DIR = ROOT / "index"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"
INDEX_META_PATH = INDEX_DIR / "index_meta.json"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Vetted queries scoring below this cosine similarity are never used to answer.
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.40"))
# Matches at or above this are used directly. Below it (when an API key is set) Gemini checks whether a
# vetted candidate really answers the question, or writes new read-only SQL.
CONFIDENT_MATCH = float(os.getenv("CONFIDENT_MATCH", "0.90"))
# Any query running longer than this is interrupted; results are capped at this many rows.
QUERY_TIMEOUT_SECONDS = 10
MAX_RESULT_ROWS = 1000
# Maximum number of result rows sent to the LLM.
MAX_ROWS_FOR_LLM = 50


def gemini_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
