"""Semantic search: match a user question to the closest query in the repository."""

from dataclasses import dataclass

import numpy as np

from .embeddings import embed, get_model, load_index
from .repository import QueryRecord


@dataclass(frozen=True)
class Match:
    query_id: str
    score: float  # cosine similarity in [-1, 1]
    matched_text: str  # the description / sample question that scored highest


class Retriever:
    def __init__(self, repo: dict[str, QueryRecord]):
        self.vectors, self.query_ids, self.texts = load_index(repo)
        get_model()  # load the embedding model up front so the first question isn't slow

    def search(self, question: str, top_k: int = 3) -> list[Match]:
        """Best `top_k` distinct queries; each query is scored by its best-matching text."""
        scores = self.vectors @ embed([question])[0]
        matches: dict[str, Match] = {}
        for i in np.argsort(-scores):
            query_id = self.query_ids[i]
            if query_id not in matches:
                matches[query_id] = Match(query_id, float(scores[i]), self.texts[i])
                if len(matches) == top_k:
                    break
        return list(matches.values())
