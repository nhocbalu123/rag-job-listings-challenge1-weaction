"""
Reranker service using bge-reranker-v2-m3 via FlagEmbedding.

Pairs naturally with the BGE-M3 embedder and runs on CPU.
Used in the two-stage retrieval pipeline:
  embed-search (top RETRIEVAL_K) → rerank → top_k
"""

import os
from threading import Lock
from typing import List

from FlagEmbedding import FlagReranker

_reranker = None
_reranker_lock = Lock()


def get_reranker() -> FlagReranker:
    """Thread-safe lazy singleton for the reranker model."""
    global _reranker
    if _reranker is None:                        # first check — no lock cost on hot path
        with _reranker_lock:
            if _reranker is None:                # second check — only one thread loads
                model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
                # use_fp16=True is safe for reranking (scoring only, no storage)
                _reranker = FlagReranker(model_name, use_fp16=True)
    return _reranker


def rerank(query: str, jobs, top_n: int = 5) -> List:
    """
    Score each job against the query and return the top_n by relevance.

    Args:
        query: The user's search query.
        jobs:  Iterable of JobListing ORM objects (must have .title and .description).
        top_n: Number of results to return after reranking.

    Returns:
        List of JobListing objects sorted by descending reranker score, length <= top_n.
    """
    if not jobs:
        return []

    reranker = get_reranker()
    pairs = [[query, f"{j.title} {j.description}"] for j in jobs]
    scores = reranker.compute_score(pairs, normalize=True)

    # scores may be a single float when len(jobs)==1; normalise to list
    if isinstance(scores, float):
        scores = [scores]

    ranked = sorted(zip(scores, jobs), key=lambda x: x[0], reverse=True)
    return [job for _, job in ranked[:top_n]]
