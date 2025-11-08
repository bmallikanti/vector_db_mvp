from __future__ import annotations
from typing import List, Tuple, Dict
import math
import random
import numpy as np

from .base import Row, Index


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v if n == 0.0 else v / n


def _dot(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b)  # dot product


class LSHIndex(Index):
    """
    Random-hyperplane LSH for cosine similarity.
    - Build: sample T tables, each with P random hyperplanes in R^D
    - Hash: sign(dot(v, plane)) -> bit; concat P bits -> bucket key
    - Store: map[key] = list of row indices
    - Query: hash(q) in each table -> union candidates -> rank by cosine

    Space:  O(N·T) for buckets + O(T·P·D) for planes
    Build:  O(N·T·P·D)  (hash every row across T tables, P planes)
    Query:  O(C·D)  (C = candidates from matched buckets), usually C << N
    """
    def __init__(self, rows: List[Row], num_tables: int = 8, num_planes: int = 12, seed: int = 42) -> None:
        self.rows = rows
        self.N = len(rows)
        self.D = len(rows[0].embedding) if rows else 0
        self.T = num_tables
        self.P = num_planes
        rng = random.Random(seed)

        # Pre-normalize embeddings so cosine == dot
        self._vecs = [_unit(r.embedding.astype(float, copy=False)) for r in rows]

        # Generate random hyperplanes (T tables × P planes each)
        # planes[t][p] is a np.ndarray of shape (D,)
        self.planes: List[List[np.ndarray]] = []
        for _ in range(self.T):
            table_planes = []
            for _ in range(self.P):
                # Gaussian random hyperplane
                vec = np.array([rng.gauss(0.0, 1.0) for _ in range(self.D)], dtype=float)
                vec = _unit(vec)
                table_planes.append(vec)
            self.planes.append(table_planes)

        # Buckets per table: List[Dict[key, List[idx]]]
        self.tables: List[Dict[int, List[int]]] = [dict() for _ in range(self.T)]
        self._build()

    def _hash(self, v: np.ndarray, planes: List[np.ndarray]) -> int:
        # Build a P-bit integer by thresholding the dot with each plane
        code = 0
        for i, p in enumerate(planes):
            bit = 1 if _dot(v, p) >= 0.0 else 0
            code |= (bit << i)
        return code

    def _build(self) -> None:
        for idx, v in enumerate(self._vecs):
            for t in range(self.T):
                key = self._hash(v, self.planes[t])
                bucket = self.tables[t].setdefault(key, [])
                bucket.append(idx)

    def search(self, query: np.ndarray, k: int) -> List[Tuple[int, float]]:
        if k <= 0 or self.N == 0:
            return []

        q = _unit(query.astype(float, copy=False))
        cand: set[int] = set()

        # Collect candidates from all tables
        for t in range(self.T):
            key = self._hash(q, self.planes[t])
            cand.update(self.tables[t].get(key, []))

        if not cand:
            return []

        # Score candidates by cosine (dot on unit vectors)
        scored: List[Tuple[int, float]] = []
        for i in cand:
            s = _dot(self._vecs[i], q)
            scored.append((i, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: min(k, len(scored))]
