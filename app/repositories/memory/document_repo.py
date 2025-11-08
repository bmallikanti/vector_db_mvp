from __future__ import annotations
from typing import List, Optional
from copy import deepcopy
from datetime import datetime

from app.models.document import Document
from app.repositories.memory.library_repo import LibraryRepo


class DocumentRepo:
    _singleton: "DocumentRepo | None" = None

    def __init__(self, libs: LibraryRepo) -> None:
        self.libs = libs

    @classmethod
    def instance(cls) -> "DocumentRepo":
        if not cls._singleton:
            cls._singleton = cls(LibraryRepo.instance())
        return cls._singleton

    # --------- CRUD within a library ----------
    def list_by_library(self, lib_id: str) -> Optional[List[Document]]:
        # structural read: safe to take global read lock through LibraryRepo.get
        lib = self.libs.get(lib_id)
        if not lib:
            return None
        return deepcopy(lib.documents)

    def add(self, lib_id: str, doc: Document) -> Optional[Document]:
        lock = self.libs.lib_lock(lib_id)
        with lock.write_lock():
            lib = LibraryRepo.instance()._libs.get(lib_id)  # protected by per-lib lock
            if not lib:
                return None
            lib.documents.append(doc)
            lib.metadata.update_timestamp()
            lib.version += 1
            return deepcopy(doc)

    def get(self, lib_id: str, doc_id: str) -> Optional[Document]:
        # read-safe via global read then deep copy
        lib = self.libs.get(lib_id)
        if not lib:
            return None
        for d in lib.documents:
            if str(d.id) == doc_id:
                return deepcopy(d)
        return None

    def delete(self, lib_id: str, doc_id: str) -> bool:
        lock = self.libs.lib_lock(lib_id)
        with lock.write_lock():
            lib = LibraryRepo.instance()._libs.get(lib_id)
            if not lib:
                return False
            before = len(lib.documents)
            lib.documents = [d for d in lib.documents if str(d.id) != doc_id]
            if len(lib.documents) != before:
                lib.metadata.update_timestamp()
                lib.version += 1
                return True
            return False
