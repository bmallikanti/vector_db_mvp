from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any
from uuid import UUID, uuid4
from .document import Document
from .metadata import LibraryMetadata


class Library(BaseModel):
    """
    Top-level container for documents (and by extension, chunks).
    'version' increments on any write in this library (doc/chunk changes),
    which helps search/index layers know if cached indexes are stale.
    
    Metadata field: tags (optional)
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    metadata: LibraryMetadata = Field(
        default_factory=LibraryMetadata,
        description="Metadata with tags (optional) + timestamps"
    )
    documents: List[Document] = Field(default_factory=list)
    version: int = 0

    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v: Any) -> LibraryMetadata:
        """Ensure metadata is a LibraryMetadata instance."""
        if isinstance(v, dict):
            return LibraryMetadata(**v)
        if isinstance(v, LibraryMetadata):
            return v
        return LibraryMetadata()
