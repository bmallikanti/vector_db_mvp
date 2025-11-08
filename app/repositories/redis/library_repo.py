"""
Redis-based repository for persistent storage.
Uses Redis to store libraries, documents, and chunks.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from copy import deepcopy
from datetime import datetime
import json
import redis

from app.models.library import Library
from app.models.metadata import LibraryMetadata
from app.concurrency.read_write_lock import ReadWriteLock


class LibraryRepoRedis:
    """
    Redis-based store for libraries with persistence.
    Data survives worker restarts!
    """
    _singleton: "LibraryRepoRedis | None" = None

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        self._global_lock = ReadWriteLock()
        self._lib_locks: Dict[str, ReadWriteLock] = {}
        self._key_prefix = "vector_db:library:"

    @classmethod
    def instance(cls, redis_url: str = "redis://localhost:6379/0") -> "LibraryRepoRedis":
        if not cls._singleton:
            cls._singleton = cls(redis_url)
        return cls._singleton

    def _ensure_lib_lock(self, lib_id: str) -> ReadWriteLock:
        if lib_id not in self._lib_locks:
            self._lib_locks[lib_id] = ReadWriteLock()
        return self._lib_locks[lib_id]

    def lib_lock(self, lib_id: str) -> ReadWriteLock:
        return self._ensure_lib_lock(lib_id)

    def _key(self, lib_id: str) -> str:
        return f"{self._key_prefix}{lib_id}"

    def create(self, lib: Library) -> Library:
        with self._global_lock.write_lock():
            key = self._key(str(lib.id))
            # Check if exists
            if self.redis_client.exists(key):
                return deepcopy(lib)
            
            # Serialize and store
            lib_dict = lib.model_dump(mode='json')
            self.redis_client.set(key, json.dumps(lib_dict))
            self._ensure_lib_lock(str(lib.id))
        return deepcopy(lib)

    def get(self, lib_id: str) -> Optional[Library]:
        with self._global_lock.read_lock():
            key = self._key(lib_id)
            data = self.redis_client.get(key)
            if not data:
                return None
            lib_dict = json.loads(data)
            return Library(**lib_dict)

    def list(self) -> List[Library]:
        with self._global_lock.read_lock():
            keys = self.redis_client.keys(f"{self._key_prefix}*")
            libs = []
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    lib_dict = json.loads(data)
                    libs.append(Library(**lib_dict))
            return libs

    def update(self, lib_id: str, name: str, description: Optional[str], metadata: dict) -> Optional[Library]:
        with self._global_lock.write_lock():
            key = self._key(lib_id)
            data = self.redis_client.get(key)
            if not data:
                return None
            
            lib_dict = json.loads(data)
            lib = Library(**lib_dict)
            lib.name = name
            lib.description = description
            
            if isinstance(metadata, dict):
                if isinstance(lib.metadata, LibraryMetadata):
                    existing_dict = lib.metadata.model_dump()
                    existing_dict.update(metadata)
                    existing_dict["updated_at"] = datetime.utcnow().isoformat()
                    lib.metadata = LibraryMetadata(**existing_dict)
                else:
                    lib.metadata = LibraryMetadata(**metadata)
            lib.metadata.update_timestamp()
            lib.version += 1
            
            # Save back to Redis
            lib_dict = lib.model_dump(mode='json')
            self.redis_client.set(key, json.dumps(lib_dict))
            return deepcopy(lib)

    def delete(self, lib_id: str) -> bool:
        with self._global_lock.write_lock():
            key = self._key(lib_id)
            deleted = self.redis_client.delete(key)
            self._lib_locks.pop(lib_id, None)
            return deleted > 0

