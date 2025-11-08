#!/usr/bin/env python3
"""
Wipe all Redis data for the vector database.

This script clears all libraries, documents, and chunks from Redis.
Useful for cleaning up after demos or testing.
"""

import redis
import sys
from app.core.config import settings


def wipe_redis_data():
    """Clear all vector_db data from Redis."""
    try:
        # Connect to Redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=False)
        
        # Test connection
        r.ping()
        print("✓ Connected to Redis")
        
        # Find all vector_db keys
        pattern = "vector_db:*"
        keys = r.keys(pattern)
        
        if not keys:
            print("✓ No data found in Redis (already empty)")
            return
        
        print(f"Found {len(keys)} keys to delete:")
        for key in keys:
            print(f"  - {key.decode('utf-8')}")
        
        # Confirm deletion
        print()
        response = input("Delete all vector_db data? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("✗ Cancelled")
            return
        
        # Delete all keys
        deleted = 0
        for key in keys:
            r.delete(key)
            deleted += 1
        
        print(f"✓ Deleted {deleted} keys")
        print("✓ Redis data wiped!")
        
    except redis.ConnectionError:
        print("✗ Error: Cannot connect to Redis")
        print(f"  URL: {settings.REDIS_URL}")
        print("  Make sure Redis is running: docker-compose up -d redis")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 70)
    print("WIPE REDIS DATA")
    print("=" * 70)
    print()
    
    if not settings.USE_REDIS:
        print("⚠ WARNING: USE_REDIS is False")
        print("  This script only works when Redis is enabled")
        print()
        response = input("Continue anyway? (yes/no): ").strip().lower()
        if response != 'yes':
            print("✗ Cancelled")
            sys.exit(0)
        print()
    
    wipe_redis_data()

