#!/usr/bin/env python3
"""Quick test of health and diagnostic endpoints."""

import requests
import time
import json

BASE_URL = "https://aeterna-autonomous-alpha-engine.onrender.com"

print("Testing service deployment...")
print("=" * 60)

# Test health
print("\n[1] Checking health endpoint...")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("✅ Service is up")
    else:
        print(f"❌ Service returned {r.status_code}")
except Exception as e:
    print(f"❌ Health check failed: {e}")

# Test diagnostic endpoints
endpoints = [
    "/ingestion/diagnostic/test-rss-sync",
    "/ingestion/diagnostic/test-consumer-poll",
    "/ingestion/diagnostic/rabbitmq-queue-depth",
]

for endpoint in endpoints:
    print(f"\n[2] Testing {endpoint}...")
    try:
        url = f"{BASE_URL}{endpoint}"
        r = requests.get(url, timeout=60)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"Response: {r.text[:200]}")
    except requests.Timeout:
        print(f"⏱️  Request timed out (endpoint is slow - might be processing)")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    time.sleep(2)

print("\n" + "=" * 60)
