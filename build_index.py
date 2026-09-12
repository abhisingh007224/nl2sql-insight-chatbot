"""Embedding / indexing script: embeds every query description and sample question once, offline.

Usage:  uv run python build_index.py
"""

from nl2sql.config import EMBEDDING_MODEL, EMBEDDINGS_PATH
from nl2sql.embeddings import build_index
from nl2sql.repository import load_repository


def main() -> None:
    repo = load_repository()
    count = build_index(repo)
    print(f"Embedded {count} texts for {len(repo)} queries with {EMBEDDING_MODEL}")
    print(f"Saved index to {EMBEDDINGS_PATH.parent}")


if __name__ == "__main__":
    main()
