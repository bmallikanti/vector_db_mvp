from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi import status as http
from typing import List, Optional

from app.models.document import Document
from app.services.document_service import DocumentService
from app.services.library_service import LibraryService

router = APIRouter()
docs = DocumentService()
libs = LibraryService()

@router.get("/{lib_id}/documents", response_model=List[Document])
def list_documents(lib_id: str):
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    res = docs.list_by_library(lib_id)
    return res or []

@router.post("/{lib_id}/documents", response_model=Document, status_code=http.HTTP_201_CREATED)
def add_document(lib_id: str, doc: Document):
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    res = docs.add(lib_id, doc)
    if not res:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    return res

@router.get("/{lib_id}/documents/{doc_id}", response_model=Document)
def get_document(lib_id: str, doc_id: str):
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    d = docs.get(lib_id, doc_id)
    if not d:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    return d

@router.put("/{lib_id}/documents/{doc_id}", response_model=Optional[Document])
def update_document(lib_id: str, doc_id: str, payload: dict):
    """
    Update a document's title and/or metadata.
    Expected payload keys:
    - title: str (optional)
    - metadata: { category?: str } (optional)
    """
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    title = payload.get("title")
    metadata = payload.get("metadata")
    if title is None and not metadata:
        raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="Provide at least one of: title, metadata")
    res = docs.update(lib_id, doc_id, title=title, metadata=metadata)
    if not res:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    return res

@router.delete("/{lib_id}/documents/{doc_id}", status_code=http.HTTP_204_NO_CONTENT)
def delete_document(lib_id: str, doc_id: str):
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    ok = docs.delete(lib_id, doc_id)
    if not ok:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Document not found")
    return None
