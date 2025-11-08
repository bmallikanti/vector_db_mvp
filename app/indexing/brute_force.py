from __future__ import annotations
from typing import List, Tuple
import math
import numpy as np
from .base import Row, Index


def _unit(v: np.ndarray) -> np.ndarray:
    """Normalize vector to unit length."""
    n = float(np.linalg.norm(v))
    return v if n == 0.0 else v / n


def _dot(a: np.ndarray, b: np.ndarray) -> float:
    """Dot product of two vectors."""
    return float(a @ b)


class BruteForceIndex(Index):
    """
    Exact cosine similarity search using NumPy.
    Build  : O(ND)   (normalization)
    Search : O(ND)   (N dot products of length D)
    Space  : O(ND)
    """

    def __init__(self, rows: List[Row]) -> None:
        self.rows = rows
        # store normalized vectors so cosine == dot
        self._vecs: List[np.ndarray] = [_unit(r.embedding.astype(float, copy=False)) for r in rows]
        self._dim = len(self._vecs[0]) if self._vecs else 0

    def search(self, query: np.ndarray, k: int) -> List[Tuple[int, float]]:
        if k <= 0 or not self._vecs:
            return []
        if len(query) != self._dim:
            raise ValueError(f"query dim {len(query)} != index dim {self._dim}")

        q = _unit(query.astype(float, copy=False))
        scores: List[Tuple[int, float]] = []
        for i, v in enumerate(self._vecs):
            s = _dot(v, q)  # cosine similarity (because both are unit)
            scores.append((i, s))

        # top-k: sort by score descending
        scores.sort(key=lambda t: t[1], reverse=True)
        return scores[:min(k, len(scores))]


# Keep the pure Python version for reference/testing
def _l2_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))

def _unit_pure(v: List[float]) -> List[float]:
    n = _l2_norm(v)
    return v if n == 0.0 else [x / n for x in v]

def _dot_pure(a: List[float], b: List[float]) -> float:
    # assumes same length
    return sum(x * y for x, y in zip(a, b))

class BruteForceIndexPure:
    """
    Exact cosine similarity search, implemented without NumPy.
    Build  : O(ND)   (normalization)
    Search : O(ND)   (N dot products of length D)
    Space  : O(ND)
    """

    def __init__(self, rows: List[Row]) -> None:
        self.rows = rows
        # store normalized vectors so cosine == dot
        self._vecs: List[List[float]] = [_unit_pure(r.embedding.tolist()) for r in rows]
        self._dim = len(self._vecs[0]) if self._vecs else 0

    def search(self, query: List[float], k: int) -> List[Tuple[int, float]]:
        if k <= 0 or not self._vecs:
            return []
        if len(query) != self._dim:
            raise ValueError(f"query dim {len(query)} != index dim {self._dim}")

        q = _unit_pure(query)
        scores: List[Tuple[int, float]] = []
        for i, v in enumerate(self._vecs):
            s = _dot_pure(v, q)  # cosine similarity (because both are unit)
            scores.append((i, s))

        # top-k without NumPy: partial selection then sort
        k_eff = min(k, len(scores))
        scores.sort(key=lambda t: t[1], reverse=True)
        return scores[:k_eff]