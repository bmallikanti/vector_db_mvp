from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any
from uuid import UUID, uuid4
from .metadata import ChunkMetadata

class Chunk(BaseModel):
    """
    Smallest retrieval unit.
    - text: the actual content
    - embedding: optional vector (will be added later if missing)
    - metadata: includes type (optional) + timestamps for filtering
    """
    id: UUID = Field(default_factory=uuid4)
    text: str
    embedding: Optional[List[float]] = None
    metadata: ChunkMetadata = Field(
        default_factory=ChunkMetadata,
        description="Metadata with type (optional) + timestamps"
    )

    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v: Any) -> ChunkMetadata:
        """Ensure metadata is a ChunkMetadata instance."""
        if isinstance(v, dict):
            return ChunkMetadata(**v)
        if isinstance(v, ChunkMetadata):
            return v
        return ChunkMetadata()
