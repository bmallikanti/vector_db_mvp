from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Protocol, List, Tuple
import numpy as np


@dataclass(frozen=True)
class Row:
    """
    A searchable record representing a chunk (and its parents) with its embedding.
    Used internally by indexes for vector math — lightweight for speed.
    """
    chunk_id: str
    document_id: str
    library_id: str
    text: str
    metadata: Dict[str, Any]
    embedding: np.ndarray


class Index(Protocol):
    """
    Interface for all vector indexes.
    Implementations must support `search(query, k)` returning top-k (row_index, score) pairs.
    """
    def search(self, query: np.ndarray, k: int) -> List[Tuple[int, float]]:
        ...
