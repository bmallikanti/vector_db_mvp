from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi import status as http
from typing import List, Optional

from app.models.library import Library
from app.services.library_service import LibraryService

router = APIRouter()
svc = LibraryService()

@router.post("", response_model=Library, status_code=http.HTTP_201_CREATED)
def create_library(lib: Library):
    # Allow client to POST minimal data (e.g., name only). Pydantic will fill defaults.
    return svc.create(lib)

@router.get("", response_model=List[Library])
def list_libraries():
    return svc.list()

@router.get("/{lib_id}", response_model=Library)
def get_library(lib_id: str):
    lib = svc.get(lib_id)
    if not lib:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    return lib

class LibraryUpdatePayload(Library.model_construct().__class__):  # quick typed shell
    pass

@router.put("/{lib_id}", response_model=Optional[Library])
def update_library(lib_id: str, payload: dict):
    # Expect keys: name, description, metadata
    name = payload.get("name")
    if not name:
        raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="name is required")
    lib = svc.update(lib_id, name=name, description=payload.get("description"), metadata=payload.get("metadata", {}))
    if not lib:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    return lib

@router.delete("/{lib_id}", status_code=http.HTTP_204_NO_CONTENT)
def delete_library(lib_id: str):
    ok = svc.delete(lib_id)
    if not ok:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")
    return None
