"""
Interactive Temporal workflow with signals/queries.
Allows creating libraries/documents/chunks (with Cohere embeddings),
then running repeated searches with adjustable params. Pauses 3s after each action.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow, activity


# =========================
# Dataclasses (workflow IO)
# =========================

@dataclass
class InteractiveState:
    current_step: str = "SETUP_LIBRARIES"
    created_library_ids: List[str] = field(default_factory=list)
    created_document_ids_by_library: Dict[str, List[str]] = field(default_factory=dict)
    # New: richer mappings for interactive CLI display
    created_libraries_by_id: Dict[str, str] = field(default_factory=dict)  # lib_id -> name
    created_document_titles_by_library: Dict[str, Dict[str, str]] = field(default_factory=dict)  # lib_id -> {doc_id -> title}
    created_chunk_counts_by_doc: Dict[str, int] = field(default_factory=dict)
    # Observed chunk metadata keys/values per library for filter suggestions
    chunk_metadata_catalog_by_library: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    active_library_id: Optional[str] = None
    active_document_id: Optional[str] = None
    query_params: Dict[str, Any] = field(default_factory=lambda: {"k": 5, "index": "brute", "filters": None})
    last_results: Dict[str, Any] = field(default_factory=dict)
    timeline: List[str] = field(default_factory=list)
    finished: bool = False


# ===============
# Activities
# ===============

@activity.defn(name="interactive_create_library")
async def interactive_create_library_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.library_service import LibraryService
    from app.models.library import Library

    libs = LibraryService()
    name = (payload or {}).get("name")
    if not name:
        raise ValueError("name is required")
    description = (payload or {}).get("description")
    lib = Library(name=name, description=description)
    lib = libs.create(lib)
    return {"id": str(lib.id), "name": lib.name, "description": lib.description}


@activity.defn(name="interactive_create_document")
async def interactive_create_document_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.document_service import DocumentService
    from app.services.library_service import LibraryService
    from app.models.document import Document
    from app.models.metadata import DocumentMetadata

    libs = LibraryService()
    lib_id = (payload or {}).get("lib_id")
    title = (payload or {}).get("title")
    metadata: Optional[Dict[str, Any]] = (payload or {}).get("metadata")
    if not lib_id or not title:
        raise ValueError("lib_id and title are required")
    if not libs.get(lib_id):
        raise ValueError("Library not found")

    docs = DocumentService()
    doc = Document(title=str(title))
    if metadata:
        # Map allowed fields only
        if "category" in metadata:
            doc.metadata.category = metadata["category"]
    res = docs.add(str(lib_id), doc)
    if not res:
        raise ValueError("Failed adding document")
    return {"id": str(res.id), "title": res.title}


@activity.defn(name="interactive_create_chunk")
async def interactive_create_chunk_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.document_service import DocumentService
    from app.services.library_service import LibraryService
    from app.services.chunk_service import ChunkService
    from app.adapters.embedding_providers.cohere_provider import CohereProvider
    from app.models.chunk import Chunk
    from app.models.metadata import ChunkMetadata

    libs = LibraryService()
    lib_id = (payload or {}).get("lib_id")
    doc_id = (payload or {}).get("doc_id")
    text = (payload or {}).get("text")
    metadata: Optional[Dict[str, Any]] = (payload or {}).get("metadata")
    if not lib_id or not doc_id or not text:
        raise ValueError("lib_id, doc_id and text are required")
    if not libs.get(lib_id):
        raise ValueError("Library not found")
    docs = DocumentService()
    if not docs.get(lib_id, doc_id):
        raise ValueError("Document not found")

    embedder = CohereProvider()
    embedding = embedder.embed_text(str(text))

    chunks = ChunkService()
    chunk = Chunk(text=str(text), embedding=embedding)
    if metadata:
        if "type" in metadata:
            chunk.metadata.type = metadata["type"]
    res = chunks.add(str(lib_id), str(doc_id), chunk)
    if not res:
        raise ValueError("Failed adding chunk")
    return {"id": str(res.id), "text": res.text}


@activity.defn(name="interactive_search")
async def interactive_search_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.search_service import SearchService

    lib_id = (payload or {}).get("lib_id")
    query_text: Optional[str] = (payload or {}).get("query_text")
    query_embedding: Optional[List[float]] = (payload or {}).get("query_embedding")
    k = int((payload or {}).get("k"))
    index = (payload or {}).get("index")
    lsh_tables = int((payload or {}).get("lsh_tables"))
    lsh_planes = int((payload or {}).get("lsh_planes"))
    filters: Optional[Dict[str, Any]] = (payload or {}).get("filters")
    if not lib_id:
        raise ValueError("lib_id is required")
    svc = SearchService()
    result = svc.search(
        lib_id=str(lib_id),
        query_text=query_text,
        query_embedding=query_embedding,
        k=k,
        index=index,
        lsh_tables=lsh_tables,
        lsh_planes=lsh_planes,
        filters=filters,
    )
    return result


# ===============================
# Workflow with signals & queries
# ===============================

@workflow.defn(name="InteractiveDBWorkflow")
class InteractiveDBWorkflow:
    def __init__(self) -> None:
        self.state = InteractiveState()
        self._pending_action: Optional[str] = None
        self._pending_payload: Dict[str, Any] = {}
        self._new_action: bool = False

    # ---------- Signals ----------
    @workflow.signal
    def add_library(self, payload: Dict[str, Any]) -> None:
        # expects: {"name": str, "description": Optional[str]}
        self._queue_action("add_library", payload or {})

    @workflow.signal
    def add_document(self, payload: Dict[str, Any]) -> None:
        # expects: {"lib_id": str, "title": str, "metadata": Optional[dict]}
        self._queue_action("add_document", payload or {})

    @workflow.signal
    def add_chunk(self, payload: Dict[str, Any]) -> None:
        # expects: {"lib_id": str, "doc_id": str, "text": str, "metadata": Optional[dict]}
        self._queue_action("add_chunk", payload or {})

    @workflow.signal
    def set_query_params(self, payload: Dict[str, Any]) -> None:
        # expects: {"k": int, "index": str, "filters": Optional[dict]}
        self._queue_action("set_query_params", payload or {})

    @workflow.signal
    def start_query(self, payload: Dict[str, Any]) -> None:
        # expects: {"lib_id": str, "query_text": Optional[str], "query_embedding": Optional[List[float]]}
        self._queue_action("start_query", payload or {})


    @workflow.signal
    def cancel_query(self) -> None:
        # For simplicity, we mark finished. Advanced: separate cancel current query vs whole workflow.
        self._queue_action("cancel", {})

    @workflow.signal
    def finish(self) -> None:
        self._queue_action("finish", {})

    # ---------- Queries ----------
    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        return {
            "current_step": self.state.current_step,
            "active_library_id": self.state.active_library_id,
            "active_document_id": self.state.active_document_id,
            "created_library_ids": list(self.state.created_library_ids),
            "created_document_ids_by_library": dict(self.state.created_document_ids_by_library),
            # Expose richer maps for nicer CLI prompts
            "created_libraries_by_id": dict(self.state.created_libraries_by_id),
            "created_document_titles_by_library": {
                k: dict(v) for k, v in self.state.created_document_titles_by_library.items()
            },
            "created_chunk_counts_by_doc": dict(self.state.created_chunk_counts_by_doc),
            "chunk_metadata_catalog_by_library": {
                lib: {k: list(v) for k, v in cat.items()} for lib, cat in self.state.chunk_metadata_catalog_by_library.items()
            },
            "query_params": dict(self.state.query_params),
            "finished": self.state.finished,
            "timeline_tail": self.state.timeline[-10:],
        }

    @workflow.query
    def get_partial_results(self) -> Dict[str, Any]:
        return dict(self.state.last_results or {})

    # ---------- Helpers ----------
    def _queue_action(self, action: str, payload: Dict[str, Any]) -> None:
        # overwrite previous pending action to keep control simple
        self._pending_action = action
        self._pending_payload = payload
        self._new_action = True

    # ---------- Main run ----------
    @workflow.run
    async def run(self) -> None:
        # Initial step
        self.state.timeline.append("Workflow started. Waiting for user actions...")
        while not self.state.finished:
            await workflow.wait_condition(lambda: self._new_action or self.state.finished)
            if self.state.finished:
                break

            action = self._pending_action
            payload = self._pending_payload
            # reset marker
            self._new_action = False
            self._pending_action = None
            self._pending_payload = {}

            try:
                if action == "add_library":
                    created = await workflow.execute_activity(
                        interactive_create_library_activity,
                        payload,
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    lib_id = created["id"]
                    lib_name = created.get("name")
                    self.state.created_library_ids.append(lib_id)
                    self.state.active_library_id = lib_id
                    if lib_name:
                        self.state.created_libraries_by_id[lib_id] = lib_name
                    self.state.current_step = "SETUP_DOCUMENTS"
                    self.state.timeline.append(f"Library created: {lib_id}{' (' + lib_name + ')' if lib_name else ''}")

                elif action == "add_document":
                    created = await workflow.execute_activity(
                        interactive_create_document_activity,
                        payload,
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    doc_id = created["id"]
                    doc_title = created.get("title")
                    lib_id = payload["lib_id"]
                    self.state.created_document_ids_by_library.setdefault(lib_id, []).append(doc_id)
                    if doc_title:
                        self.state.created_document_titles_by_library.setdefault(lib_id, {})[doc_id] = doc_title
                    self.state.active_document_id = doc_id
                    self.state.current_step = "SETUP_CHUNKS"
                    self.state.timeline.append(
                        f"Document created: {doc_id}{' (' + doc_title + ')' if doc_title else ''} in library {lib_id}"
                    )

                elif action == "add_chunk":
                    res = await workflow.execute_activity(
                        interactive_create_chunk_activity,
                        payload,
                        start_to_close_timeout=timedelta(seconds=60),
                    )
                    doc_id = payload["doc_id"]
                    self.state.created_chunk_counts_by_doc[doc_id] = self.state.created_chunk_counts_by_doc.get(doc_id, 0) + 1
                    # Record observed metadata keys/values for filter suggestions
                    lib_id = payload.get("lib_id")
                    meta = payload.get("metadata") or {}
                    if lib_id and isinstance(meta, dict):
                        cat = self.state.chunk_metadata_catalog_by_library.setdefault(lib_id, {})
                        for mk, mv in meta.items():
                            try:
                                sval = str(mv)
                            except Exception:
                                sval = repr(mv)
                            values = cat.setdefault(mk, [])
                            if sval not in values:
                                # keep small sample of distinct values
                                if len(values) < 20:
                                    values.append(sval)
                    self.state.timeline.append(f"Chunk created: {res['id']} for document {doc_id}")
                    self.state.current_step = "READY_TO_QUERY"

                elif action == "set_query_params":
                    self.state.query_params.update({
                        "k": int(payload["k"]),
                        "index": payload["index"],
                        "filters": payload.get("filters"),
                    })
                    self.state.timeline.append(f"Query params set: {self.state.query_params}")
                    self.state.current_step = "READY_TO_QUERY"

                elif action == "start_query":
                    qp = self.state.query_params
                    # merge default params into payload
                    search_payload = {
                        "lib_id": payload.get("lib_id"),
                        "query_text": payload.get("query_text"),
                        "query_embedding": payload.get("query_embedding"),
                        "k": int(qp.get("k", 5)),
                        "index": qp.get("index", "brute"),
                        "lsh_tables": 8,
                        "lsh_planes": 12,
                        "filters": qp.get("filters"),
                    }
                    search_results = await workflow.execute_activity(
                        interactive_search_activity,
                        search_payload,
                        start_to_close_timeout=timedelta(seconds=60),
                    )
                    # Optional reranking step using shared activity from query workflow
                    try:
                        from app.temporal_workflows.query_workflow import rerank_results_activity  # local import is safe
                        ranked_hits = await workflow.execute_activity(
                            rerank_results_activity,
                            args=[search_results.get("hits", []), search_payload.get("query_text")],
                            start_to_close_timeout=timedelta(seconds=30),
                        )
                    except Exception:
                        ranked_hits = search_results.get("hits", [])

                    # Ensure we respect k (just in case reranker returns more)
                    top_k = int(qp.get("k", 5))
                    if isinstance(ranked_hits, list):
                        ranked_hits = ranked_hits[:top_k]

                    self.state.last_results = {
                        "durable_execution": True,
                        **{k: v for k, v in search_results.items() if k != "hits"},
                        "hits": ranked_hits,
                        "reranked": True,
                    }
                    self.state.timeline.append("Search executed.")
                    self.state.current_step = "READY_TO_QUERY"

                # 'proceed' step removed; progression now happens naturally via actions

                elif action == "cancel":
                    self.state.timeline.append("Cancel received. Finishing workflow.")
                    self.state.finished = True

                elif action == "finish":
                    self.state.timeline.append("Finish received. Closing workflow.")
                    self.state.finished = True

                # Pause 3 seconds after every processed action
                await workflow.sleep(timedelta(seconds=3))

            except Exception as e:
                # Record failure in timeline; keep workflow alive to allow correction via signals
                self.state.timeline.append(f"Error processing action '{action}': {e!r}")
                # short pause to avoid tight loop on repeated errors
                await workflow.sleep(timedelta(seconds=3))
