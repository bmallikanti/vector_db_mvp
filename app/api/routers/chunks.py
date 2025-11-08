from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi import status as http
from typing import List

from app.models.chunk import Chunk
from app.services.chunk_service import ChunkService
from app.services.document_service import DocumentService
from app.services.library_service import LibraryService

router = APIRouter()
chunks = ChunkService()
docs = DocumentService()
libs = LibraryService()

@router.get("/{lib_id}/documents/{doc_id}/chunks", response_model=List[Chunk])
def list_chunks(lib_id: str, doc_id: str):
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    if not docs.get(lib_id, doc_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    res = chunks.list_by_document(lib_id, doc_id)
    return res or []

@router.post("/{lib_id}/documents/{doc_id}/chunks", response_model=Chunk, status_code=http.HTTP_201_CREATED)
def add_chunk(lib_id: str, doc_id: str, chunk: Chunk):
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    if not docs.get(lib_id, doc_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    res = chunks.add(lib_id, doc_id, chunk)
    if not res:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    return res

@router.put("/{lib_id}/documents/{doc_id}/chunks/{chunk_id}", response_model=Chunk)
def update_chunk(lib_id: str, doc_id: str, chunk_id: str, payload: dict):
    """
    Update a chunk.
    Payload keys (all optional, at least one required):
    - text: str
    - embedding: List[float]
    - metadata: { type?: str }
    Behavior: if text is provided and embedding omitted, server will re-embed via Cohere (if configured).
    """
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    if not docs.get(lib_id, doc_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    text = payload.get("text")
    embedding = payload.get("embedding")
    metadata = payload.get("metadata")
    if text is None and embedding is None and not metadata:
        raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="Provide at least one of: text, embedding, metadata")
    res = chunks.update(
        lib_id, doc_id, chunk_id, text=text, embedding=embedding, metadata=metadata, reembed_if_needed=True
    )
    if not res:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Chunk not found")
    return res

@router.delete("/{lib_id}/documents/{doc_id}/chunks/{chunk_id}", status_code=http.HTTP_204_NO_CONTENT)
def delete_chunk(lib_id: str, doc_id: str, chunk_id: str):
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    if not docs.get(lib_id, doc_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    ok = chunks.delete(lib_id, doc_id, chunk_id)
    if not ok:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Chunk not found")
    return None
