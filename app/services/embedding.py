"""
Lightweight embedding service using TF-IDF-style cosine similarity.
Swap embed() with any real model (sentence-transformers, OpenAI) without
changing the interface — just replace the implementation below.
"""

import math
import re
from typing import List


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def _term_freq(tokens: List[str]) -> dict:
    tf: dict = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    return tf


def embed(text: str) -> List[float]:
    """
    Returns a simple bag-of-words TF vector (fixed 256-dim hash trick).
    Replace this with sentence-transformers or OpenAI for production.
    """
    tokens = _tokenize(text)
    tf = _term_freq(tokens)
    dim = 256
    vec = [0.0] * dim
    for word, count in tf.items():
        idx = hash(word) % dim
        vec[idx] += count
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # both are already L2-normalized
