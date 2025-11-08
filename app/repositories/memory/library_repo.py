from __future__ import annotations
from typing import Dict, List, Optional
from copy import deepcopy
from datetime import datetime

from app.models.library import Library
from app.models.metadata import LibraryMetadata
from app.concurrency.read_write_lock import ReadWriteLock


class LibraryRepo:
    """
    In-memory store for libraries with:
      - Global RW lock for the libraries map
      - Per-library RW locks for contained mutations
    """
    _singleton: "LibraryRepo | None" = None

    def __init__(self) -> None:
        self._libs: Dict[str, Library] = {}
        self._global_lock = ReadWriteLock()
        self._lib_locks: Dict[str, ReadWriteLock] = {}

    @classmethod
    def instance(cls) -> "LibraryRepo":
        if not cls._singleton:
            cls._singleton = cls()
        return cls._singleton

    # --------------- locking helpers ---------------
    def _ensure_lib_lock(self, lib_id: str) -> ReadWriteLock:
        if lib_id not in self._lib_locks:
            self._lib_locks[lib_id] = ReadWriteLock()
        return self._lib_locks[lib_id]

    def lib_lock(self, lib_id: str) -> ReadWriteLock:
        # public accessor for other repos
        return self._ensure_lib_lock(lib_id)

    # --------------- CRUD ---------------
    def create(self, lib: Library) -> Library:
        with self._global_lock.write_lock():
            self._libs[str(lib.id)] = lib
            self._ensure_lib_lock(str(lib.id))
        return deepcopy(lib)

    def get(self, lib_id: str) -> Optional[Library]:
        with self._global_lock.read_lock():
            lib = self._libs.get(lib_id)
            return deepcopy(lib) if lib else None

    def list(self) -> List[Library]:
        with self._global_lock.read_lock():
            return deepcopy(list(self._libs.values()))

    def update(self, lib_id: str, name: str, description: Optional[str], metadata: dict) -> Optional[Library]:
        with self._global_lock.write_lock():
            lib = self._libs.get(lib_id)
            if not lib:
                return None
            lib.name = name
            lib.description = description
            # Update metadata, preserving created_at if it exists
            if isinstance(metadata, dict):
                if isinstance(lib.metadata, LibraryMetadata):
                    # Merge with existing metadata
                    existing_dict = lib.metadata.model_dump()
                    existing_dict.update(metadata)
                    existing_dict["updated_at"] = datetime.utcnow()
                    lib.metadata = LibraryMetadata(**existing_dict)
                else:
                    lib.metadata = LibraryMetadata(**metadata)
            lib.metadata.update_timestamp()
            lib.version += 1
            return deepcopy(lib)

    def delete(self, lib_id: str) -> bool:
        with self._global_lock.write_lock():
            if lib_id in self._libs:
                del self._libs[lib_id]
                self._lib_locks.pop(lib_id, None)
                return True
            return False
