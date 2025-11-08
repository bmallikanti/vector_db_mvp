#!/usr/bin/env python3
"""
Simple test script to verify the system works end-to-end.
"""

import asyncio
import sys
from uuid import uuid4
from app.temporal_workflows.client import TemporalQueryClient
from app.temporal_workflows.query_workflow import QueryRequest
from app.core.config import settings


async def test_system():
    print("=" * 70)
    print("SYSTEM TEST")
    print("=" * 70)
    print()
    
    print("Configuration:")
    print(f"  USE_REDIS: {settings.USE_REDIS}")
    print(f"  REDIS_URL: {settings.REDIS_URL}")
    print()
    
    lib_id = str(uuid4())
    print(f"Testing with library ID: {lib_id}")
    print()
    
    print("1. Creating query request...")
    client = TemporalQueryClient()
    request = QueryRequest(
        lib_id=lib_id,
        query_embedding=[1.0, 0.0],
        k=2,
        index="brute",
    )
    
    print("2. Executing workflow...")
    try:
        result = await client.execute_query(request)
        
        print("   ✓ Workflow completed!")
        print()
        print("3. Results:")
        hits = result.get('hits', [])
        print(f"   Found {len(hits)} hits")
        
        for i, hit in enumerate(hits, 1):
            print(f"   Hit {i}: {hit.get('text', 'N/A')} (score: {hit.get('score', 0):.4f})")
        
        print()
        print("=" * 70)
        print("✓ TEST PASSED!")
        print("=" * 70)
        print()
        print("System is working correctly!")
        print(f"Storage: {'Redis' if settings.USE_REDIS else 'In-Memory'}")
        print()
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_system())

