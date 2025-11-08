from fastapi import FastAPI
from app.api.routers.libraries import router as libraries_router
from app.api.routers.documents import router as documents_router
from app.api.routers.chunks import router as chunks_router
from app.api.routers.search import router as search_router

app = FastAPI(title="Vector DB (CRUD)")

app.include_router(libraries_router, prefix="/vector_db/libraries", tags=["libraries"])
app.include_router(documents_router, prefix="/vector_db/libraries", tags=["documents"])
app.include_router(chunks_router, prefix="/vector_db/libraries", tags=["chunks"])
app.include_router(search_router, prefix="/vector_db/libraries", tags=["search"])
