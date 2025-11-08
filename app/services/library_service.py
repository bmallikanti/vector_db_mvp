from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from copy import deepcopy

from app.models.library import Library
from app.repositories.memory.library_repo import LibraryRepo

class LibraryService:
    def __init__(self, libs: LibraryRepo | None = None) -> None:
        self.libs = libs or LibraryRepo.instance()

    def create(self, lib: Library) -> Library:
        return self.libs.create(lib)

    def get(self, lib_id: str) -> Optional[Library]:
        return self.libs.get(lib_id)

    def list(self) -> List[Library]:
        return self.libs.list()

    def update(self, lib_id: str, name: str, description: str | None, metadata: dict) -> Optional[Library]:
        return self.libs.update(lib_id, name, description, metadata)

    def delete(self, lib_id: str) -> bool:
        return self.libs.delete(lib_id)
