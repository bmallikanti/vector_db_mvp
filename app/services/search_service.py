from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.models.library import Library
from app.repositories.memory.library_repo import LibraryRepo
from app.repositories.memory.document_repo import DocumentRepo
from app.repositories.memory.chunk_repo import ChunkRepo

from app.indexing.base import Row
from app.indexing.brute_force import BruteForceIndex
from app.indexing.lsh import LSHIndex
from app.adapters.embedding_providers.cohere_provider import CohereProvider


class SearchService:
    """
    Orchestrates building searchable rows from a library, embedding the query,
    picking an index (brute|lsh), and returning top-k hits.
    """

    def __init__(
        self,
        libs: Optional[LibraryRepo] = None,
        docs: Optional[DocumentRepo] = None,
        chunks: Optional[ChunkRepo] = None,
        embedder: Optional[CohereProvider] = None,
    ) -> None:
        self.libs = libs or LibraryRepo.instance()
        self.docs = docs or DocumentRepo.instance()
        self.chunks = chunks or ChunkRepo.instance()
        self.embedder = embedder or CohereProvider()

    def _collect_rows(self, lib_id: str, dim_hint: Optional[int] = None) -> List[Row]:
        lib = self.libs.get(lib_id)
        if not lib:
            return []

        rows: List[Row] = []
        for d in lib.documents:
            for c in d.chunks:
                # Use stored embedding if present; otherwise skip for now.
                if c.embedding is None:
                    # For minimalism, we do NOT mutate repo state here; we just skip.
                    # (If you want auto-embed-on-read, call self.embedder here and use the vector without saving.)
                    continue
                vec = np.array(c.embedding, dtype=float)
                # Convert metadata to dict if it's a BaseMetadata object
                metadata_dict = c.metadata.to_dict() if hasattr(c.metadata, 'to_dict') else c.metadata
                rows.append(
                    Row(
                        chunk_id=str(c.id),
                        document_id=str(d.id),
                        library_id=str(lib.id),
                        text=c.text,
                        metadata=metadata_dict,
                        embedding=vec,
                    )
                )
        return rows

    def _apply_metadata_filters(self, rows: List[Row], filters: Optional[Dict[str, Any]]) -> List[Row]:
        """
        Filter rows by metadata using exact match.
        Example: filters={"type": "museum", "landmark": "Louvre"} 
        will only return rows where metadata matches ALL specified fields.
        """
        if not filters:
            return rows
        
        filtered = []
        for row in rows:
            match = True
            for key, value in filters.items():
                if row.metadata.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(row)
        
        return filtered

    def search(
        self,
        lib_id: str,
        *,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        k: int = 5,
        index: str = "brute",  # "brute" | "lsh"
        lsh_tables: int = 8,
        lsh_planes: int = 12,
        filters: Optional[Dict[str, Any]] = None,  # Optional metadata filters (exact match)
    ) -> Dict[str, Any]:
        if k <= 0:
            return {"hits": [], "index": index, "library_version": self.libs.get(lib_id).version if self.libs.get(lib_id) else None}

        # 1) Build dataset rows (only chunks that already have embeddings)
        rows = self._collect_rows(lib_id)
        
        # 2) Apply metadata filters if provided
        if filters:
            rows = self._apply_metadata_filters(rows, filters)
        
        if not rows:
            return {"hits": [], "index": index, "library_version": self.libs.get(lib_id).version if self.libs.get(lib_id) else None}

        dim = len(rows[0].embedding)

        # 3) Build/derive query vector
        if query_embedding is not None:
            q = np.array(query_embedding, dtype=float)
        elif query_text is not None:
            q = np.array(self.embedder.embed_text(query_text, dim=dim), dtype=float)
        else:
            raise ValueError("Provide either query_text or query_embedding")

        # 4) Choose index and search
        if index == "brute":
            idx = BruteForceIndex(rows)
        elif index == "lsh":
            idx = LSHIndex(rows, num_tables=lsh_tables, num_planes=lsh_planes)
        else:
            raise ValueError("index must be 'brute' or 'lsh'")

        hits = idx.search(q, k)

        # 5) Pack results
        packed = []
        for row_idx, score in hits:
            r = rows[row_idx]
            packed.append(
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "library_id": r.library_id,
                    "text": r.text,
                    "metadata": r.metadata,
                    "score": score,
                }
            )

        lib = self.libs.get(lib_id)
        return {"hits": packed, "index": index, "library_version": (lib.version if lib else None)}
