#!/usr/bin/env python3
"""
Test to verify that the Decrypt feed issue is resolved.

This test:
1. Captures initial Decrypt event count in database
2. Triggers fresh RSS collection (including Decrypt feed)
3. Consumes messages from RabbitMQ queue
4. Captures final Decrypt event count in database
5. Reports if issue is fixed (new events should appear)
"""

import time
import requests
import json
import urllib.request
import urllib.error
import ssl

# Disable SSL verification for local testing
ssl._create_default_https_context = ssl._create_unverified_context

BASE_URL = "https://aeterna-autonomous-alpha-engine.onrender.com"

def make_request(url, method="GET", timeout=30):
    """Make HTTP request without requests library."""
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)

def get_decrypt_count():
    """Get current count of Decrypt events in database."""
    try:
        status, response = make_request(f"{BASE_URL}/ingestion/stats", timeout=15)
        if status == 200:
            data = json.loads(response)
            return data.get("by_source", {}).get("decrypt.co", 0)
        else:
            print(f"❌ Failed to get stats: HTTP {status}")
            return None
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return None

def trigger_rss_collection():
    """Trigger RSS collection to fetch fresh Decrypt entries."""
    try:
        status, response = make_request(f"{BASE_URL}/ingestion/trigger-rss-collection", method="POST", timeout=30)
        if status == 200:
            print("✅ RSS collection triggered")
            return True
        else:
            print(f"❌ Failed to trigger collection: HTTP {status}")
            return False
    except Exception as e:
        print(f"❌ Trigger failed: {e}")
        return False

def poll_consumer(batch_size=1000):
    """Manually poll consumer to process RabbitMQ messages."""
    try:
        status, response = make_request(
            f"{BASE_URL}/ingestion/diagnostic/test-consumer-poll?batch_size={batch_size}",
            timeout=60
        )
        if status == 200:
            data = json.loads(response)
            count = data.get("processed_count", 0)
            actual_batch = data.get("batch_size", batch_size)
            print(f"✅ Consumer polled: processed {count} messages (batch_size={actual_batch})")
            return count
        else:
            print(f"❌ Consumer poll failed: HTTP {status}")
            return 0
    except Exception as e:
        print(f"❌ Consumer poll error: {e}")
        return 0

def get_full_stats():
    """Get full statistics of all events."""
    try:
        status, response = make_request(f"{BASE_URL}/ingestion/stats", timeout=15)
        if status == 200:
            return json.loads(response)
        return None
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return None

def check_rss_collection_details():
    """Get detailed RSS collection results."""
    try:
        status, response = make_request(
            f"{BASE_URL}/ingestion/diagnostic/test-rss-sync",
            timeout=120
        )
        if status == 200:
            data = json.loads(response)
            if "results" in data:
                success = data["results"].get("success", [])
                for item in success:
                    if item["source"] == "decrypt.co":
                        return item
        return None
    except Exception as e:
        if "timeout" in str(e).lower():
            print("⏱️  RSS diagnostic timed out")
        else:
            print(f"❌ RSS diagnostic error: {e}")
        return None

if __name__ == "__main__":
    print("=" * 70)
    print("DECRYPT FEED ISSUE TEST")
    print("=" * 70)
    print("Checking if Decrypt.co events are being stored properly\n")
    
    # Step 1: Get initial count
    print("[1] Getting initial Decrypt event count...")
    initial_decrypt = get_decrypt_count()
    if initial_decrypt is None:
        print("❌ Cannot connect to service")
        exit(1)
    print(f"    Initial Decrypt events: {initial_decrypt}\n")
    
    # Step 2: Trigger collection
    print("[2] Triggering RSS collection...")
    if not trigger_rss_collection():
        print("❌ Failed to trigger collection")
        exit(1)
    time.sleep(2)
    
    # Step 3: Check what RSS collector found
    print("\n[3] Checking RSS collection details...")
    rss_detail = check_rss_collection_details()
    if rss_detail:
        print(f"    Source: {rss_detail.get('source')}")
        print(f"    Total entries found: {rss_detail.get('total_entries')}")
        print(f"    New entries published: {rss_detail.get('new_entries')}")
        print(f"    Duplicates skipped: {rss_detail.get('duplicates_skipped')}")
        print(f"    Publish failed: {rss_detail.get('publish_failed')}")
        print(f"    Normalization errors: {rss_detail.get('normalization_errors', 'N/A')}")
    else:
        print("    ⚠️  Could not get RSS details")
    
    # Step 4: Wait for collection to complete
    print("\n[4] Waiting 15 seconds for collection to complete...")
    time.sleep(15)
    
    # Step 5: Poll consumer with large batch
    print("\n[5] Polling consumer to process all queued messages...")
    processed = poll_consumer(batch_size=10000)  # Process everything in queue
    
    # Step 6: Wait for database updates
    print("\n[6] Waiting 5 seconds for database updates...")
    time.sleep(5)
    
    # Step 7: Get final count
    print("\n[7] Getting final Decrypt event count...")
    final_decrypt = get_decrypt_count()
    if final_decrypt is None:
        print("❌ Cannot get final count")
        exit(1)
    decrypt_added = final_decrypt - initial_decrypt
    print(f"    Final Decrypt events: {final_decrypt}")
    print(f"    Events added: {decrypt_added}\n")
    
    # Step 8: Get full stats for context
    print("[8] Full Statistics:")
    stats = get_full_stats()
    if stats:
        print(f"    Total events in database: {stats.get('total_events')}")
        print(f"    By source:")
        for source, count in stats.get('by_source', {}).items():
            print(f"      - {source}: {count}")
    
    # Final verdict
    print("\n" + "=" * 70)
    print("TEST RESULT")
    print("=" * 70)
    
    if decrypt_added > 0:
        print(f"✅ SUCCESS: Decrypt issue is FIXED!")
        print(f"   {decrypt_added} new Decrypt events added to database")
        print(f"   (from {initial_decrypt} → {final_decrypt})")
    elif processed > 0 and decrypt_added == 0:
        print(f"⚠️  PARTIAL: Consumer processed {processed} messages but Decrypt didn't increase")
        print(f"   Decrypt events may be failing validation or normalization")
    else:
        print(f"❌ FAILED: Decrypt issue NOT fixed")
        print(f"   No new Decrypt events added (still {final_decrypt} total)")
        if processed == 0:
            print(f"   Consumer didn't process any messages - check RabbitMQ queue")
    
    print("=" * 70)
    
    # Exit with appropriate code
    exit(0 if decrypt_added > 0 else 1)
