#!/usr/bin/env python3
"""Verify automatic scheduling is working."""

import requests
import time
import json

BASE_URL = "https://aeterna-autonomous-alpha-engine.onrender.com"

print("=" * 60)
print("AUTOMATIC SCHEDULER TEST")
print("=" * 60)

# Check initial state
print("\n[1] Initial state...")
r = requests.get(f"{BASE_URL}/ingestion/stats")
initial = r.json()
print(f"Total events: {initial['total_events']}")
print(f"By source: {initial['by_source']}")

# Wait for RSS collector to run (scheduled every 60 seconds)
print("\n[2] Waiting 65 seconds for RSS collector to run...")
print("(Collectors should run automatically via APScheduler)")
time.sleep(65)

# Check if new events appeared
print("\n[3] Checking stats after scheduled collection...")
r = requests.get(f"{BASE_URL}/ingestion/stats")
updated = r.json()
print(f"Total events: {updated['total_events']}")
print(f"By source: {updated['by_source']}")

# Calculate difference
added = updated['total_events'] - initial['total_events']
print(f"\n[4] Summary:")
print(f"Events added in 65 seconds: {added}")

if added > 0:
    print("✅ SUCCESS: Automatic scheduling is working!")
    print("   Collectors are running on schedule and adding events")
else:
    print("⚠️  No new events in 65 seconds")
    print("   Schedulers might not be running")
