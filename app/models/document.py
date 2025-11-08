from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Any
from uuid import UUID, uuid4
from .chunk import Chunk
from .metadata import DocumentMetadata

class Document(BaseModel):
    """
    A logical document that contains chunks.
    We store chunks here for simplicity; repos/services will manage them.
    
    Metadata field: category (optional)
    """
    id: UUID = Field(default_factory=uuid4)
    title: str
    metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata,
        description="Metadata with category (optional) + timestamps"
    )
    chunks: List[Chunk] = Field(default_factory=list)

    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v: Any) -> DocumentMetadata:
        """Ensure metadata is a DocumentMetadata instance."""
        if isinstance(v, dict):
            return DocumentMetadata(**v)
        if isinstance(v, DocumentMetadata):
            return v
        return DocumentMetadata()
