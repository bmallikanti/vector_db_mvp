from __future__ import annotations
from typing import List, Optional
from copy import deepcopy
from datetime import datetime

from app.models.chunk import Chunk
from app.repositories.memory.library_repo import LibraryRepo


class ChunkRepo:
    _singleton: "ChunkRepo | None" = None

    def __init__(self, libs: LibraryRepo) -> None:
        self.libs = libs

    @classmethod
    def instance(cls) -> "ChunkRepo":
        if not cls._singleton:
            cls._singleton = cls(LibraryRepo.instance())
        return cls._singleton

    # We keep signatures explicit with lib_id + doc_id for O(n_docs) → O(1) per-lib search
    def list_by_document(self, lib_id: str, doc_id: str) -> Optional[List[Chunk]]:
        lib = self.libs.get(lib_id)
        if not lib:
            return None
        for d in lib.documents:
            if str(d.id) == doc_id:
                return deepcopy(d.chunks)
        return None

    def add(self, lib_id: str, doc_id: str, chunk: Chunk) -> Optional[Chunk]:
        lock = self.libs.lib_lock(lib_id)
        with lock.write_lock():
            lib = LibraryRepo.instance()._libs.get(lib_id)
            if not lib:
                return None
            for d in lib.documents:
                if str(d.id) == doc_id:
                    d.chunks.append(chunk)
                    d.metadata.update_timestamp()
                    lib.metadata.update_timestamp()
                    lib.version += 1
                    return deepcopy(chunk)
            return None

    def delete(self, lib_id: str, doc_id: str, chunk_id: str) -> bool:
        lock = self.libs.lib_lock(lib_id)
        with lock.write_lock():
            lib = LibraryRepo.instance()._libs.get(lib_id)
            if not lib:
                return False
            for d in lib.documents:
                if str(d.id) == doc_id:
                    before = len(d.chunks)
                    d.chunks = [c for c in d.chunks if str(c.id) != chunk_id]
                    if len(d.chunks) != before:
                        d.metadata.update_timestamp()
                        lib.metadata.update_timestamp()
                        lib.version += 1
                        return True
        return False

    def update(
        self,
        lib_id: str,
        doc_id: str,
        chunk_id: str,
        *,
        text: str | None,
        embedding: list[float] | None,
        metadata: dict | None,
    ) -> Optional[Chunk]:
        """
        Update chunk text, embedding, and/or metadata.type.
        """
        lock = self.libs.lib_lock(lib_id)
        with lock.write_lock():
            lib = LibraryRepo.instance()._libs.get(lib_id)
            if not lib:
                return None
            for d in lib.documents:
                if str(d.id) == doc_id:
                    for c in d.chunks:
                        if str(c.id) == chunk_id:
                            if text is not None:
                                c.text = text
                            if embedding is not None:
                                c.embedding = embedding
                            if metadata:
                                t = metadata.get("type")
                                if t is not None:
                                    c.metadata.type = t
                            d.metadata.update_timestamp()
                            lib.metadata.update_timestamp()
                            lib.version += 1
                            return deepcopy(c)
        return None
