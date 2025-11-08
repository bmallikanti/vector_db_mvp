from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi import status as http
import asyncio

from app.services.search_service import SearchService
from app.services.library_service import LibraryService
from app.temporal_workflows.client import TemporalQueryClient
from app.temporal_workflows.query_workflow import QueryRequest

router = APIRouter()
svc = SearchService()
libs = LibraryService()
temporal_client = TemporalQueryClient()

@router.post("/{lib_id}/search")
async def search(
    lib_id: str,
    body: Dict[str, Any],
    use_temporal: bool = Query(False, description="Use Temporal for durable execution"),
):
    """
    Search endpoint with optional Temporal durable execution.
    
    Request JSON:
    {
      "query_text": "string" | null,
      "query_embedding": [float, ...] | null,
      "k": 5,
      "index": "brute" | "lsh",
      "lsh_tables": 8,
      "lsh_planes": 12,
      "filters": {"key": "value"} | null  # Optional metadata filters (exact match)
    }
    
    Query params:
    - use_temporal: If true, execute via Temporal workflow (durable execution)
    """
    if not libs.get(lib_id):
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail="Library not found")

    query_text = body.get("query_text")
    query_embedding = body.get("query_embedding")
    k = int(body.get("k", 5))
    index = body.get("index", "brute")
    lsh_tables = int(body.get("lsh_tables", 8))
    lsh_planes = int(body.get("lsh_planes", 12))
    filters = body.get("filters")

    if not query_text and not query_embedding:
        raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="Provide query_text or query_embedding")

    try:
        if use_temporal:
            # Execute via Temporal workflow (durable execution)
            request = QueryRequest(
                lib_id=lib_id,
                query_text=query_text,
                query_embedding=query_embedding,
                k=k,
                index=index,
                lsh_tables=lsh_tables,
                lsh_planes=lsh_planes,
                filters=filters,
            )
            result = await temporal_client.execute_query(request)
            return {
                "hits": result.hits,
                "index": result.index,
                "library_version": result.library_version,
                "execution_metadata": result.metadata,
                "durable_execution": True,
            }
        else:
            # Direct execution (non-durable)
            res = svc.search(
                lib_id,
                query_text=query_text,
                query_embedding=query_embedding,
                k=k,
                index=index,
                lsh_tables=lsh_tables,
                lsh_planes=lsh_planes,
                filters=filters,
            )
            return {**res, "durable_execution": False}
    except ValueError as e:
        raise HTTPException(http.HTTP_400_BAD_REQUEST, detail=str(e))
