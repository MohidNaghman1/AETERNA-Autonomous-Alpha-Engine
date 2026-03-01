# AETERNA Ingestion System - Complete Guide

**Last Updated:** March 1, 2026

This guide explains how the AETERNA data ingestion system works, how to set it up, and how to use it. No prior knowledge required.

---

## Table of Contents

1. [What is This System?](#what-is-this-system)
2. [How It Works (Overview)](#how-it-works-overview)
3. [System Architecture](#system-architecture)
4. [Setup & Installation](#setup--installation)
5. [Running the System](#running-the-system)
6. [Using the API](#using-the-api)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

---

## What is This System?

The **AETERNA Ingestion System** is an automated data pipeline that:

- **Collects** cryptocurrency news and price data from external sources
- **Processes** the data and scores its importance
- **Stores** everything in a database
- **Generates alerts** when important events occur
- **Delivers** those alerts to users via email, Telegram, or web notifications

Think of it like a robot that watches crypto news, understands what's important, saves it to a file, and alerts you when something big happens.

---

## How It Works (Overview)

### The Simple Flow

```
Data Collection → Message Queue → Store in DB → Analyze → Generate Alerts
(News/Prices)    (RabbitMQ)      (Raw Data)   (Scoring)  (Notifications)
```

### Step-by-Step

1. **Collection (Every 60 seconds)**
   - RSS collector fetches news from CoinDesk, CoinTelegraph, Decrypt
   - Price collector fetches top 100 crypto prices from CoinGecko
   - Both send data to a message queue (RabbitMQ)

2. **Storage**
   - A consumer reads messages from the queue
   - Stores the raw data in the database
   - This happens almost instantly

3. **Analysis (Intelligence Agent)**
   - Another consumer reads the same data
   - Scores it based on: multi-source mentions, engagement, bot detection, etc.
   - Calculates a priority: HIGH, MEDIUM, or LOW
   - Stores scores in database

4. **Alert Generation**
   - High and medium priority events trigger alerts
   - Respects user preferences (quiet hours, channels, etc.)
   - Stores alert records in database

5. **Delivery**
   - Alerts sent via email, Telegram, or WebSocket
   - User sees notification immediately

**Key Point:** Raw data is stored **immediately** (within ~100ms), so you never lose data.

---

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    AETERNA INGESTION SYSTEM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📰 RSS Collector     💰 Price Collector                        │
│  (News)               (Crypto Prices)                           │
│  ↓                    ↓                                          │
│  └──────────┬─────────┘                                         │
│             ↓                                                    │
│         📦 RabbitMQ (Message Queue)                             │
│             ↓                                                    │
│  ┌─────────────────────────┐                                    │
│  │ 🔄 Event Consumer       │ → 💾 PostgreSQL DB                │
│  │ (Saves raw events)      │    (events table)                  │
│  └─────────────────────────┘                                    │
│             ↓                                                    │
│  ┌─────────────────────────┐                                    │
│  │ 🧠 Intelligence Consumer│ → 💾 PostgreSQL DB                │
│  │ (Scores events)         │    (processed_events table)        │
│  └─────────────────────────┘                                    │
│             ↓                                                    │
│  ┌─────────────────────────┐                                    │
│  │ ⚠️  Alert Generator     │ → 💾 PostgreSQL DB                │
│  │ (Creates alerts)        │    (alerts table)                  │
│  └─────────────────────────┘                                    │
│             ↓                                                    │
│  ┌─────────────────────────┐                                    │
│  │ 📤 Delivery Module      │                                    │
│  │ (Email, Telegram, Web)  │                                    │
│  └─────────────────────────┘                                    │
│             ↓                                                    │
│  ⚡ 🔔 ✉️  User Gets Alert!                                   │
│                                                                  │
│  📡 FastAPI Server (REST API)                                   │
│     ↑                                                            │
│     └─ User queries: /ingestion/events, /ingestion/stats        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component      | Technology | Purpose                     |
| -------------- | ---------- | --------------------------- |
| Data Queue     | RabbitMQ   | Reliable message passing    |
| Database       | PostgreSQL | Permanent storage           |
| Cache          | Redis      | Deduplication tracking      |
| Task Scheduler | Celery     | Run collectors periodically |
| API            | FastAPI    | Expose data to users        |
| Messaging      | pika       | RabbitMQ communication      |

### Database Tables

```
events
├─ id: Auto-incrementing ID
├─ source: "coindesk", "coingecko", etc.
├─ type: "news" or "price"
├─ timestamp: When collected
├─ content: Full data (JSON)
└─ raw: Original API response

processed_events
├─ id: Auto-incrementing ID
├─ event_id: Link to events table
├─ priority: "HIGH", "MEDIUM", "LOW"
├─ score: 0-100 importance score
├─ multi_source_score: Appears in multiple sources?
├─ engagement_score: How much interaction?
├─ bot_score: Is this spam?
├─ dedup_score: Is it unique?
└─ timestamp: When processed

alerts
├─ id: Auto-incrementing ID
├─ alert_id: Unique alert identifier
├─ user_id: Who should see this?
├─ event_id: Which event triggered this?
├─ priority: "HIGH", "MEDIUM", "LOW"
├─ channels: ["email", "telegram", "web"]
├─ status: "pending", "sent", "read"
└─ created_at: When alert was created
```

---

## Setup & Installation

### Prerequisites

You need these installed on your computer:

- **Python 3.9+** - Programming language
- **PostgreSQL** - Database
- **RabbitMQ** - Message queue
- **Redis** - Cache
- **pip** - Python package manager

### Check if You Have Everything

```powershell
python --version         # Should show 3.9 or higher
psql --version          # Should show PostgreSQL version
# RabbitMQ and Redis - check their services
```

### Step 1: Install Python Dependencies

```powershell
cd C:\Users\lenovo\Desktop\LangChain\AETERNA-Autonomous-Alpha-Engine

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

### Step 2: Set Up Environment Variables

Create or edit `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost/aeterna
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_PASSWORD

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=events

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API
API_HOST=localhost
API_PORT=8000
```

### Step 3: Create Database

```powershell
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE aeterna;
\q
```

### Step 4: Run Database Migrations

```powershell
# This creates all tables automatically
alembic upgrade head
```

Verify tables were created:

```powershell
psql -U postgres -d aeterna -c "\dt"
```

You should see: `events`, `processed_events`, `alerts`, `users`, `user_preferences`, etc.

---

## Running the System

### Quick Start (All Components)

You need **6 separate terminals**:

**Terminal 1: Start RabbitMQ**

```powershell
# If installed as Windows service
# Just make sure service is running

# Or if installed as executable
rabbitmq-server
```

**Terminal 2: Start PostgreSQL**

```powershell
# PostgreSQL service should be running
# If not: pg_ctl -D "C:\Program Files\PostgreSQL\data" start
```

**Terminal 3: Start Redis**

```powershell
# Redis service should be running
```

**Terminal 4: Start Event Consumer**

```powershell
.\venv\Scripts\Activate.ps1
python -m app.modules.ingestion.application.consumer
```

Expected output:

```
[CONSUMER] Listening on queue 'events'...
```

**Terminal 5: Start Collectors**

```powershell
.\venv\Scripts\Activate.ps1
python -m app.modules.ingestion.application.rss_collector
```

This will fetch news every 60 seconds.

**Terminal 6: Start API Server**

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Expected output:

```
Uvicorn running on http://127.0.0.1:8000
```

**Terminal 7 (Optional): Start Intelligence Consumer**

```powershell
.\venv\Scripts\Activate.ps1
python -m app.modules.intelligence.application.consumer
```

### Verify Everything is Working

```powershell
# Check all services are running
$resp = Invoke-WebRequest -Uri "http://localhost:8000/health/system"
$resp.Content

# Should show something like:
# {"rabbitmq":"✅ Connected","redis":"✅ Connected","postgresql":"✅ Connected"}

# Check if data is being collected
$resp = Invoke-WebRequest -Uri "http://localhost:8000/ingestion/stats"
$resp.Content

# Should show events count (will be 0 initially, increases as system runs)
# {"total_events":42,"by_source":{"coindesk":15,"coingecko":27},"by_type":{"news":15,"price":27}}
```

---

## Using the API

### What is an API?

An API is a way to ask the system for data. You make a request, it sends back the answer.

### Base URL

```
http://localhost:8000
```

### Common Endpoints

#### 1. Get Statistics

**What:** How many events have been collected?

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/stats" | Select-Object -ExpandProperty Content
```

**Response:**

```json
{
  "total_events": 1234,
  "by_source": {
    "coindesk": 500,
    "coingecko": 734
  },
  "by_type": {
    "news": 500,
    "price": 734
  }
}
```

#### 2. Get All Events

**What:** Get a list of all events (news and prices)

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/events" | Select-Object -ExpandProperty Content
```

**Optional Parameters:**

- `skip=0` - Start from which event (for pagination)
- `limit=100` - How many to return (max 500)

**Example with filters:**

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/events?source=coindesk&type=news&limit=10" | Select-Object -ExpandProperty Content
```

#### 3. Get Single Event

**What:** Get details of one specific event

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/events/1" | Select-Object -ExpandProperty Content
```

**Response:**

```json
{
  "id": 1,
  "source": "coindesk",
  "type": "news",
  "timestamp": "2026-03-01T15:30:00",
  "content": {
    "title": "Bitcoin Reaches New High",
    "summary": "Bitcoin price surges past $50,000",
    "link": "https://..."
  },
  "raw": null
}
```

#### 4. Get Events by Source

```powershell
# Get news from CoinDesk
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/search/by-source/coindesk" | Select-Object -ExpandProperty Content

# Get price data from CoinGecko
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/search/by-source/coingecko" | Select-Object -ExpandProperty Content
```

#### 5. Get Events by Type

```powershell
# Get all news
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/search/by-type/news" | Select-Object -ExpandProperty Content

# Get all price updates
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/search/by-type/price" | Select-Object -ExpandProperty Content
```

#### 6. Filter by Date Range

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/ingestion/events?start_date=2026-03-01T00:00:00&end_date=2026-03-02T00:00:00" | Select-Object -ExpandProperty Content
```

#### 7. System Health

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/health/system" | Select-Object -ExpandProperty Content
```

**Response:**

```json
{
  "rabbitmq": "✅ Connected",
  "redis": "✅ Connected",
  "postgresql": "✅ Connected"
}
```

### Using in Code

**Python Example:**

```python
import requests

# Get stats
response = requests.get('http://localhost:8000/ingestion/stats')
data = response.json()
print(f"Total events: {data['total_events']}")

# Get events
response = requests.get('http://localhost:8000/ingestion/events?limit=10')
events = response.json()
for event in events:
    print(f"{event['source']} - {event['type']}: {event['content']['title']}")
```

**JavaScript Example:**

```javascript
// Get events
fetch("http://localhost:8000/ingestion/events?limit=10")
  .then((response) => response.json())
  .then((events) => {
    events.forEach((event) => {
      console.log(`${event.source}: ${event.content.title}`);
    });
  });
```

---

## Troubleshooting

### Problem: "Connection refused" when accessing API

**Cause:** API server not running

**Solution:**

```powershell
# Check if running
Get-Process | Where-Object {$_.ProcessName -eq "python"}

# If not in list, start it:
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

---

### Problem: Stats show 0 events, but collectors are running

**Cause:** Consumer not running or database not saving

**Solution:**

1. Check consumer is running:

```powershell
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Where-Object {$_.CommandLine -like "*consumer*"}
```

2. If not running, start it:

```powershell
.\venv\Scripts\Activate.ps1
python -m app.modules.ingestion.application.consumer
```

3. Test manually:

```powershell
.\venv\Scripts\Activate.ps1
python -c "
from app.config.db import SessionLocal
from app.modules.ingestion.infrastructure.models import EventORM

db = SessionLocal()
count = db.query(EventORM).count()
print(f'Events in database: {count}')
db.close()
"
```

---

### Problem: RabbitMQ connection error

**Cause:** RabbitMQ service not running

**Solution:**

```powershell
# Check if running
Get-Service | Where-Object {$_.Name -like "*rabbitmq*"}

# If stopped, start it:
Start-Service RabbitMQ

# Or run directly:
rabbitmq-server
```

---

### Problem: PostgreSQL connection error

**Cause:** Database not running or credentials wrong

**Solution:**

1. Check service:

```powershell
Get-Service | Where-Object {$_.Name -like "*postgres*"}
```

2. Test connection:

```powershell
psql -U postgres -d aeterna -c "SELECT COUNT(*) FROM events;"
```

3. If fails, check `.env` file has correct credentials

---

### Problem: Events in RabbitMQ but not in database

**Cause:** Consumer crashed during processing

**Solution:**

1. Check consumer logs (look at terminal where consumer is running)
2. Look for error messages
3. Common causes:
   - Database connection lost
   - Malformed data
   - Missing columns
   - Permission errors

**Fix:**

- Restart consumer
- Restart database
- Check data format

---

### Problem: "Table does not exist" error

**Cause:** Migrations not run

**Solution:**

```powershell
# Create all tables
alembic upgrade head

# Verify
psql -U postgres -d aeterna -c "\dt"
```

---

### Problem: RabbitMQ has lots of messages but system is slow

**Cause:** Consumer can't keep up

**Solution:**

1. Check if collector is running multiple times:

```powershell
Get-Process python
```

2. If multiple collectors running, stop duplicates

3. Increase consumer prefetch (advanced):
   - Edit `app/modules/ingestion/application/consumer.py`
   - Change `channel.basic_qos(prefetch_count=1)` to higher number

---

## Advanced Topics

### How Scoring Works

Raw events from collectors have a basic score. The Intelligence Agent enhances this with:

```
Final Score = (30% × Multi-source Check)
            + (20% × Engagement Analysis)
            + (30% × Bot Detection)
            + (20% × Deduplication Score)
```

**Priority Assignment:**

- Score ≥ 80 → HIGH priority
- Score 50-79 → MEDIUM priority
- Score < 50 → LOW priority

### Where Data Goes To

**Raw Events** → `events` table

- What's collected directly from sources
- Never modified
- Used as source of truth

**Processed Events** → `processed_events` table

- Same events with scores
- Includes priority
- What gets alerted on

**Alerts** → `alerts` table

- Generated from HIGH/MEDIUM events
- One alert = One notification sent
- Tracks status (sent, read, etc.)

### Database Backups

```powershell
# Backup database
pg_dump -U postgres aeterna > aeterna_backup.sql

# Restore
psql -U postgres aeterna < aeterna_backup.sql

# Backup to regular schedule with task scheduler:
# Task: "Run at 2:00 AM every night"
# Action: "pg_dump -U postgres aeterna > C:\backups\aeterna_$(Get-Date -Format yyyyMMdd).sql"
```

### Performance Tuning

**If system is slow:**

1. Check database indexes:

```sql
SELECT * FROM pg_indexes WHERE tablename = 'events';
```

2. Monitor queue size:

```powershell
python -c "
import pika
import os
from dotenv import load_dotenv

load_dotenv()
creds = pika.PlainCredentials(os.getenv('RABBITMQ_USER'), os.getenv('RABBITMQ_PASSWORD'))
conn = pika.BlockingConnection(pika.ConnectionParameters(os.getenv('RABBITMQ_HOST'), credentials=creds))
ch = conn.channel()
q = ch.queue_declare('events', durable=True, passive=True)
print(f'Messages in queue: {q.method.message_count}')
conn.close()
"
```

3. Add more consumers:
   - Run multiple `python -m app.modules.ingestion.application.consumer` in different terminals
   - They'll automatically load-balance

### Custom Data Source

To add your own data source:

1. Create collector in `app/modules/ingestion/application/my_collector.py`
2. Publish JSON to RabbitMQ in same format
3. Existing consumer will automatically store it

---

## Summary

| Command                                                         | What it does                  |
| --------------------------------------------------------------- | ----------------------------- |
| `.\venv\Scripts\Activate.ps1`                                   | Activate Python environment   |
| `python -m app.modules.ingestion.application.consumer`          | Start event storage service   |
| `python -m app.modules.ingestion.application.rss_collector`     | Start news collector          |
| `alembic upgrade head`                                          | Create/update database tables |
| `uvicorn app.main:app --reload`                                 | Start API server              |
| `Invoke-WebRequest http://localhost:8000/ingestion/stats`       | Get stats                     |
| `psql -U postgres -d aeterna -c "SELECT COUNT(*) FROM events;"` | Count events in DB            |

---

## Support

### Check System Status

```powershell
# All-in-one health check
Invoke-WebRequest -Uri "http://localhost:8000/health/system" | Select-Object -ExpandProperty Content
```

### Common Issues Location

| Issue            | Check File                             |
| ---------------- | -------------------------------------- |
| Collector errors | Terminal running `rss_collector`       |
| Consumer errors  | Terminal running `consumer`            |
| API errors       | Terminal running `uvicorn`             |
| Database errors  | PostgreSQL logs                        |
| Queue errors     | RabbitMQ admin panel (localhost:15672) |

### Getting Help

1. **Check error message** - tells you what's wrong
2. **Check logs** - look at terminal output
3. **Verify connections** - run `/health/system` endpoint
4. **Restart service** - stop and start the problematic service
5. **Check database** - manually query with `psql`

---

**You're all set! The system is ready to collect, process, and alert on crypto data.** 🚀
