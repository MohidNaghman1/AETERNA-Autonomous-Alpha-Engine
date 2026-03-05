#!/usr/bin/env python3
"""Test script to trigger RSS collection and check if events are created."""

import requests
import time
import json

BASE_URL = "https://aeterna-autonomous-alpha-engine.onrender.com"

def get_stats():
    """Get current event stats."""
    response = requests.get(f"{BASE_URL}/ingestion/stats")
    response.raise_for_status()
    return response.json()

def trigger_rss_collection():
    """Trigger RSS collection via POST."""
    response = requests.post(f"{BASE_URL}/ingestion/trigger-rss-collection")
    response.raise_for_status()
    return response.json()

def trigger_price_collection():
    """Trigger price collection via POST."""
    response = requests.post(f"{BASE_URL}/ingestion/trigger-price-collection")
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    print("=" * 60)
    print("COLLECTOR TRIGGER TEST")
    print("=" * 60)
    
    # Get initial stats
    print("\n[1] Getting initial stats...")
    stats_before = get_stats()
    print(f"Total events before: {stats_before['total_events']}")
    print(f"By source: {stats_before['by_source']}")
    
    # Trigger RSS collection
    print("\n[2] Triggering RSS collection...")
    result = trigger_rss_collection()
    print(f"Response: {result}")
    
    # Wait 15 seconds for processing (collectors can be slow with HTTP requests)
    print("\n[3] Waiting 15 seconds for events to be processed...")
    time.sleep(15)
    
    # Check stats after RSS
    print("\n[4] Getting stats after RSS trigger...")
    stats_after_rss = get_stats()
    print(f"Total events after RSS: {stats_after_rss['total_events']}")
    print(f"By source: {stats_after_rss['by_source']}")
    
    # Trigger price collection
    print("\n[5] Triggering price collection...")
    result = trigger_price_collection()
    print(f"Response: {result}")
    
    # Wait 15 seconds for processing
    print("\n[6] Waiting 15 seconds for events to be processed...")
    time.sleep(15)
    
    # Check final stats
    print("\n[7] Getting final stats after price trigger...")
    stats_after_price = get_stats()
    print(f"Total events after price: {stats_after_price['total_events']}")
    print(f"By source: {stats_after_price['by_source']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Starting events: {stats_before['total_events']}")
    print(f"Ending events: {stats_after_price['total_events']}")
    print(f"Events added: {stats_after_price['total_events'] - stats_before['total_events']}")
    
    if stats_after_price['total_events'] > stats_before['total_events']:
        print("✅ SUCCESS: Collectors are working and events are being stored!")
    else:
        print("❌ FAILURE: No new events were created. Collectors may not be running.")
        print("\nDebugging steps:")
        print("1. Check if RSS collector is queued properly")
        print("2. Verify RabbitMQ connectivity")
        print("3. Check if consumer is running (should receive and store events)")
