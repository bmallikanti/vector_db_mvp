"""
Redis-based repository for chunks.
Chunks are stored nested within documents within libraries in Redis.
"""

from __future__ import annotations
from typing import List, Optional
from copy import deepcopy
from datetime import datetime
import json

from app.models.chunk import Chunk
from app.repositories.redis.library_repo import LibraryRepoRedis


class ChunkRepoRedis:
    """
    Redis-based store for chunks.
    Chunks are stored nested within documents within libraries.
    """
    _singleton: "ChunkRepoRedis | None" = None

    def __init__(self, libs: LibraryRepoRedis) -> None:
        self.libs = libs

    @classmethod
    def instance(cls, libs: LibraryRepoRedis | None = None) -> "ChunkRepoRedis":
        if not cls._singleton:
            cls._singleton = cls(libs or LibraryRepoRedis.instance())
        return cls._singleton

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
            lib = self.libs.get(lib_id)
            if not lib:
                return None
            
            for d in lib.documents:
                if str(d.id) == doc_id:
                    d.chunks.append(chunk)
                    d.metadata.update_timestamp()
                    lib.metadata.update_timestamp()
                    lib.version += 1
                    
                    # Save back to Redis
                    lib_dict = lib.model_dump(mode='json')
                    key = self.libs._key(lib_id)
                    self.libs.redis_client.set(key, json.dumps(lib_dict))
                    
                    return deepcopy(chunk)
            return None

    def delete(self, lib_id: str, doc_id: str, chunk_id: str) -> bool:
        lock = self.libs.lib_lock(lib_id)
        with lock.write_lock():
            lib = self.libs.get(lib_id)
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
                        
                        # Save back to Redis
                        lib_dict = lib.model_dump(mode='json')
                        key = self.libs._key(lib_id)
                        self.libs.redis_client.set(key, json.dumps(lib_dict))
                        return True
            return False

