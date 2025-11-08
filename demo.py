#!/usr/bin/env python3
"""
Comprehensive demo script for the Vector DB system.
Creates libraries, documents, chunks, and demonstrates both direct API and Temporal workflows.
"""

import asyncio
import json
import sys
from uuid import uuid4
from typing import Dict, Any

import httpx
from app.temporal_workflows.client import TemporalQueryClient
from app.temporal_workflows.query_workflow import QueryRequest
from app.adapters.embedding_providers.cohere_provider import CohereProvider


API_BASE = "http://localhost:8000"
TEMPORAL_URL = "localhost:7233"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_step(step_num: int, description: str):
    """Print a formatted step."""
    print(f"Step {step_num}: {description}")


async def check_api_running() -> bool:
    """Check if the API server is running."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/docs", timeout=2.0)
            return response.status_code == 200
    except Exception:
        return False


async def create_library(name: str, description: str = None) -> Dict[str, Any]:
    """Create a library via API."""
    async with httpx.AsyncClient() as client:
        payload = {"name": name}
        if description:
            payload["description"] = description
        
        response = await client.post(
            f"{API_BASE}/vector_db/libraries",
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()


async def create_document(lib_id: str, title: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a document via API."""
    async with httpx.AsyncClient() as client:
        payload = {"title": title}
        if metadata:
            payload["metadata"] = metadata
        
        response = await client.post(
            f"{API_BASE}/vector_db/libraries/{lib_id}/documents",
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()


async def create_chunk(
    lib_id: str,
    doc_id: str,
    text: str,
    embedding: list[float],
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create a chunk via API."""
    async with httpx.AsyncClient() as client:
        payload = {
            "text": text,
            "embedding": embedding
        }
        if metadata:
            payload["metadata"] = metadata
        
        response = await client.post(
            f"{API_BASE}/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()


async def search_direct(
    lib_id: str,
    query_text: str,
    k: int = 5,
    index: str = "brute"
) -> Dict[str, Any]:
    """Search directly via API (non-Temporal) using query text."""
    async with httpx.AsyncClient() as client:
        payload = {
            "query_text": query_text,
            "k": k,
            "index": index
        }
        
        response = await client.post(
            f"{API_BASE}/vector_db/libraries/{lib_id}/search?use_temporal=false",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


async def search_temporal(
    lib_id: str,
    query_text: str,
    k: int = 5,
    index: str = "brute"
) -> Dict[str, Any]:
    """Search via Temporal workflow using query text."""
    client = TemporalQueryClient(temporal_url=TEMPORAL_URL)
    request = QueryRequest(
        lib_id=lib_id,
        query_text=query_text,
        k=k,
        index=index,
    )
    result = await client.execute_query(request)
    return result


async def main():
    """Run the comprehensive demo."""
    print_section("Vector DB Demo")
    
    # Check API is running
    print_step(1, "Checking if API server is running...")
    if not await check_api_running():
        print("❌ ERROR: API server is not running!")
        print("\nPlease start the API server in a separate terminal:")
        print("  source venv/bin/activate")
        print("  uvicorn app.main:app --reload")
        sys.exit(1)
    print("✓ API server is running\n")
    
    # Create library
    print_step(2, "Creating a library...")
    lib = await create_library(
        name="Demo Library",
        description="A demo library for testing vector search"
    )
    lib_id = str(lib["id"])
    print(f"✓ Created library: {lib['name']} (ID: {lib_id})")
    
    # Create document
    print_step(3, "Creating a document...")
    doc = await create_document(
        lib_id=lib_id,
        title="Paris Travel Guide",
        metadata={"category": "travel"}
    )
    doc_id = str(doc["id"])
    print(f"✓ Created document: {doc['title']} (ID: {doc_id})")
    
    # Create chunks with embeddings using Cohere API
    print_step(4, "Creating chunks with Cohere embeddings...")
    
    # Initialize Cohere provider
    try:
        embedder = CohereProvider()
        print("  ✓ Cohere API configured")
    except Exception as e:
        print(f"  ❌ ERROR: Cohere API not configured: {e}")
        print("  Please set COHERE_API_KEY in your .env file")
        sys.exit(1)
    
    chunks_data = [
        {
            "text": "The Louvre Museum is one of the world's largest museums and a historic monument in Paris.",
            "metadata": {"type": "landmark"}
        },
        {
            "text": "Mount Fuji is Japan's tallest peak and an active volcano.",
            "metadata": {"type": "landmark"}
        },
        {
            "text": "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris.",
            "metadata": {"type": "landmark"}
        },
        {
            "text": "Tokyo is the capital and largest city of Japan.",
            "metadata": {"type": "city"}
        },
        {
            "text": "Paris is the capital and most populous city of France.",
            "metadata": {"type": "city"}
        },
    ]
    
    created_chunks = []
    for i, chunk_data in enumerate(chunks_data, 1):
        # Generate embedding using Cohere API
        print(f"  Generating embedding for chunk {i}...", end=" ", flush=True)
        embedding = embedder.embed_text(chunk_data["text"])
        print("✓")
        
        chunk = await create_chunk(
            lib_id=lib_id,
            doc_id=doc_id,
            text=chunk_data["text"],
            embedding=embedding,
            metadata=chunk_data["metadata"]
        )
        created_chunks.append(chunk)
        print(f"  ✓ Created chunk {i}: {chunk_data['text'][:50]}...")
    
    print(f"\n✓ Created {len(created_chunks)} chunks with Cohere embeddings")
    
    # Direct search (non-Temporal) using query text
    print_step(5, "Testing direct search (non-Temporal) with Cohere...")
    query_text = "Paris museums and landmarks"
    direct_results = await search_direct(
        lib_id=lib_id,
        query_text=query_text,
        k=3,
        index="brute"
    )
    print(f"✓ Direct search completed (durable_execution: {direct_results.get('durable_execution', False)})")
    print(f"  Query: '{query_text}'")
    print(f"  Found {len(direct_results.get('hits', []))} results:")
    for i, hit in enumerate(direct_results.get('hits', [])[:3], 1):
        print(f"    {i}. Score: {hit['score']:.4f} - {hit['text'][:60]}...")
    
    # Temporal search using query text
    print_step(6, "Testing Temporal workflow search with Cohere...")
    print("  (Make sure the Temporal worker is running: python -m app.temporal_workflows.worker)")
    try:
        temporal_results = await search_temporal(
            lib_id=lib_id,
            query_text=query_text,
            k=3,
            index="brute"
        )
        print(f"✓ Temporal workflow completed!")
        hits = temporal_results.get('hits', [])
        print(f"  Found {len(hits)} results:")
        for i, hit in enumerate(hits[:3], 1):
            score = hit.get('score', 0) if isinstance(hit, dict) else 0
            text = hit.get('text', 'N/A')[:60] if isinstance(hit, dict) else str(hit)[:60]
            print(f"    {i}. Score: {score:.4f} - {text}...")
    except Exception as e:
        print(f"⚠ Warning: Temporal workflow failed: {e}")
        print("  This is expected if the Temporal worker is not running.")
        print("  Start it with: python -m app.temporal_workflows.worker")
    
    # Summary
    print_section("Demo Complete!")
    print("Summary:")
    print(f"  • Library ID: {lib_id}")
    print(f"  • Document ID: {doc_id}")
    print(f"  • Chunks created: {len(created_chunks)}")
    print(f"  • Direct search: ✓")
    print(f"  • Temporal search: {'✓' if 'temporal_results' in locals() else '⚠ (worker not running)'}")
    print("\nNext steps:")
    print("  1. View Temporal UI: http://localhost:8080")
    print("  2. View API docs: http://localhost:8000/docs")
    print("  3. Start worker: python -m app.temporal_workflows.worker")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

