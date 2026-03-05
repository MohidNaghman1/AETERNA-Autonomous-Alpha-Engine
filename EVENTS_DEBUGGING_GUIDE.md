# Events Not Showing - Debugging Guide

**Date:** March 4, 2026  
**Issue:** API endpoint `/ingestion/events` returns empty array `[]` despite 200 OK response

## Root Causes Identified and Fixed

### Issue #1: Infinite Loop in Collectors (CRITICAL - NOW FIXED)

**Problem:**

- `run_collector()` in both `rss_collector.py` and `price_collector.py` were blocking infinite loops
- When called by Celery Beat, tasks would hang and never complete
- On Render's free tier, hanging tasks lead to worker restarts and service interruptions
- Events never got published to RabbitMQ

**Solution Applied:**

```python
# ❌ BEFORE: Infinite loop that never returned
def run_collector():
    while True:
        # ... fetch and publish events ...
        time.sleep(POLL_INTERVAL)  # Block forever

# ✅ AFTER: Single run that returns
def run_collector():
    # ... fetch and publish events once ...
    logger.info("Collection cycle completed.")
    # Returns normally

def run_collector_loop():
    # Use this for standalone execution
    while True:
        run_collector()
        time.sleep(POLL_INTERVAL)
```

**Files Changed:**

- `app/modules/ingestion/application/rss_collector.py`
- `app/modules/ingestion/application/price_collector.py`

### Issue #2: Timestamp Type Mismatch (Already Fixed Earlier)

- `Event` domain model stores timestamp as ISO8601 string
- `EventORM` expects datetime object
- Consumer now properly converts: `datetime.fromisoformat(timestamp_str.rstrip('Z'))`

### Issue #3: Celery on Free Tier Limitations

On Render.com's free tier:

- Worker services can be suspended after inactivity
- Services get restarted frequently
- Each restart interrupts the event collection cycle
- RabbitMQ connection pooling might timeout

---

## Verification Steps

### Step 1: Test Diagnostics Endpoint

```bash
curl https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/diagnostic
```

Expected response:

```json
{
  "timestamp": "2026-03-04T12:47:00.123Z",
  "database": {
    "status": "✅ Connected",
    "total_events": 0
  },
  "rabbitmq": {
    "status": "✅ Connected",
    "host": "your-rabbitmq-host"
  },
  "events": {
    "recent": []
  }
}
```

### Step 2: Create Test Event

```bash
curl -X POST https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/test-event
```

Expected response:

```json
{
  "status": "success",
  "event_id": 1,
  "timestamp": "2026-03-04T12:47:05.123Z"
}
```

Then verify it appears:

```bash
curl https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/events?skip=0&limit=10
```

Should now return the test event.

### Step 3: Manually Trigger Collection

```bash
curl -X POST https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/trigger-rss-collection
```

Expected response:

```json
{
  "status": "success",
  "message": "RSS collection triggered",
  "timestamp": "2026-03-04T12:47:10.123Z"
}
```

Then check events:

```bash
curl https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/events?source=coindesk&limit=10
```

Should return any news articles collected.

### Step 4: Check Logs

View real-time logs from Render dashboard:

```
Services > aeterna-celery-beat > Logs
Services > aeterna-celery-worker > Logs
Services > aeterna-consumer > Logs
Services > aeterna-api > Logs
```

Look for messages like:

- `✅ PROCESSED Event ...` (consumer success)
- `Publishing event:` (collector publishing)
- `Feed 'coindesk' returned X entries` (collector fetching)

---

## Architecture After Fixes

```
Celery Beat (runs on schedule)
    ↓
Celery Task: run_rss_collector()
    ↓ calls
rss_collector.run_collector() [SINGLE RUN - no loop]
    ↓ publishes to
RabbitMQ (events queue)
    ↓
Consumer (continuous listener)
    ↓ processes and
EventORM → PostgreSQL (events table)
    ↓
API endpoint (reads from DB)
    ↓
/ingestion/events [returns JSON]
```

---

## Deployment Checklist

- [ ] **Pull latest code** with collector fixes
- [ ] **Verify Python syntax** - no import errors
- [ ] **Rebuild Docker image**: `docker build -t aeterna:latest .`
- [ ] **Push to registry**
- [ ] **Deploy to Render.com**
- [ ] **Wait for services to start** (2-3 minutes)
- [ ] **Run diagnostic endpoint** - verify DB and RabbitMQ connected
- [ ] **Create test event** - verify API storage works
- [ ] **Trigger RSS collection** - verify publisher works
- [ ] **Check logs** for success messages
- [ ] **Query events** - verify data appears after 5-10 seconds

---

## Expected Timeline After Deployment

1. **T+0min**: Services deployed and started
2. **T+1min**: Celery Beat starts scheduling tasks
3. **T+2min**: First collection cycle runs
4. **T+3min**: Events published to RabbitMQ
5. **T+4min**: Consumer processes events and stores in DB
6. **T+5min**: Events visible via `/ingestion/events` API

---

## Troubleshooting

### No events after 10 minutes

1. Check if services are running: `Services > Logs`
2. Look for errors in consumer logs
3. Verify RabbitMQ is accessible
4. Manually trigger collection: `POST /ingestion/trigger-rss-collection`

### All services appear stopped

- Render free tier suspends idle services
- Visit the API URL to wake it up
- Services will auto-start

### RabbitMQ connection failures

- Verify credentials in environment variables
- Check if CloudAMQP service is active
- Restart RabbitMQ on render.yml databases section

### Consumer not processing messages

- Check consumer logs for errors
- Verify `RABBITMQ_QUEUE` environment variable is set to `events`
- Test with direct HTTP call: `POST /ingestion/test-event`

---

## Performance Monitoring

Query event statistics:

```bash
curl https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/stats
```

Expected response:

```json
{
  "total_events": 42,
  "by_source": {
    "coindesk": 15,
    "cointelegraph": 12,
    "coingecko": 15
  },
  "by_type": {
    "news": 27,
    "price": 15
  }
}
```

---

## Key Technical Details

### Celery Beat Schedule

From `celery_app.py`:

```python
beat_schedule = {
    "run_rss_collector": {
        "task": "app.modules.ingestion.application.tasks.run_rss_collector",
        "schedule": 60.0,  # Every 60 seconds
    },
    "run_price_collector": {
        "task": "app.modules.ingestion.application.tasks.run_price_collector",
        "schedule": 60.0,  # Every 60 seconds
    },
}
```

### Event Flow

1. RSS feeds are fetched every 60 seconds
2. Each entry is validated and deduplicated
3. Events are published to RabbitMQ as JSON
4. Consumer picks up messages from queue
5. Timestamp is converted from ISO8601 string to datetime
6. EventORM is created with all data
7. Transaction is committed to database
8. On success: message is ACKed and removed from queue
9. On failure: message is NACKed and returned for retry

---

## Files Modified

1. **`app/modules/ingestion/application/rss_collector.py`**
   - Split `run_collector()` into single-run and loop versions
   - Added proper logging for each cycle
2. **`app/modules/ingestion/application/price_collector.py`**
   - Split `run_collector()` into single-run and loop versions
   - Added proper logging for each cycle

3. **`app/modules/ingestion/presentation/api.py`**
   - Added `/diagnostic` endpoint for debugging connectivity
   - Added `/test-event` endpoint for testing DB storage
   - Added `/trigger-rss-collection` endpoint for manual testing
   - Added `/trigger-price-collection` endpoint for manual testing
   - Enhanced POST `/events` endpoint error handling

---

## Future Improvements

- [ ] Add metrics dashboard (Prometheus + Grafana)
- [ ] Implement dead-letter queue for failed events
- [ ] Add event retry mechanism with exponential backoff
- [ ] Create alerting for collection failures
- [ ] Implement circuit breaker for external APIs
- [ ] Add caching layer for frequently accessed events
- [ ] Implement pagination for large result sets
- [ ] Add event filtering by date range
