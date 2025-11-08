from __future__ import annotations
from typing import Optional, List
from app.models.chunk import Chunk
from app.repositories.memory.library_repo import LibraryRepo
from app.repositories.memory.chunk_repo import ChunkRepo

class ChunkService:
    def __init__(self,
                 libs: LibraryRepo | None = None,
                 chunks: ChunkRepo | None = None) -> None:
        self.libs = libs or LibraryRepo.instance()
        self.chunks = chunks or ChunkRepo.instance()

    def list_by_document(self, lib_id: str, doc_id: str) -> Optional[List[Chunk]]:
        return self.chunks.list_by_document(lib_id, doc_id)

    def add(self, lib_id: str, doc_id: str, chunk: Chunk) -> Optional[Chunk]:
        return self.chunks.add(lib_id, doc_id, chunk)

    def delete(self, lib_id: str, doc_id: str, chunk_id: str) -> bool:
        return self.chunks.delete(lib_id, doc_id, chunk_id)

    def update(
        self,
        lib_id: str,
        doc_id: str,
        chunk_id: str,
        *,
        text: str | None,
        embedding: list[float] | None,
        metadata: dict | None,
        reembed_if_needed: bool = True,
    ) -> Optional[Chunk]:
        """
        Update a chunk. If text changes and embedding not provided, optionally re-embed via Cohere.
        """
        final_embedding = embedding
        if text is not None and embedding is None and reembed_if_needed:
            try:
                from app.adapters.embedding_providers.cohere_provider import CohereProvider
                embedder = CohereProvider()
                final_embedding = embedder.embed_text(text)
            except Exception:
                # Proceed without embedding change if Cohere not configured
                final_embedding = None
        return self.chunks.update(
            lib_id, doc_id, chunk_id, text=text, embedding=final_embedding, metadata=metadata
        )
