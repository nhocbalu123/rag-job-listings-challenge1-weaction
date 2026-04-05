"""
Embedding service using BGE-M3 via FlagEmbedding.
"""

import os
from typing import List
from FlagEmbedding import BGEM3FlagModel

_model = None

def get_model():
    global _model
    if _model is None:
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
        # use_fp16=False is usually faster and safer on CPU
        _model = BGEM3FlagModel(model_name, use_fp16=False)
    return _model

def embed(text: str) -> List[float]:
    """
    Returns a 1024-dim vector using BGE-M3.
    """
    model = get_model()
    # BGE-M3 encode returns a dict with 'dense_vecs'
    output = model.encode([text], return_dense=True, return_sparse=False, return_colbert_vecs=False)
    vec = output['dense_vecs'][0]
    return vec.tolist()

def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # both are already L2-normalized by the model
