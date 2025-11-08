#!/usr/bin/env python3
"""
Quick Redis cleanup - wipe all data without confirmation.
Use with caution!
"""

import redis
import sys
from app.core.config import settings


def quick_wipe():
    """Quickly wipe all vector_db data without confirmation."""
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=False)
        r.ping()
        
        keys = r.keys("vector_db:*")
        if keys:
            for key in keys:
                r.delete(key)
            print(f"✓ Wiped {len(keys)} keys from Redis")
        else:
            print("✓ Redis already empty")
            
    except redis.ConnectionError:
        print("✗ Redis not running. Start with: docker-compose up -d redis")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    quick_wipe()

