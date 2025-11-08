from __future__ import annotations
from typing import Optional, List
from app.models.document import Document
from app.repositories.memory.library_repo import LibraryRepo
from app.repositories.memory.document_repo import DocumentRepo
from app.core.config import settings

# Import Redis repos if enabled
if settings.USE_REDIS:
    from app.repositories.redis.library_repo import LibraryRepoRedis
    from app.repositories.redis.document_repo import DocumentRepoRedis

class DocumentService:
    def __init__(self,
                 libs: LibraryRepo | None = None,
                 docs: DocumentRepo | None = None) -> None:
        if settings.USE_REDIS:
            lib_repo = libs or LibraryRepoRedis.instance(settings.REDIS_URL)
            self.libs = lib_repo
            self.docs = docs or DocumentRepoRedis.instance(lib_repo)
        else:
            self.libs = libs or LibraryRepo.instance()
            self.docs = docs or DocumentRepo.instance()

    def list_by_library(self, lib_id: str) -> Optional[List[Document]]:
        return self.docs.list_by_library(lib_id)

    def add(self, lib_id: str, doc: Document) -> Optional[Document]:
        return self.docs.add(lib_id, doc)

    def get(self, lib_id: str, doc_id: str) -> Optional[Document]:
        return self.docs.get(lib_id, doc_id)

    def delete(self, lib_id: str, doc_id: str) -> bool:
        return self.docs.delete(lib_id, doc_id)
