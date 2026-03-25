# AETERNA: Database Schema & Design

## Complete Database Schema Reference, ER Diagrams & Optimization Guide

**Document Version:** 1.0  
**Date:** March 2026  
**Database:** PostgreSQL 15+  
**Status:** Production Ready  
**Last Updated:** March 25, 2026

---

## Table of Contents

1. Database Overview
2. Entity-Relationship Diagram
3. Core Tables & Schemas
4. Implementation Status: MVP vs Phase II
5. Indexing Strategy
6. Performance Optimization
7. Query Patterns & Examples
8. Migration Management
9. Backup & Recovery Integration
10. Size & Growth Projections
11. Operational Checklists

---

## 1. Database Overview

### 1.1 Database Architecture

ACTUAL IMPLEMENTATION (12 tables total, 5 implemented):

```
AETERNA Production Database (PostgreSQL 15+)
├── Schema: public
│   ├── Users & Auth (5 tables - IMPLEMENTED)
│   │   ├── users
│   │   ├── user_preferences
│   │   ├── refresh_tokens
│   │   ├── user_roles
│   │   └── password_reset_tokens
│   ├── Events & Processing (3 tables - IMPLEMENTED)
│   │   ├── events (raw ingestion)
│   │   ├── processed_events (scored/prioritized)
│   │   └── event_scores (future ML features)
│   ├── Alerts & Delivery (2+ tables - PARTIAL)
│   │   ├── alerts (current - MVP version)
│   │   └── alert_deliveries (future - Phase II)
│   └── System Tables (2 tables - NOT YET)
│       ├── audit_logs (planned)
│       └── system_metrics (planned)

Size: ~2-5 GB (estimated at 3 months)
Growth: ~1-2 GB per month
Connections: Max 100 (Pool: 20 per app instance)
Backup: Daily, retained 30 days
Replication: Async to read replica (optional Phase II)
```

**Implementation Status:**

- ✅ Users & Auth: Complete (5/5 tables)
- ✅ Events & Processing: Implemented (events, processed_events)
- ⚠️ Alerts: MVP version (simplified)
- ⏳ System: Planned for Phase II

### 1.2 Data Types & Conventions

**Naming Conventions:**

- Tables: singular, lowercase with underscores (`user`, `alert`, `event`)
- Columns: lowercase with underscores (`created_at`, `user_id`)
- Indexes: `idx_<table>_<column>` (e.g., `idx_events_timestamp`)
- Foreign keys: `fk_<table>_<referenced_table>` (e.g., `fk_alerts_user_id`)

**Data Type Standards:**

```
Primary Keys: BIGINT SERIAL (auto-increment)
Foreign Keys: BIGINT (matches parent table)
Timestamps: TIMESTAMP WITH TIME ZONE (always UTC)
Money: NUMERIC(19,2) (cents as integer)
IDs/UUIDs: UUID PRIMARY KEY DEFAULT gen_random_uuid()
Booleans: BOOLEAN (not CHAR/INT)
Flags: SMALLINT for enum-like values
JSON: JSONB (not TEXT)
Large text: TEXT (PostgreSQL handles efficiently)
```

---

## 2. Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER MANAGEMENT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐        ┌──────────────────┐                 │
│  │   users      │◄───────┤   auth_tokens    │                 │
│  ├──────────────┤        ├──────────────────┤                 │
│  │ id (PK)      │        │ id (PK)          │                 │
│  │ email        │        │ user_id (FK)     │                 │
│  │ password     │        │ token_type       │                 │
│  │ role         │        │ token_hash       │                 │
│  │ created_at   │        │ expires_at       │                 │
│  │ updated_at   │        └──────────────────┘                 │
│  │ deleted_at   │                                              │
│  └──────────────┘                                              │
│         │                                                       │
│         │        ┌─────────────────────┐                      │
│         └────────┤ user_preferences    │                      │
│                  ├─────────────────────┤                      │
│                  │ user_id (FK)        │                      │
│                  │ email_frequency     │                      │
│                  │ telegram_id         │                      │
│                  │ telegram_verified   │                      │
│                  │ watchlist_tokens    │                      │
│                  │ quiet_hours_start   │                      │
│                  │ quiet_hours_end     │                      │
│                  │ timezone            │                      │
│                  └─────────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   DATA INGESTION & EVENTS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│         ┌──────────────────────────────────────┐               │
│         │          events                      │               │
│         ├──────────────────────────────────────┤               │
│         │ id (PK, UUID)                        │               │
│         │ source_type (news/social/onchain/...)│               │
│         │ source_name (coindesk/twitter/...)  │               │
│         │ timestamp (UTC)                      │               │
│         │ title                                │               │
│         │ content                              │               │
│         │ entities (JSONB array)               │               │
│         │ metadata (JSONB)                     │               │
│         │ priority (low/medium/high)           │               │
│         │ processed (boolean)                  │               │
│         │ created_at                           │               │
│         └──────────────────────────────────────┘               │
│                      │                                          │
│                      └──┬─┐                                     │
│                         └┼────────────────┐                    │
│                          │                │                    │
│                   ┌──────────────┐  ┌──────────────┐           │
│                   │ event_scores │  │event_analytics│           │
│                   ├──────────────┤  ├──────────────┤           │
│                   │ event_id (FK)│  │ event_id (FK)│           │
│                   │ multi_src    │  │ entity_type  │           │
│                   │ engagement   │  │ entity       │           │
│                   │ bot_score    │  │ mention_count│           │
│                   │ dedup_score  │  │ created_at   │           │
│                   │ final_score  │  └──────────────┘           │
│                   │ updated_at   │                              │
│                   └──────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   ALERTS & DELIVERY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────┐                          │
│  │         alerts                   │                          │
│  ├──────────────────────────────────┤                          │
│  │ id (PK)                          │                          │
│  │ user_id (FK → users)             │                          │
│  │ event_id (FK → events)           │                          │
│  │ priority (HIGH/MEDIUM/LOW)       │                          │
│  │ title                            │                          │
│  │ description                      │                          │
│  │ status (pending/sent/read/dismissed) │                      │
│  │ created_at                       │                          │
│  │ sent_at                          │                          │
│  │ read_at                          │                          │
│  │ dismissed_at                     │                          │
│  └──────────────┬───────────────────┘                          │
│                 │                                               │
│         ┌───────┴────────┐                                     │
│         │                │                                     │
│    ┌────────────────────┐  └─────────────────────┐             │
│    │ alert_deliveries   │    alert_interactions │             │
│    ├────────────────────┤  └─────────────────────┘             │
│    │ id (PK)            │    alert_id (FK)                    │
│    │ alert_id (FK)      │    interaction_type                 │
│    │ channel (email/...)│    timestamp                        │
│    │ status (pending...)│    user_action                      │
│    │ delivered_at       │                                     │
│    │ error_message      │                                     │
│    └────────────────────┘                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   SYSTEM & AUDIT                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────┐                          │
│  │    audit_logs                    │                          │
│  ├──────────────────────────────────┤                          │
│  │ id (PK)                          │                          │
│  │ user_id (FK, nullable)           │                          │
│  │ action (login/update/delete)     │                          │
│  │ resource_type                    │                          │
│  │ changes (JSONB)                  │                          │
│  │ timestamp                        │                          │
│  │ ip_address                       │                          │
│  └──────────────────────────────────┘                          │
│                                                                 │
│  ┌──────────────────────────────────┐                          │
│  │    system_metrics                │                          │
│  ├──────────────────────────────────┤                          │
│  │ id (PK)                          │                          │
│  │ metric_name                      │                          │
│  │ metric_value                     │                          │
│  │ timestamp                        │                          │
│  └──────────────────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Tables & Schemas

### 3.1 Users & Authentication

#### Table: `users`

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hash
    username VARCHAR(50),
    role VARCHAR(20) NOT NULL DEFAULT 'user',  -- user, moderator, admin

    -- Account status
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,

    -- 2FA
    totp_secret VARCHAR(255),  -- Encrypted
    totp_enabled BOOLEAN DEFAULT FALSE,
    backup_codes VARCHAR(255),  -- Encrypted array

    -- Account metadata
    profile_picture_url TEXT,
    bio TEXT,

    CONSTRAINT email_domain CHECK (email LIKE '%@%.%')
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_deleted_at ON users(deleted_at);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
```

#### Table: `refresh_tokens` - JWT Token Management

```sql
CREATE TABLE refresh_tokens (
    id BIGINT PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,  -- SHA256 hash (never store plain token)
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_revoked ON refresh_tokens(revoked) WHERE revoked = FALSE;
```

**Security Notes:**

- Never store full token, only hash
- Used for JWT refresh token rotation
- Revocation possible without re-hashing
- Cleanup job: Delete expired tokens older than 30 days

#### Table: `user_preferences` - Flexible Preference Storage

```sql
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    preferences JSON NOT NULL  -- Flexible preference structure
);

-- Indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
```

**Preference JSON Structure:**

```json
{
  "email_frequency": "daily",       -- 'instant', 'daily', 'weekly', 'never'
  "telegram_verified": true,
  "watchlist_tokens": ["BTC", "ETH"],
  "quiet_hours": {
    "start": "22:00",               -- 24-hour format
    "end": "08:00"
  },
  "timezone": "UTC",
  "share_analytics": true,
  "language": "en"
}
```

**MVP Note:** Flexible JSON structure allows rapid iteration.
**Phase II:** Consider normalizing frequently-queried fields for better performance.

---

### 3.2 Events & Processing

#### Table: `events` - Raw Event Ingestion (MVP Implementation)

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(100) NOT NULL,        -- e.g., 'twitter', 'ethereum', 'coindesk'
    type VARCHAR(100) NOT NULL,           -- e.g., 'news', 'social', 'onchain'
    timestamp DATETIME NOT NULL,          -- When the event occurred
    content JSON NOT NULL,                -- Event payload (flexible structure)
    raw JSON,                             -- Optional: Raw API response for debugging
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes (CRITICAL for performance)
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);  -- Time-range queries
CREATE INDEX idx_events_composite ON events(source, type, timestamp DESC);
```

**Content JSON Structure (Example):**
```json
{
  "title": "Bitcoin ETF Approval",
  "body": "SEC approves first spot Bitcoin ETF",
  "entities": ["BTC", "SEC"],
  "sentiment": "bullish",
  "url": "https://...",
  "author": "coindesk"
}
```

**Design Notes (MVP vs Ideal):**
- MVP: Simple INT PK, flexible JSON for rapid iteration
- Future Phase II: Separate title/content columns, normalized entity extraction
- Partitioning: Add by month if table exceeds 10M rows

#### Table: `processed_events` - Scored & Prioritized Events (MVP Implementation)

```sql
CREATE TABLE processed_events (
    id VARCHAR(255) PRIMARY KEY,         -- Event ID as string
    user_id VARCHAR(255),                -- Optional: For user-specific scoring
    timestamp DATETIME NOT NULL,         -- Original event timestamp
    priority VARCHAR(50),                -- 'high', 'medium', 'low'
    score FLOAT,                         -- Final composite score (0-100)
    
    -- Component scores (0-100)
    multi_source INTEGER,                -- Multi-source verification score
    engagement INTEGER,                  -- Social engagement metrics
    bot INTEGER,                         -- Bot detection score
    dedup INTEGER,                       -- Deduplication/similarity score
    
    -- Original event data
    event_data JSON,                     -- Full event details stored as JSON
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes (CRITICAL for MVP performance)
CREATE INDEX idx_processed_events_user ON processed_events(user_id);
CREATE INDEX idx_processed_events_timestamp ON processed_events(timestamp DESC);
CREATE INDEX idx_processed_events_priority ON processed_events(priority);
CREATE INDEX idx_processed_events_user_priority_time ON processed_events(user_id, priority, timestamp DESC);
```

**Scoring Algorithm (MVP):**
- Each event scored on relevance/importance (0-100)
- Component scores: multi_source, engagement, bot detection, deduplication
- Higher score = higher priority for user alerts
- Phase II: ML model to learn user preferences

---

### 3.3 Alerts & Delivery

#### Table: `alerts` - Alert Records (Current MVP Implementation)

```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,                     -- Foreign key to users (nullable for system alerts)
    event_id INTEGER,                    -- Foreign key to events (nullable for system alerts)
    channels JSON,                       -- Array of delivery channels: ["email", "telegram"]
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'sent', 'failed', 'bounced'
    sent_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes (Important for user alert queries)
CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX idx_alerts_user_created ON alerts(user_id, created_at DESC);
```

**Channels JSON Example:**
```json
[
  {
    "channel": "email",
    "status": "sent",
    "sent_at": "2026-03-25T10:30:00Z"
  },
  {
    "channel": "telegram",
    "status": "pending",
    "retry_count": 0
  }
]
```

**MVP Note:** Simplified channels as JSON array in single table
**Phase II Improvement:** Separate into dedicated `alert_deliveries` table for better queryability and retry management

#### Table: `alert_deliveries` - Future Phase II Enhancement

```sql
-- NOT YET IMPLEMENTED - Planned for Phase II
-- Will separate per-channel delivery tracking from alert metadata

CREATE TABLE alert_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,        -- 'email', 'telegram', 'webhook'
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'sent', 'failed', 'bounced'
    sent_at DATETIME,
    failed_reason TEXT,
    retry_count SMALLINT DEFAULT 0,
    max_retries SMALLINT DEFAULT 3,
    next_retry_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_alert_deliveries_alert ON alert_deliveries(alert_id);
CREATE INDEX idx_alert_deliveries_channel ON alert_deliveries(channel);
CREATE INDEX idx_alert_deliveries_retryable ON alert_deliveries(next_retry_at) 
WHERE status = 'failed';
```

---

### 3.4 System & Audit

#### Table: `user_roles` - Role-Based Access Control

```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer'  -- 'admin', 'moderator', 'viewer'
);

-- Index
CREATE INDEX idx_user_roles_role ON user_roles(role);
```

---

#### Table: `password_reset_tokens` - Secure Password Reset

```sql
CREATE TABLE password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,  -- SHA256 hash (never store plain token)
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX idx_password_reset_user ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_unused ON password_reset_tokens(used, expires_at) 
WHERE used = FALSE;
```

---

#### Table: `audit_logs` - Compliance & Security Audit Trail (Planned)

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- Nullable for system actions
    action VARCHAR(100) NOT NULL,         -- 'login', 'update_prefs', 'delete', etc
    resource_type VARCHAR(100) NOT NULL,  -- 'user', 'alert', 'event'
    resource_id VARCHAR(255),
    old_values JSON,                      -- Previous values (if update)
    new_values JSON,                      -- New values (if update/create)
    ip_address VARCHAR(50),
    user_agent TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_cleanup ON audit_logs(timestamp) 
WHERE timestamp < DATE_ADD(NOW(), INTERVAL -1 YEAR);
```

---

#### Table: `system_metrics` - Performance & Business Metrics (Planned)

```sql
CREATE TABLE system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name VARCHAR(100) NOT NULL,    -- 'events_ingested', 'alerts_sent', 'error_rate'
    metric_value FLOAT NOT NULL,
    tags JSON DEFAULT '{}',               -- Context: {"source": "twitter", "priority": "high"}
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_system_metrics_name_time ON system_metrics(metric_name, timestamp DESC);
CREATE INDEX idx_system_metrics_time ON system_metrics(timestamp DESC);
```

**Example Metrics:**
```sql
INSERT INTO system_metrics (metric_name, metric_value, tags, timestamp) VALUES
  ('events_ingested_total', 1000, '{"source": "twitter"}', NOW()),
  ('alerts_generated', 50, '{"priority": "HIGH"}', NOW()),
  ('alert_delivery_success_rate', 0.98, '{"channel": "email"}', NOW()),
  ('api_response_time_p95', 1.2, '{"endpoint": "/alerts"}', NOW()),
  ('db_query_time_p95', 0.05, '{"query": "get_user_alerts"}', NOW());
```

---

## 4. Implementation Status: MVP vs Phase II

### Current MVP State (March 2026 - v1.0)

**Implemented (5 tables):**
- ✅ `users` - Lean structure with preferences JSON
- ✅ `refresh_tokens` - JWT token management
- ✅ `user_preferences` - Flexible JSON preferences
- ✅ `user_roles` - Simple role assignment
- ✅ `password_reset_tokens` - Secure password resets
- ✅ `events` - Raw event ingestion with flexible JSON
- ✅ `processed_events` - Event scoring & prioritization

**Simplified/Combined (2 tables):**
- ⚠️ `alerts` - Simplified MVP (channels as JSON array)

**Planned for Phase II (3+ tables):**
- ⏳ `alert_deliveries` - Separate per-channel delivery tracking
- ⏳ `event_scores` - Dedicated ML feature table
- ⏳ `event_analytics` - Entity extraction & tracking
- ⏳ `audit_logs` - Full compliance audit trail
- ⏳ `system_metrics` - Observability metrics

### Design Philosophy

| Aspect | MVP Approach | Phase II Direction |
|--------|-------------|-------------------|
| **Schema Flexibility** | JSON for rapid iteration | Normalized for queries |
| **Storage** | Single alerts table | alert_deliveries separate |
| **Events** | Simple INT PK | Partition if >10M rows |
| **Audit** | Not yet implemented | Full compliance trail |
| **Metrics** | Application-level tracking | Dedicated metrics table |
| **Query Optimization** | Basic indexes | Advanced composite + partial |

### Migration Path (Phase II)

When transitioning from MVP to production scale:

```sql
-- Step 1: Create new normalized tables alongside existing ones
CREATE TABLE new_alert_deliveries (...);

-- Step 2: Migrate data with transformation
INSERT INTO new_alert_deliveries 
  SELECT ... FROM alerts, JSON_EXTRACT(channels, ...);

-- Step 3: Update application code to write to both (dual-write)
-- Application: Write to alerts + new_alert_deliveries

-- Step 4: Backfill any gaps
INSERT INTO new_alert_deliveries 
  SELECT ... FROM alerts WHERE id > max_migrated_id;

-- Step 5: Verify data consistency
SELECT COUNT(*) FROM alerts;
SELECT COUNT(*) FROM new_alert_deliveries;
-- Should match

-- Step 6: Switch reads to new table
-- Application: Read from new_alert_deliveries

-- Step 7: Sunset old structure (after monitoring)
DROP TABLE alerts_old_backup;
```

---

## 5. Indexing Strategy

### 5.1 Implemented Indexes (MVP)

| Table | Index | Type | Purpose | Status |
|-------|-------|------|---------|--------|
| users | `idx_users_email` | BTREE | User lookup | ✅ |
| users | `idx_users_telegram_id` | BTREE | Telegram user mapping | ✅ |
| refresh_tokens | `idx_refresh_tokens_user_id` | BTREE | User token lookup | ✅ |
| refresh_tokens | `idx_refresh_tokens_expires` | BTREE | Token expiration cleanup | ✅ |
| events | `idx_events_source` | BTREE | Filter by source | ✅ |
| events | `idx_events_type` | BTREE | Filter by type | ✅ |
| events | `idx_events_timestamp` | BTREE | Time-range queries (common) | ✅ |
| events | `idx_events_composite` | BTREE | Multi-column optimization | ✅ |
| processed_events | `idx_processed_user_time` | BTREE | User's recent events | ✅ |
| processed_events | `idx_processed_priority_time` | BTREE | Filter by priority | ✅ |
| alerts | `idx_alerts_user_id` | BTREE | User alert history | ✅ |
| alerts | `idx_alerts_created` | BTREE | Time-ordered queries | ✅ |
| alerts | `idx_alerts_user_created` | BTREE | User's recent alerts | ✅ |
| user_roles | `idx_user_roles_role` | BTREE | Role-based lookups | ✅ |

### 5.2 Composite Indexes (Query Optimization)

**Best Practices:**

- Order columns by selectivity (most selective first)
- Include WHERE clause conditions in index definition
- Use INCLUDE for covering indexes (PG 12+)

**Example: High-value index for alert queries**

```sql
-- Query: SELECT * FROM alerts WHERE user_id=X ORDER BY created_at DESC
CREATE INDEX idx_alerts_user_created ON alerts(user_id, created_at DESC);
```

### 5.3 Maintenance Operations

**Monitor Index Health:**

```sql
-- Find unused indexes (potential cleanup)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Identify bloated indexes (need REINDEX)
SELECT schemaname, tablename, indexname, 
       round(pg_relation_size(indexrelid)/1024/1024::numeric, 2) as size_mb
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Scheduled Maintenance:**

```bash
# Weekly: VACUUM to clean up dead rows
VACUUM ANALYZE events;

# Monthly: REINDEX fragmented tables
REINDEX TABLE events;

# Quarterly: Identify & remove unused indexes
DROP INDEX idx_unused_index_name;
```

---

## 6. Performance Optimization

### 5.1 Query Optimization Patterns

**Pattern 1: Get recent alerts for user**

```sql
-- ❌ SLOW: Full scan
SELECT * FROM alerts WHERE user_id = 123 ORDER BY created_at DESC LIMIT 20;

-- ✅ FAST: Use composite index
CREATE INDEX idx_alerts_user_created ON alerts(user_id, created_at DESC);
SELECT * FROM alerts WHERE user_id = 123 ORDER BY created_at DESC LIMIT 20;
-- Uses index scan, <50ms
```

**Pattern 2: Deduplication check**

```sql
-- ❌ SLOW: Full table scan of events
SELECT * FROM events WHERE content_hash = 'abc123def';

-- ✅ FAST: Use content_hash index + 60-minute window
CREATE INDEX idx_events_dedup ON events(content_hash, created_at DESC)
WHERE created_at > NOW() - INTERVAL '1 hour';

SELECT * FROM events
WHERE content_hash = 'abc123def'
AND created_at > NOW() - INTERVAL '1 hour';
-- Uses index, <10ms
```

**Pattern 3: Filter by priority (low selectivity)**

```sql
-- ❌ Might be SLOW: Index may still scan many rows
SELECT * FROM alerts WHERE priority = 'HIGH' LIMIT 1000;

-- ✅ BETTER: Partial index on just HIGH priority
CREATE INDEX idx_alerts_high_priority ON alerts(created_at DESC)
WHERE priority = 'HIGH';

SELECT * FROM alerts WHERE priority = 'HIGH' ORDER BY created_at DESC LIMIT 1000;
-- Smaller index, faster scan
```

### 5.2 Connection Pooling

**Configuration:**

```yaml
# PgBouncer connection pooling (recommended for production)
[databases]
aeterna = host=prod-db.internal port=5432 dbname=aeterna user=app

[pgbouncer]
pool_mode = transaction  # Lowest latency for our use case
max_client_conn = 1000
default_pool_size = 20  # Per-app-instance
reserve_pool_size = 5
reserve_pool_timeout = 3
```

**Benefits:**

- Reduces overhead (new connections expensive)
- Limits total DB connections
- Improves latency (reuse existing connections)

### 5.3 Query Cache with Redis

**Strategy:**

- Cache frequently accessed data (user preferences, recent alerts)
- Invalidate on update
- TTL: varies by data freshness requirement

**Implementation:**

```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(host='cache', port=6379, decode_responses=True)

def get_user_preferences(user_id: int) -> dict:
    # Try cache first
    cache_key = f"user_prefs:{user_id}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # Cache miss: fetch from DB
    prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()
    prefs_dict = prefs.to_dict()

    # Store in cache (1 hour TTL)
    redis_client.setex(cache_key, timedelta(hours=1), json.dumps(prefs_dict))

    return prefs_dict

def invalidate_user_preferences(user_id: int):
    """Call this whenever user updates preferences"""
    redis_client.delete(f"user_prefs:{user_id}")
```

---

## 7. Query Patterns & Examples

### 6.1 Common Queries (with execution plans)

**Query 1: Get user's pending alerts**

```sql
SELECT a.id, a.title, a.description, a.created_at, e.title as event_title
FROM alerts a
JOIN events e ON a.event_id = e.id
WHERE a.user_id = 123 AND a.status = 'pending'
ORDER BY a.created_at DESC
LIMIT 20;

-- Execution Plan:
-- Limit (cost=0.56..21.37 rows=20)
--   Sort (cost=0.56..21.37 rows=50)
--     Nested Loop (cost=0.42..20.87 rows=50)
--       Index Scan using idx_alerts_user_status_created (cost=0.14..0.32 rows=50)
--         Index Cond: (user_id = 123 AND status = 'pending')
--       Index Scan using events_pkey (cost=0.28..0.40 rows=1)
--         Index Cond: (id = a.event_id)
-- Time: 12ms
```

**Query 2: Find duplicate events (deduplication)**

```sql
SELECT e1.id, e1.content_hash, COUNT(*) as duplicate_count
FROM events e1
WHERE e1.created_at > NOW() - INTERVAL '1 hour'
GROUP BY e1.content_hash
HAVING COUNT(*) > 1;

-- With index: <50ms
-- Without index: >2000ms
```

**Query 3: Get recent HIGH priority alerts with aggregation**

```sql
SELECT
  DATE_TRUNC('hour', a.created_at) as hour,
  COUNT(*) as alert_count,
  COUNT(CASE WHEN a.read_at IS NOT NULL THEN 1 END) as read_count
FROM alerts a
WHERE a.priority = 'HIGH' AND a.created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', a.created_at)
ORDER BY hour DESC;

-- Execution: <100ms with proper indexes
```

---

## 8. Migration Management

### 7.1 Database Migrations (Alembic)

**Structure:**

```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_alerts_table.py
│   ├── 003_add_indexes.py
│   └── 004_add_audit_logs.py
└── env.py
```

**Creating Migrations:**

```bash
# Auto-generate from ORM models
alembic revision --autogenerate -m "add events table"

# Or manual migration (for complex changes)
alembic revision -m "add custom index"

# Review the migration file before running
cat alembic/versions/001_*.py
```

**Running Migrations:**

```bash
# Development
alembic upgrade head

# Production (with verification)
alembic upgrade +1  # One migration at a time
# Check if successful
SELECT * FROM alembic_version;

# Rollback (if needed)
alembic downgrade -1
```

### 7.2 Migration Safety Guidelines

**Rules:**

1. ✅ Always test on staging first
2. ✅ Create backup before large migrations
3. ✅ Use zero-downtime migrations for production tables
4. ✅ Add indexes CONCURRENTLY (don't lock table)
5. ✅ Drop columns only after dual-write period

**Zero-Downtime Migration Example:**

```python
# Migration: Add new indexed column
def upgrade():
    # 1) Add column (doesn't lock for long)
    op.add_column('alerts', sa.Column('new_field', sa.String(), nullable=True))

    # 2) Create index CONCURRENTLY (no locks)
    op.create_index('idx_alerts_new_field', 'alerts', ['new_field'],
                   postgresql_concurrently=True)

def downgrade():
    op.drop_index('idx_alerts_new_field', postgresql_concurrently=True)
    op.drop_column('alerts', 'new_field')
```

---

## 9. Backup & Recovery Integration

### 8.1 Backup Strategy (Coordinated with Deployment)

**Daily Backup:**

```bash
# Run daily at 2 AM UTC
pg_dump -h prod-db -U postgres aeterna | gzip > backup_$(date +%Y%m%d).sql.gz

# Replicate to S3 (cross-region)
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://aeterna-backups/

# Keep 30-day retention
aws s3 ls s3://aeterna-backups/ | awk '{print $4}' | tail -n +31 | xargs -I {} aws s3 rm s3://aeterna-backups/{}
```

**Point-in-Time Recovery (PITR):**

```bash
# Restore to specific time
pg_basebackup -h prod-db -D /var/lib/postgresql/recovery_backup
# Then restore from WAL archives to desired timestamp
```

### 8.2 Restore Verification

**After Restore:**

```bash
# 1) Check row counts
psql -d aeterna_restored -c "SELECT TABLE_NAME, COUNT(*) FROM information_schema.tables..."

# 2) Verify indexes exist
psql -d aeterna_restored -c "SELECT indexname FROM pg_indexes WHERE schemaname='public';"

# 3) Run integrity checks
psql -d aeterna_restored -c "REINDEX DATABASE aeterna_restored;"
```

---

## 10. Size & Growth Projections

### 9.1 Table Growth Estimates

| Table        | Rows/Month | Size/Month | Est. Size Month 3 |
| ------------ | ---------- | ---------- | ----------------- |
| events       | 1,000,000  | 500 MB     | 1.5 GB            |
| alerts       | 50,000     | 50 MB      | 150 MB            |
| users        | 500        | <1 MB      | 1 MB              |
| audit_logs   | 200,000    | 100 MB     | 300 MB            |
| event_scores | 1,000,000  | 200 MB     | 600 MB            |
| **Total**    |            |            | **~3 GB**         |

### 9.2 Scaling Thresholds

| Metric                 | Threshold   | Action                              |
| ---------------------- | ----------- | ----------------------------------- |
| DB size                | >10 GB      | Add read replicas                   |
| Connections            | >80         | Increase pool size or add PgBouncer |
| Query latency p95      | >2 seconds  | Add indexes or scale up             |
| Alert delivery latency | >30 seconds | Scale Celery workers                |

---

## 11. Operational Checklists

### 10.1 Database Pre-Launch Checklist

- [ ] All tables created & verified
- [ ] Primary & foreign keys set up
- [ ] Indexes created & tested
- [ ] Row-level security configured (if needed)
- [ ] Backup strategy tested
- [ ] Restore procedure tested
- [ ] Capacity sizing verified
- [ ] Connection pooling configured
- [ ] Query plans reviewed (via EXPLAIN)
- [ ] Performance tested under load

### 10.2 Monthly Maintenance Checklist

- [ ] Review query performance (slow queries)
- [ ] Reindex bloated tables
- [ ] Update statistics (ANALYZE)
- [ ] Check index usage (remove unused)
- [ ] Verify backup integrity
- [ ] Test restore procedure
- [ ] Monitor growth rate

---

## Conclusion

AETERNA's database is optimized for:

- **Speed:** Composite indexes on common queries
- **Scale:** Partition strategy for large tables
- **Reliability:** Automated backups, PITR support
- **Monitoring:** Instrumentation for production visibility

Keep this document updated as schema evolves!
