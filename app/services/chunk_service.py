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
