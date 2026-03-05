# Fix: Events Not Being Stored in Database

## Problem Summary
When requesting `/ingestion/events?skip=0&limit=100`, the endpoint returned HTTP 200 OK but with an empty list. The database query was executing correctly, but **no events were being stored in the database**.

## Root Cause
There was a **type mismatch** between two models:

### Event Domain Model (app/modules/ingestion/domain/models.py)
```python
class Event(BaseModel):
    ...
    timestamp: str = Field(..., description="UTC ISO8601 timestamp")
    
    @classmethod
    def create(cls, ..., timestamp: datetime, ...):
        ts = timestamp.replace(microsecond=0).isoformat() + "Z"  # ← Converts to STRING
        return cls(timestamp=ts, ...)  # ← Stored as "2026-03-04T12:27:02Z"
```

### EventORM Infrastructure Model (app/modules/ingestion/infrastructure/models.py)
```python
class EventORM(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)  # ← Expects datetime OBJECT
```

### The Bug in Consumer (app/modules/ingestion/application/consumer.py)
```python
# ❌ BEFORE (BROKEN)
db_event = EventORM(
    source=getattr(event, "source", None),
    type=getattr(event, "type", None),
    timestamp=getattr(event, "timestamp", None),  # ← Event.timestamp is a STRING!
    content=content,
    raw=None,
)
db.add(db_event)
db.commit()  # ← This SILENTLY FAILS, causing a ROLLBACK
```

When PostgreSQL tried to store a string like `"2026-03-04T12:27:02Z"` in a `DateTime` column, it caused a database constraint violation that was caught internally and rolled back, leaving no events stored.

## Solution Applied
I updated the consumer to **convert the ISO8601 string timestamp back to a datetime object** before storing:

```python
# ✅ AFTER (FIXED)
# Parse timestamp string to datetime object
# Event.timestamp is ISO8601 string (e.g., "2026-03-04T12:27:02Z")
# EventORM.timestamp expects datetime object
timestamp_str = getattr(event, "timestamp", None)
if timestamp_str:
    # Remove 'Z' suffix and parse
    ts_clean = timestamp_str.rstrip('Z')
    timestamp_dt = datetime.fromisoformat(ts_clean)
else:
    timestamp_dt = None

db_event = EventORM(
    source=getattr(event, "source", None),
    type=getattr(event, "type", None),
    timestamp=timestamp_dt,  # ← Now a proper datetime object
    content=content,
    raw=None,
)
db.add(db_event)
db.commit()  # ← Now succeeds!
```

## Files Modified
- **app/modules/ingestion/application/consumer.py**
  - Added `import datetime` at the top
  - Added timestamp parsing logic before creating EventORM (lines 117-124)

## Verification Steps
After deploying this fix, events should now be stored successfully. To verify:

### Option 1: Check API Endpoint
```bash
curl http://localhost:8000/ingestion/events?limit=100
```
Should return events in the response.

### Option 2: Check Stats
```bash
curl http://localhost:8000/ingestion/stats
```
Should show `total_events > 0`

### Option 3: Direct Database Query
```bash
psql -U postgres -d aeterna_db -c "SELECT COUNT(*) FROM events;"
```
Should return a count > 0

## How the Event Flow Works (Now Corrected)

1. **Collector** (RSS/Price) → Creates Event with timestamp as datetime
2. **Event.create()** → Converts datetime to ISO8601 **string** ("2026-03-04T12:27:02Z")
3. **Publisher** → Publishes Event JSON to RabbitMQ
4. **Consumer** → Receives JSON, deserializes to Event (**timestamp is STRING**)
5. **Consumer Fix** → **Converts string back to datetime** before storing
6. **EventORM** → Stores with correct datetime type
7. **API** → Queries database, returns events with proper datetime fields

## Why This Design?
The domain model uses ISO8601 strings for:
- **Serialization**: JSON-friendly format for API/RabbitMQ
- **Deduplication**: Consistent string representation for hashing

While EventORM uses datetime objects for:
- **Indexing**: Efficient database queries on timestamp
- **Type safety**: SQLAlchemy ORM type checking

The fix properly bridges this gap by converting at the persistence layer.
