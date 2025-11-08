#!/usr/bin/env python3
"""
Enable Redis and verify setup.
"""

import os
import sys

def enable_redis():
    env_file = ".env"
    
    # Read existing .env if it exists
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Update Redis settings
    env_vars['USE_REDIS'] = 'true'
    env_vars['REDIS_URL'] = 'redis://localhost:6379/0'
    
    # Write back to .env
    with open(env_file, 'w') as f:
        # Write COHERE_API_KEY if it exists
        if 'COHERE_API_KEY' in env_vars:
            f.write(f"COHERE_API_KEY={env_vars['COHERE_API_KEY']}\n")
        
        # Write Redis settings
        f.write(f"USE_REDIS={env_vars['USE_REDIS']}\n")
        f.write(f"REDIS_URL={env_vars['REDIS_URL']}\n")
    
    print("✓ Redis enabled in .env")
    print(f"  USE_REDIS=true")
    print(f"  REDIS_URL=redis://localhost:6379/0")
    print()
    print("⚠ Remember to restart worker and API server!")

if __name__ == "__main__":
    enable_redis()

