"""
Temporal workflows and activities for durable query execution.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from temporalio import workflow, activity
from datetime import timedelta

# Don't import services/models at workflow level - they use non-deterministic functions
# Import them only inside activities


# ============================================================================
# Data Classes for Workflow Input/Output
# ============================================================================

@dataclass
class QueryRequest:
    """Input for query workflow."""
    lib_id: str
    query_text: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    k: int = 5
    index: str = "brute"
    lsh_tables: int = 8
    lsh_planes: int = 12
    filters: Optional[Dict[str, Any]] = None


@dataclass
class QueryResponse:
    """Output from query workflow."""
    hits: List[Dict[str, Any]]
    index: str
    library_version: Optional[int]
    metadata: Dict[str, Any]  # execution metadata


# ============================================================================
# Activities - Individual units of work
# ============================================================================

@activity.defn(name="setup_test_data")
async def setup_test_data_activity(lib_id: str) -> Dict[str, Any]:
    """
    Activity: Create test data in the worker process.
    This ensures data exists in the same process as the worker.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔧 Setup activity: Creating test data for library {lib_id}")
    
    # Import here to avoid workflow sandbox restrictions
    from app.models.library import Library
    from app.models.document import Document
    from app.models.chunk import Chunk
    from app.services.library_service import LibraryService
    from app.services.document_service import DocumentService
    from app.services.chunk_service import ChunkService
    from uuid import UUID, uuid4
    
    libs = LibraryService()
    docs = DocumentService()
    chunks = ChunkService()
    
    # Check if library exists and has chunks
    existing_lib = libs.get(lib_id)
    if existing_lib:
        chunks_count = sum(len(d.chunks) for d in existing_lib.documents)
        if chunks_count > 0:
            logger.info(f"✓ Library {lib_id} already exists with {chunks_count} chunks")
            return {
                "created": False,
                "lib_id": lib_id,
                "message": "Library already exists with chunks",
                "chunks_count": chunks_count,
            }
        else:
            logger.info(f"✓ Library {lib_id} exists but has no chunks, creating chunks...")
            # Use first document or create one
            if existing_lib.documents:
                doc = existing_lib.documents[0]
            else:
                doc = docs.add(str(existing_lib.id), Document(title="Test Doc"))
                logger.info(f"✓ Created document: {doc.id}")
            
            # Generate embeddings using Cohere API
            from app.adapters.embedding_providers.cohere_provider import CohereProvider
            try:
                embedder = CohereProvider()
                embedding1 = embedder.embed_text("Paris is beautiful")
                embedding2 = embedder.embed_text("Tokyo is amazing")
                logger.info("✓ Generated embeddings using Cohere API")
            except Exception as e:
                logger.error(f"❌ Cohere API not available: {e}")
                raise ValueError(
                    "Cohere API key required. Please set COHERE_API_KEY in your .env file. "
                    "The setup activity needs Cohere to generate embeddings."
                )
            
            # Add chunks with embeddings
            chunk1 = chunks.add(str(existing_lib.id), str(doc.id),
                      Chunk(text="Paris is beautiful", embedding=embedding1,
                           metadata={"type": "paragraph"}))
            chunk2 = chunks.add(str(existing_lib.id), str(doc.id),
                      Chunk(text="Tokyo is amazing", embedding=embedding2,
                           metadata={"type": "paragraph"}))
            
            logger.info(f"✓ Created 2 chunks for existing library")
            return {
                "created": True,
                "lib_id": str(existing_lib.id),
                "message": "Added chunks to existing library",
                "chunks_count": 2,
            }
    
    # Create test library - handle both UUID and string IDs
    lib = Library(name="Temporal Demo")
    
    # Try to parse as UUID, if fails, generate a new UUID
    try:
        lib.id = UUID(lib_id)
        logger.info(f"✓ Using provided UUID: {lib_id}")
    except ValueError:
        # If lib_id is not a valid UUID, generate one but use lib_id as lookup key
        lib.id = uuid4()
        logger.info(f"✓ Generated new UUID: {lib.id} (from non-UUID input: {lib_id})")
        # Store with the provided lib_id as key for lookup
        lib_id = str(lib.id)  # Use the generated UUID
    
    # Create library using service (in-memory demo)
    lib = libs.create(lib)
    
    doc = docs.add(str(lib.id), Document(title="Test Doc"))
    logger.info(f"✓ Created document: {doc.id}")
    
    # Generate embeddings using Cohere API
    from app.adapters.embedding_providers.cohere_provider import CohereProvider
    try:
        embedder = CohereProvider()
        embedding1 = embedder.embed_text("Paris is beautiful")
        embedding2 = embedder.embed_text("Tokyo is amazing")
        logger.info("✓ Generated embeddings using Cohere API")
    except Exception as e:
        logger.error(f"❌ Cohere API not available: {e}")
        raise ValueError(
            "Cohere API key required. Please set COHERE_API_KEY in your .env file. "
            "The setup activity needs Cohere to generate embeddings."
        )
    
    # Add chunks with embeddings (using Cohere)
    chunk1 = chunks.add(str(lib.id), str(doc.id),
              Chunk(text="Paris is beautiful", embedding=embedding1,
                   metadata={"type": "paragraph"}))
    chunk2 = chunks.add(str(lib.id), str(doc.id),
              Chunk(text="Tokyo is amazing", embedding=embedding2,
                   metadata={"type": "paragraph"}))
    
    logger.info(f"✓ Created 2 chunks: '{chunk1.text}' and '{chunk2.text}'")
    
    return {
        "created": True,
        "lib_id": str(lib.id),
        "message": "Test data created",
        "chunks_count": 2,
    }


@activity.defn(name="validate_query")
async def validate_query_activity(request: QueryRequest) -> Dict[str, Any]:
    """
    Activity: Validate and preprocess query input.
    Returns validation result and preprocessed data.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"✓ Validate activity: lib_id={request.lib_id}, k={request.k}, index={request.index}")
    
    if not request.query_text and not request.query_embedding:
        raise ValueError("Must provide query_text or query_embedding")
    
    if request.k <= 0:
        raise ValueError("k must be positive")
    
    if request.index not in ["brute", "lsh"]:
        raise ValueError("index must be 'brute' or 'lsh'")
    
    return {
        "valid": True,
        "lib_id": request.lib_id,
        "has_text": request.query_text is not None,
        "has_embedding": request.query_embedding is not None,
    }


@activity.defn(name="generate_embedding")
async def generate_embedding_activity(query_text: str) -> List[float]:
    """
    Activity: Generate embedding from query text using Cohere.
    """
    # Import here to avoid workflow sandbox restrictions
    from app.adapters.embedding_providers.cohere_provider import CohereProvider
    
    embedder = CohereProvider()
    embedding = embedder.embed_text(query_text)
    return embedding


@activity.defn(name="search_vectors")
async def search_vectors_activity(
    lib_id: str,
    query_embedding: List[float],
    k: int,
    index: str,
    lsh_tables: int,
    lsh_planes: int,
    filters: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Activity: Perform vector search over the library.
    Uses in-memory repositories (singleton pattern).
    Note: Data must exist in the worker process's memory.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Search activity: lib_id={lib_id}, k={k}, index={index}, dim={len(query_embedding)}")
    
    # Import here to avoid workflow sandbox restrictions
    from app.services.search_service import SearchService
    
    search_service = SearchService()
    results = search_service.search(
        lib_id=lib_id,
        query_embedding=query_embedding,
        k=k,
        index=index,
        lsh_tables=lsh_tables,
        lsh_planes=lsh_planes,
        filters=filters,
    )
    
    logger.info(f"✓ Search found {len(results.get('hits', []))} hits")
    return results


@activity.defn(name="rerank_results")
async def rerank_results_activity(
    hits: List[Dict[str, Any]],
    query_text: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Activity: Rerank results (optional post-processing).
    For now, just returns hits as-is. Can add reranking logic later.
    """
    # Placeholder for reranking logic
    # Could add semantic reranking, boosting by metadata, etc.
    return hits


# ============================================================================
# Workflow - Orchestrates the query execution
# ============================================================================

@workflow.defn(name="QueryWorkflow")
class QueryWorkflow:
    """
    Durable workflow that orchestrates query execution:
    1. Setup test data (optional, for demo)
    2. Validate query
    3. Generate embedding (if needed)
    4. Search vectors
    5. Rerank results (optional)
    """

    @workflow.run
    async def run(self, request: QueryRequest) -> QueryResponse:
        """
        Main workflow execution.
        """
        # Step 0: Setup test data (ensures data exists in worker process)
        # This is optional - only for demo/testing. In production, data would exist already.
        setup_result = await workflow.execute_activity(
            setup_test_data_activity,
            request.lib_id,
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        # Update lib_id if setup generated a new UUID
        actual_lib_id = setup_result.get("lib_id", request.lib_id)
        
        # Step 1: Validate query
        validation_result = await workflow.execute_activity(
            validate_query_activity,
            request,
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        # Step 2: Generate embedding if needed
        query_embedding = request.query_embedding
        if request.query_text and not query_embedding:
            query_embedding = await workflow.execute_activity(
                generate_embedding_activity,
                request.query_text,
                start_to_close_timeout=timedelta(seconds=30),
            )
        
        # Step 3: Search vectors (use actual_lib_id)
        search_results = await workflow.execute_activity(
            search_vectors_activity,
            args=[
                actual_lib_id,
                query_embedding,
                request.k,
                request.index,
                request.lsh_tables,
                request.lsh_planes,
                request.filters,
            ],
            start_to_close_timeout=timedelta(seconds=60),
        )
        
        # Step 4: Rerank results (optional)
        hits = await workflow.execute_activity(
            rerank_results_activity,
            args=[search_results["hits"], request.query_text],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        return QueryResponse(
            hits=hits,
            index=search_results["index"],
            library_version=search_results.get("library_version"),
            metadata={
                "setup": setup_result,
                "validation": validation_result,
                "embedding_generated": request.query_text is not None and request.query_embedding is None,
            },
        )
    
    @workflow.query(name="get_status")
    def get_status(self) -> Dict[str, str]:
        """
        Query: Get current workflow status.
        Note: This is a simplified version. For full status tracking,
        you'd need to use workflow state variables properly.
        """
        return {
            "status": "running",
            "current_step": "processing",
        }
    
    @workflow.signal(name="cancel_query")
    def cancel_query(self) -> None:
        """
        Signal: Cancel the query execution.
        Note: This is a placeholder. Full cancellation would require
        workflow state management.
        """
        pass

