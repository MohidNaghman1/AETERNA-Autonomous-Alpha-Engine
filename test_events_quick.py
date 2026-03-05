#!/usr/bin/env python
"""
Quick test to verify events are being stored in the database correctly.
Run this to check if the timestamp fix is working.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

def test_event_storage():
    """Test that events can be stored and retrieved from the database."""
    print("\n" + "="*70)
    print("EVENT STORAGE TEST - Verifying database functionality")
    print("="*70 + "\n")
    
    try:
        from app.config.db import SessionLocal
        from app.modules.ingestion.infrastructure.models import EventORM
        from app.modules.ingestion.domain.models import Event
        
        # Test 1: Create an Event domain object
        print("1️⃣  Creating Event domain object...")
        event = Event.create(
            source="test-source",
            type_="news",
            timestamp=datetime.utcnow(),
            content={"title": "Test Event", "summary": "This is a test event"}
        )
        print(f"   ✅ Event created: {event.id}")
        print(f"   - Type: {type(event.timestamp)} = {event.timestamp}")
        
        # Test 2: Store in database using EventORM
        print("\n2️⃣  Storing event in database...")
        db = SessionLocal()
        
        # Parse timestamp string to datetime (this is what the consumer does)
        timestamp_str = getattr(event, "timestamp", None)
        if timestamp_str:
            ts_clean = timestamp_str.rstrip('Z')
            timestamp_dt = datetime.fromisoformat(ts_clean)
        else:
            timestamp_dt = None
        
        db_event = EventORM(
            source=getattr(event, "source", None),
            type=getattr(event, "type", None),
            timestamp=timestamp_dt,
            content=event.content,
            raw=None,
        )
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        print(f"   ✅ Event stored with DB ID: {db_event.id}")
        
        # Test 3: Retrieve from database
        print("\n3️⃣  Retrieving event from database...")
        retrieved = db.query(EventORM).filter(EventORM.id == db_event.id).first()
        if retrieved:
            print(f"   ✅ Event retrieved successfully")
            print(f"   - Source: {retrieved.source}")
            print(f"   - Type: {retrieved.type}")
            print(f"   - Timestamp: {retrieved.timestamp}")
            print(f"   - Content: {retrieved.content}")
        else:
            print(f"   ❌ Event not found!")
            return False
        
        # Test 4: Count total events
        print("\n4️⃣  Counting total events in database...")
        count = db.query(EventORM).count()
        print(f"   ✅ Total events: {count}")
        
        # Test 5: Retrieve all events (like the API would do)
        print("\n5️⃣  Retrieving all events with pagination...")
        events = db.query(EventORM).order_by(EventORM.timestamp.desc()).limit(100).offset(0).all()
        print(f"   ✅ Retrieved {len(events)} events")
        if events:
            for i, e in enumerate(events[:3], 1):
                print(f"   Event {i}: {e.source} - {e.type} ({e.timestamp})")
        
        db.close()
        
        print("\n✅ ALL TESTS PASSED!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("="*70 + "\n")


if __name__ == "__main__":
    success = test_event_storage()
    sys.exit(0 if success else 1)
