"""
Redis-based repository for documents.
Documents are stored nested within libraries in Redis.
"""

from __future__ import annotations
from typing import List, Optional
from copy import deepcopy
from datetime import datetime
import json

from app.models.document import Document
from app.repositories.redis.library_repo import LibraryRepoRedis


class DocumentRepoRedis:
    """
    Redis-based store for documents.
    Documents are stored nested within libraries.
    """
    _singleton: "DocumentRepoRedis | None" = None

    def __init__(self, libs: LibraryRepoRedis) -> None:
        self.libs = libs

    @classmethod
    def instance(cls, libs: LibraryRepoRedis | None = None) -> "DocumentRepoRedis":
        if not cls._singleton:
            cls._singleton = cls(libs or LibraryRepoRedis.instance())
        return cls._singleton

    def list_by_library(self, lib_id: str) -> Optional[List[Document]]:
        lib = self.libs.get(lib_id)
        if not lib:
            return None
        return deepcopy(lib.documents)

    def add(self, lib_id: str, doc: Document) -> Optional[Document]:
        lock = self.libs.lib_lock(lib_id)
        with lock.write_lock():
            lib = self.libs.get(lib_id)
            if not lib:
                return None
            
            lib.documents.append(doc)
            lib.metadata.update_timestamp()
            lib.version += 1
            
            # Save back to Redis
            lib_dict = lib.model_dump(mode='json')
            key = self.libs._key(lib_id)
            self.libs.redis_client.set(key, json.dumps(lib_dict))
            
            return deepcopy(doc)

    def get(self, lib_id: str, doc_id: str) -> Optional[Document]:
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
            lib = self.libs.get(lib_id)
            if not lib:
                return False
            
            before = len(lib.documents)
            lib.documents = [d for d in lib.documents if str(d.id) != doc_id]
            
            if len(lib.documents) != before:
                lib.metadata.update_timestamp()
                lib.version += 1
                
                # Save back to Redis
                lib_dict = lib.model_dump(mode='json')
                key = self.libs._key(lib_id)
                self.libs.redis_client.set(key, json.dumps(lib_dict))
                return True
            return False

