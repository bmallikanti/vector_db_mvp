from __future__ import annotations
from typing import Any, Dict, Optional
import os
from fastapi import APIRouter, HTTPException
from fastapi import status as http

from temporalio.client import Client

from app.temporal_workflows.client import TASK_QUEUE  # reuse same queue

router = APIRouter()


async def get_temporal_client() -> Client:
    # Allow env override when running in Docker: TEMPORAL_ADDRESS=temporal:7233
    temporal_url = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    return await Client.connect(temporal_url)


@router.post("/start", status_code=http.HTTP_202_ACCEPTED)
async def start_interactive_workflow() -> Dict[str, Any]:
    """
    Start a long-running interactive workflow session.
    Returns workflow_id and run_id.
    """
    from uuid import uuid4
    try:
        temporal_url = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
        client = await get_temporal_client()
        handle = await client.start_workflow(
            "InteractiveDBWorkflow",
            id=f"interactive-session-{uuid4()}",
            task_queue=TASK_QUEUE,
        )
        # Safely try to include run_id and status, but don't fail if unavailable
        try:
            info = await handle.describe()
            run_id = getattr(info, "run_id", None)
            if run_id is None:
                exec_obj = getattr(info, "execution", None)
                run_id = getattr(exec_obj, "run_id", None) if exec_obj else None
            return {"workflow_id": handle.id, "run_id": run_id, "status": str(info.status)}
        except Exception:
            # Some SDK versions/servers may not support describe fields uniformly
            return {"workflow_id": handle.id}
    except Exception as e:
        error_msg = str(e)
        # Provide more helpful error messages
        if "connection" in error_msg.lower() or "refused" in error_msg.lower():
            temporal_url = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
            error_msg = f"Cannot connect to Temporal server at {temporal_url}. Make sure Temporal is running (e.g., via docker-compose up). Original error: {error_msg}"
        raise HTTPException(http.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)


@router.get("/{workflow_id}/status")
async def get_status(workflow_id: str) -> Dict[str, Any]:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        status = await handle.query("get_status")
        return status
    except Exception as e:
        # If workflow not found or query missing, surface as 404
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{workflow_id}/results")
async def get_results(workflow_id: str) -> Dict[str, Any]:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        res = await handle.query("get_partial_results")
        return res
    except Exception as e:
        raise HTTPException(http.HTTP_404_NOT_FOUND, detail=str(e))


# -----------------
# Signal endpoints
# -----------------

@router.post("/{workflow_id}/signal/add_library", status_code=http.HTTP_202_ACCEPTED)
async def signal_add_library(workflow_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        name = body.get("name")
        if not name or not str(name).strip():
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="name is required")
        description = body.get("description")
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("add_library", {"name": name, "description": description})
        return {"accepted": True, "message": "add_library signaled"}
    except HTTPException:
        raise
    except Exception as e:
        # Map Temporal errors to 404/400 where reasonable; default 500
        msg = str(e)
        code = http.HTTP_404_NOT_FOUND if "not found" in msg.lower() else http.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(code, detail=msg)


@router.post("/{workflow_id}/signal/add_document", status_code=http.HTTP_202_ACCEPTED)
async def signal_add_document(workflow_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        lib_id = body.get("lib_id")
        title = body.get("title")
        if not lib_id or not title:
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="lib_id and title are required")
        metadata = body.get("metadata")
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("add_document", {"lib_id": lib_id, "title": title, "metadata": metadata})
        return {"accepted": True, "message": "add_document signaled"}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        code = http.HTTP_404_NOT_FOUND if "not found" in msg.lower() else http.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(code, detail=msg)


@router.post("/{workflow_id}/signal/add_chunk", status_code=http.HTTP_202_ACCEPTED)
async def signal_add_chunk(workflow_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        lib_id = body.get("lib_id")
        doc_id = body.get("doc_id")
        text = body.get("text")
        if not lib_id or not doc_id or not text:
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="lib_id, doc_id and text are required")
        metadata = body.get("metadata")
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("add_chunk", {"lib_id": lib_id, "doc_id": doc_id, "text": text, "metadata": metadata})
        return {"accepted": True, "message": "add_chunk signaled"}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        code = http.HTTP_404_NOT_FOUND if "not found" in msg.lower() else http.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(code, detail=msg)


@router.post("/{workflow_id}/signal/set_query_params", status_code=http.HTTP_202_ACCEPTED)
async def signal_set_query_params(workflow_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        try:
            k = int(body.get("k", 5))
        except Exception:
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="k must be integer")
        index = body.get("index", "brute")
        filters = body.get("filters")
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("set_query_params", {"k": k, "index": index, "filters": filters})
        return {"accepted": True, "message": "set_query_params signaled"}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        code = http.HTTP_404_NOT_FOUND if "not found" in msg.lower() else http.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(code, detail=msg)


@router.post("/{workflow_id}/signal/start_query", status_code=http.HTTP_202_ACCEPTED)
async def signal_start_query(workflow_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        lib_id = body.get("lib_id")
        if not lib_id:
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="lib_id is required")
        query_text = body.get("query_text")
        query_embedding = body.get("query_embedding")
        if not query_text and not query_embedding:
            raise HTTPException(http.HTTP_400_BAD_REQUEST, detail="Provide query_text or query_embedding")
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("start_query", {"lib_id": lib_id, "query_text": query_text, "query_embedding": query_embedding})
        return {"accepted": True, "message": "start_query signaled"}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        code = http.HTTP_404_NOT_FOUND if "not found" in msg.lower() else http.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(code, detail=msg)


# 'proceed' signal removed (step advances naturally via actions)


@router.post("/{workflow_id}/signal/cancel", status_code=http.HTTP_202_ACCEPTED)
async def signal_cancel(workflow_id: str) -> Dict[str, Any]:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        try:
            await handle.signal("cancel_query")
            return {"accepted": True, "message": "cancel signaled"}
        except Exception as e:
            # If workflow already finished/closed, treat cancel as idempotent success
            msg_l = str(e).lower()
            if any(x in msg_l for x in ["already", "completed", "closed", "not running", "terminated"]):
                return {"accepted": True, "message": "workflow already closed"}
            if "not found" in msg_l or "unknown workflow" in msg_l:
                raise HTTPException(http.HTTP_404_NOT_FOUND, detail=str(e))
            raise
    except Exception as e:
        raise HTTPException(http.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{workflow_id}/signal/finish", status_code=http.HTTP_202_ACCEPTED)
async def signal_finish(workflow_id: str) -> Dict[str, Any]:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        try:
            await handle.signal("finish")
            return {"accepted": True, "message": "finish signaled"}
        except Exception as e:
            msg_l = str(e).lower()
            if any(x in msg_l for x in ["already", "completed", "closed", "not running", "terminated"]):
                return {"accepted": True, "message": "workflow already closed"}
            if "not found" in msg_l or "unknown workflow" in msg_l:
                raise HTTPException(http.HTTP_404_NOT_FOUND, detail=str(e))
            raise
    except Exception as e:
        raise HTTPException(http.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
