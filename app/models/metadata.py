"""
Metadata models for Library, Document, and Chunk.
Simplified - minimal fields for easier testing and maintenance.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BaseMetadata(BaseModel):
    """
    Base metadata with timestamps.
    All metadata classes inherit from this.
    """
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class LibraryMetadata(BaseMetadata):
    """
    Library metadata - simplified to 1 field.
    Field:
    - tags: Tags/categories for the library (comma-separated string or list)
    """
    tags: Optional[str] = Field(default=None, description="Tags/categories (comma-separated)")
    
    # Strict validation - no extra fields allowed
    model_config = {"extra": "forbid"}


class DocumentMetadata(BaseMetadata):
    """
    Document metadata - simplified to 1 field.
    Field:
    - category: Document category/type
    """
    category: Optional[str] = Field(default=None, description="Document category/type")
    
    # Strict validation - no extra fields allowed
    model_config = {"extra": "forbid"}


class ChunkMetadata(BaseMetadata):
    """
    Chunk metadata - simplified to 1 field.
    Field:
    - type: Chunk type (e.g., "paragraph", "heading", "list")
    """
    type: Optional[str] = Field(default=None, description="Chunk type (e.g., 'paragraph', 'heading')")
    
    # Strict validation - no extra fields allowed
    model_config = {"extra": "forbid"}


