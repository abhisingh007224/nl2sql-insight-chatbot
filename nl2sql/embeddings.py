"""Embedding model wrapper and the on-disk embedding index."""

import json
from functools import lru_cache

import numpy as np

from .config import EMBEDDING_MODEL, EMBEDDINGS_PATH, INDEX_DIR, INDEX_META_PATH
from .repository import QueryRecord, fingerprint


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed(texts: list[str]) -> np.ndarray:
    """L2-normalised embeddings, so a dot product equals cosine similarity."""
    vectors = get_model().encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vectors.astype(np.float32)


def build_index(repo: dict[str, QueryRecord]) -> int:
    """Embed every description / sample question and save vectors + metadata. Returns the vector count."""
    query_ids, texts = [], []
    for record in repo.values():
        for text in record.index_texts():
            query_ids.append(record.query_id)
            texts.append(text)

    vectors = embed(texts)
    INDEX_DIR.mkdir(exist_ok=True)
    np.save(EMBEDDINGS_PATH, vectors)
    meta = {
        "model": EMBEDDING_MODEL,
        "fingerprint": fingerprint(repo),
        "query_ids": query_ids,
        "texts": texts,
    }
    INDEX_META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return len(texts)


def load_index(repo: dict[str, QueryRecord]) -> tuple[np.ndarray, list[str], list[str]]:
    """Load the saved index, rebuilding it first if missing or out of date with descriptions.csv."""
    meta = None
    if EMBEDDINGS_PATH.exists() and INDEX_META_PATH.exists():
        meta = json.loads(INDEX_META_PATH.read_text(encoding="utf-8"))
    if meta is None or meta["model"] != EMBEDDING_MODEL or meta["fingerprint"] != fingerprint(repo):
        build_index(repo)
        meta = json.loads(INDEX_META_PATH.read_text(encoding="utf-8"))
    return np.load(EMBEDDINGS_PATH), meta["query_ids"], meta["texts"]
