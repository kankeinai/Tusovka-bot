#!/usr/bin/env python3
"""
Simple health check script for DigitalOcean App Platform
"""
import asyncio
import aiohttp
import sys
import os

async def check_health():
    """Check if the bot's health endpoint is responding"""
    try:
        # Use localhost for container health checks
        url = 'http://localhost:8080/health'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    print("✅ Health check passed")
                    return True
                else:
                    print(f"❌ Health check failed with status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Health check failed with error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_health())
    sys.exit(0 if success else 1) 