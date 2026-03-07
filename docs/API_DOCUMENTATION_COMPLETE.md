# AETERNA Complete API Documentation

**API Base URL:** `https://aeterna-autonomous-alpha-engine.onrender.com`  
**Frontend URL:** `https://aeterna-fronend.vercel.app`  
**Version:** 1.0.0 (Production-Ready)  
**Last Updated:** March 7, 2026

> **For Frontend Integration:** This API is deployed on Render and supports CORS for Vercel frontend.
> Set `VITE_API_URL=https://aeterna-autonomous-alpha-engine.onrender.com` in your frontend `.env`

---

## Table of Contents

1. [Quick Start (Frontend)](#quick-start-frontend)
2. [System & Health](#system--health)
3. [Authentication & Identity](#authentication--identity)
4. [Events (Ingestion)](#events-ingestion)
5. [Alerts](#alerts)
6. [Admin Module](#admin-module)
7. [WebSocket (Real-time)](#websocket-real-time)
8. [Error Codes](#error-codes)
9. [Rate Limiting](#rate-limiting)
10. [Frontend Examples](#frontend-examples)

---

## Quick Start (Frontend)

### 1. Setup Environment Variables

**.env (or .env.local for Vite)**

```env
VITE_API_URL=https://aeterna-autonomous-alpha-engine.onrender.com
VITE_SOCKET_URL=https://aeterna-autonomous-alpha-engine.onrender.com
```

### 2. Make Your First Request

```javascript
// Get crypto news events (no auth required)
fetch(
  "https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/events?limit=20",
)
  .then((r) => r.json())
  .then((data) => console.log(data));
```

### 3. User Registration & Login

```javascript
// Register
fetch("https://aeterna-autonomous-alpha-engine.onrender.com/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "user@example.com",
    password: "securepassword123",
  }),
})
  .then((r) => r.json())
  .then((data) => localStorage.setItem("token", data.access_token));

// Login
fetch("https://aeterna-autonomous-alpha-engine.onrender.com/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: `username=user@example.com&password=securepassword123`,
})
  .then((r) => r.json())
  .then((data) => localStorage.setItem("token", data.access_token));
```

### 4. Protected API Calls (with auth)

```javascript
const token = localStorage.getItem("token");
fetch(
  "https://aeterna-autonomous-alpha-engine.onrender.com/api/alerts/history",
  {
    headers: { Authorization: `Bearer ${token}` },
  },
)
  .then((r) => r.json())
  .then((data) => console.log(data));
```

### 5. Check Automatic Updates Status

```javascript
fetch(
  "https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/auto-update-status",
)
  .then((r) => r.json())
  .then((status) => {
    if (status.auto_updates_enabled) {
      console.log("✅ Automatic updates running every 60 seconds");
    }
  });
```

---

## System & Health

### Get Root Endpoint

**Endpoint:** `GET /`

**Description:** Welcome message and API info

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "message": "Welcome to AETERNA Autonomous Alpha Engine API"
}
```

---

### Get Health Status

**Endpoint:** `GET /health`

**Description:** Simple health check for load balancers

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

---

### Get System Health Check

**Endpoint:** `GET /health/system`

**Description:** Comprehensive system health check of all dependencies

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "rabbitmq": "✅ Connected",
  "redis": "✅ Connected",
  "postgresql": "✅ Connected"
}
```

**Error Response:** `503 Service Unavailable`

```json
{
  "rabbitmq": "❌ Connection refused",
  "redis": "✅ Connected",
  "postgresql": "❌ Connection timeout"
}
```

---

### Get Prometheus Metrics

**Endpoint:** `GET /metrics`

**Description:** Prometheus format metrics for monitoring

**Authentication:** Not required

**Response:** `200 OK` (Prometheus text format)

```
# HELP aeterna_api_requests_total Total API Requests
# TYPE aeterna_api_requests_total counter
aeterna_api_requests_total{endpoint="/ingestion/events"} 1234.0
aeterna_api_requests_total{endpoint="/auth/login"} 56.0
```

---

## Authentication & Identity

### Register User

**Endpoint:** `POST /auth/register`

**Description:** Create a new user account

**Authentication:** Not required

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNoIn...",
  "token_type": "bearer"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Email already registered"
}
```

---

### Login

**Endpoint:** `POST /auth/login`

**Description:** Authenticate user and get JWT tokens

**Authentication:** Not required

**Request Body:**

```
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNoIn...",
  "token_type": "bearer"
}
```

**Error Response:** `401 Unauthorized`

```json
{
  "detail": "Invalid credentials"
}
```

**Token Details:**

- `access_token`: Expires in 24 hours
- `refresh_token`: Expires in 30 days
- Both are JWT tokens containing user ID in "sub" claim

---

### Refresh Access Token

**Endpoint:** `POST /auth/refresh`

**Description:** Get new access token using refresh token

**Authentication:** Not required

**Request Body:**

```json
{
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNoIn..."
}
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc... (new token)",
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNoIn... (new token)",
  "token_type": "bearer"
}
```

**Error Response:** `401 Unauthorized`

```json
{
  "detail": "Invalid refresh token"
}
```

---

### Get User Profile

**Endpoint:** `GET /auth/profile`

**Description:** Get current authenticated user's profile

**Authentication:** Required (Bearer token)

**Response:** `200 OK`

```json
{
  "id": 1,
  "email": "user@example.com",
  "telegram_id": "123456789",
  "preferences": {
    "notifications_enabled": true,
    "email_frequency": "immediate"
  },
  "created_at": "2026-02-15T10:00:00",
  "email_verified": true
}
```

**Error Response:** `401 Unauthorized`

```json
{
  "detail": "Not authenticated"
}
```

---

### Update User Profile

**Endpoint:** `PATCH /auth/profile`

**Description:** Update user profile (Telegram ID, preferences)

**Authentication:** Required (Bearer token)

**Request Body:**

```json
{
  "telegram_id": "987654321",
  "preferences": {
    "notifications_enabled": true,
    "email_frequency": "daily_digest"
  }
}
```

**Response:** `200 OK` (Updated profile object)

---

### Request Password Reset

**Endpoint:** `POST /auth/password-reset/request`

**Description:** Request a password reset (email-only token)

**Authentication:** Not required

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`

```json
{
  "message": "If an account with this email exists, a password reset link has been sent. Check your email.",
  "email": "user@example.com"
}
```

**Security Note:** Reset token is sent ONLY via email, not in response. This prevents interception.

---

### Confirm Password Reset

**Endpoint:** `POST /auth/password-reset/confirm`

**Description:** Confirm password reset with token from email

**Authentication:** Not required

**Request Body:**

```json
{
  "token": "reset_token_from_email",
  "new_password": "newpassword123"
}
```

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Password updated successfully"
}
```

---

### Unsubscribe from Emails

**Endpoint:** `GET /auth/unsubscribe`

**Description:** Unsubscribe from email notifications

**Authentication:** Not required

**Query Parameters:**

| Parameter | Type   | Required | Description                  |
| --------- | ------ | -------- | ---------------------------- |
| email     | string | Yes      | Email address to unsubscribe |

**Response:** `200 OK` (HTML response)

```html
<h3>You have been unsubscribed from all emails.</h3>
```

---

## Events (Ingestion)

### Health Check (Ingestion)

**Endpoint:** `GET /ingestion/health`

**Description:** Ingestion module health check

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

---

### Create Event

**Endpoint:** `POST /ingestion/events`

**Description:** Create a new event via API

**Authentication:** Not required

**Request Body:**

```json
{
  "source": "coindesk",
  "type": "news",
  "content": {
    "title": "Bitcoin Price Update",
    "summary": "Bitcoin reaches new high",
    "link": "https://coindesk.com/..."
  }
}
```

**Response:** `201 Created`

```json
{
  "id": 123,
  "source": "coindesk",
  "type": "news",
  "timestamp": "2026-03-06T15:30:00",
  "content": {
    "title": "Bitcoin Price Update",
    "summary": "Bitcoin reaches new high",
    "link": "https://coindesk.com/..."
  }
}
```

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Failed to store event: Invalid content format"
}
```

---

### List All Events

**Endpoint:** `GET /ingestion/events`

**Description:** Retrieve all ingested events with optional filtering

**Authentication:** Not required (public)

**Query Parameters:**

| Parameter  | Type              | Required | Description                | Example               |
| ---------- | ----------------- | -------- | -------------------------- | --------------------- |
| skip       | integer           | No       | Offset for pagination      | `0`                   |
| limit      | integer           | No       | Results per page (max 500) | `100`                 |
| source     | string            | No       | Filter by source           | `coindesk`            |
| type       | string            | No       | Filter by type             | `news`                |
| start_date | string (ISO 8601) | No       | Events after date          | `2026-03-01T00:00:00` |
| end_date   | string (ISO 8601) | No       | Events before date         | `2026-03-02T00:00:00` |

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "source": "coindesk",
    "type": "news",
    "timestamp": "2026-03-01T15:30:00",
    "content": {
      "title": "Bitcoin Reaches New High",
      "summary": "Bitcoin price surges past $50,000",
      "link": "https://coindesk.com/..."
    }
  },
  {
    "id": 2,
    "source": "coingecko",
    "type": "price",
    "timestamp": "2026-03-01T15:35:00",
    "content": {
      "symbol": "BTC",
      "price": 50234.5,
      "change_24h": 3.45
    }
  }
]
```

---

### Get Single Event

**Endpoint:** `GET /ingestion/events/{event_id}`

**Description:** Retrieve a specific event by ID

**Authentication:** Not required

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| event_id  | integer | Event ID    |

**Response:** `200 OK`

```json
{
  "id": 1,
  "source": "coindesk",
  "type": "news",
  "timestamp": "2026-03-01T15:30:00",
  "content": {
    "title": "Bitcoin Reaches New High",
    "summary": "Bitcoin price surges past $50,000",
    "link": "https://coindesk.com/..."
  }
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Event not found"
}
```

---

### Get Events by Source

**Endpoint:** `GET /ingestion/search/by-source/{source}`

**Description:** Filter events by collection source

**Authentication:** Not required

**Path Parameters:**

| Parameter | Type   | Description                                               |
| --------- | ------ | --------------------------------------------------------- |
| source    | string | Source name (e.g., "coindesk", "coingecko", "decrypt.co") |

**Query Parameters:**

| Parameter | Type    | Description                |
| --------- | ------- | -------------------------- |
| skip      | integer | Pagination offset          |
| limit     | integer | Results per page (max 500) |

**Response:** `200 OK` (Array of events)

**Example:**

```bash
curl "https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/search/by-source/coindesk?limit=10"
```

---

### Get Events by Type

**Endpoint:** `GET /ingestion/search/by-type/{event_type}`

**Description:** Filter events by type

**Authentication:** Not required

**Path Parameters:**

| Parameter  | Type   | Description             |
| ---------- | ------ | ----------------------- |
| event_type | string | Type: "news" or "price" |

**Query Parameters:**

| Parameter | Type    | Description                |
| --------- | ------- | -------------------------- |
| skip      | integer | Pagination offset          |
| limit     | integer | Results per page (max 500) |

**Response:** `200 OK` (Array of events)

---

### Get Event Statistics

**Endpoint:** `GET /ingestion/stats`

**Description:** Get aggregated statistics about collected events

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "total_events": 3400,
  "by_source": {
    "coindesk": 1200,
    "cointelegraph": 1100,
    "decrypt.co": 1100
  },
  "by_type": {
    "news": 3400,
    "price": 0
  }
}
```

---

### Check Auto-Update Status

**Endpoint:** `GET /ingestion/auto-update-status`

**Description:** Check if automatic RSS collection and event processing is running

**Authentication:** Not required (public)

**Response:** `200 OK` (Active)

```json
{
  "status": "active",
  "auto_updates_enabled": true,
  "update_frequency": {
    "rss_collection": "every 60 seconds",
    "consumer_processing": "every 3 seconds (50 messages per batch)",
    "price_collection": "every 120 seconds"
  },
  "last_event_timestamp": "2026-03-06T12:37:45",
  "message": "🔄 Automatic updates RUNNING - new events fetched every 60 seconds"
}
```

**Response:** `200 OK` (Inactive)

```json
{
  "status": "inactive",
  "auto_updates_enabled": false,
  "message": "⚠️  Scheduler not running"
}
```

**What This Means:**

- ✅ **Active:** New crypto news is automatically fetched every 60 seconds from CoinDesk, CoinTelegraph, Decrypt
- ✅ **Active:** Events are continuously processed from queue every 3 seconds
- ❌ **Inactive:** Manual collection needed (contact backend team)

---

## Alerts

### 📢 Alert System Overview

**Automatic Alert Generation:**

- ✅ HIGH and MEDIUM priority events automatically generate alerts
- ✅ Alerts created by intelligence pipeline (Agent A scoring)
- ✅ **Broadcast alerts** (user_id=0) visible to all users
- ✅ Rate limiting: 10 alerts per user per hour
- ✅ Quiet hours respected (if configured in user preferences)

**Alert Flow:**

```
Event scored by Agent A
  ↓ (if HIGH/MEDIUM priority)
  ↓
Automatic alert generated (user_id=0 = system broadcast)
  ↓
Available via /api/alerts/history for all authenticated users
```

**Alert Status Values:**

- `pending` - New alert not yet viewed
- `read` - User has viewed the alert
- `dismissed` - User dismissed the alert

---

### Get Alert History

**Endpoint:** `GET /api/alerts/history`

**Description:** Get alerts for the authenticated user with filtering (includes personal + broadcast alerts)

**Authentication:** Required (Bearer token)

**Important:** This endpoint returns both:

- Personal alerts assigned to your user ID
- **Broadcast alerts** (user_id=0) created by the system for all users

**Query Parameters:**

| Parameter  | Type              | Description                             |
| ---------- | ----------------- | --------------------------------------- |
| skip       | integer           | Pagination offset (default: 0)          |
| limit      | integer           | Results per page (default: 20, max: 50) |
| priority   | string            | Filter: "HIGH", "MEDIUM", "LOW"         |
| start_date | string (ISO 8601) | Alerts after date                       |
| end_date   | string (ISO 8601) | Alerts before date                      |

**Response:** `200 OK`

```json
[
  {
    "alert_id": "1",
    "created_at": "2026-03-01T15:30:00",
    "title": "alert_1",
    "priority": "HIGH",
    "entity": null,
    "status": "pending",
    "read_at": null
  },
  {
    "alert_id": "2",
    "created_at": "2026-03-01T15:35:00",
    "title": "alert_2",
    "priority": "MEDIUM",
    "entity": null,
    "status": "read",
    "read_at": "2026-03-01T15:40:00"
  }
]
```

**Error Response:** `401 Unauthorized`

```json
{
  "detail": "Not authenticated"
}
```

---

### Get Single Alert

**Endpoint:** `GET /api/alerts/{alert_id}`

**Description:** Get a specific alert

**Authentication:** Required

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| alert_id  | integer | Alert ID    |

**Response:** `200 OK` (Single alert object)

**Error Response:** `404 Not Found` or `403 Forbidden`

```json
{
  "detail": "Alert not found or access denied"
}
```

---

### Mark Alert as Read

**Endpoint:** `PATCH /api/alerts/{alert_id}`

**Description:** Mark an alert as read

**Authentication:** Required

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| alert_id  | integer | Alert ID    |

**Response:** `200 OK`

```json
{
  "alert_id": "1",
  "created_at": "2026-03-01T15:30:00",
  "title": "alert_1",
  "priority": "HIGH",
  "entity": null,
  "status": "read",
  "read_at": "2026-03-01T16:30:00"
}
```

---

### Dismiss Alert

**Endpoint:** `DELETE /api/alerts/{alert_id}`

**Description:** Dismiss/delete an alert

**Authentication:** Required

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| alert_id  | integer | Alert ID    |

**Response:** `200 OK`

```json
{
  "detail": "Alert dismissed successfully"
}
```

---

### Export Alert History as CSV

**Endpoint:** `GET /api/alerts/history/export`

**Description:** Export alerts as CSV file for download

**Authentication:** Required

**Query Parameters:** Same as `/api/alerts/history`

**Response:** `200 OK` (CSV file download)

**CSV Format:**

```
alert_id,created_at,title,priority,status
1,2026-03-01T15:30:00,alert_1,HIGH,pending
2,2026-03-01T15:35:00,alert_2,MEDIUM,read
```

---

### 🔧 Diagnostic Endpoints (Admin Only)

#### Get All Alerts in System

**Endpoint:** `GET /api/alerts/diagnostics/all`

**Description:** Admin-only endpoint to view all alerts in system for debugging

**Authentication:** Required + Admin role

**Query Parameters:**

| Parameter | Type    | Description                           |
| --------- | ------- | ------------------------------------- |
| limit     | integer | Max results (default: 100, max: 1000) |
| skip      | integer | Pagination offset (default: 0)        |

**Response:** `200 OK`

```json
{
  "total": 2500,
  "returned": 100,
  "skip": 0,
  "limit": 100,
  "alerts": [
    {
      "id": 1,
      "user_id": 0,
      "event_id": "abc123def456",
      "priority": "HIGH",
      "status": "pending",
      "created_at": "2026-03-06T15:30:00",
      "channels": ["email", "web"]
    },
    {
      "id": 2,
      "user_id": 5,
      "event_id": "xyz789uvw000",
      "priority": "MEDIUM",
      "status": "read",
      "created_at": "2026-03-06T15:35:00",
      "channels": ["web"]
    }
  ]
}
```

**Note:** This includes both personal alerts and broadcast alerts (user_id=0)

---

#### Get Alerts for Specific User

**Endpoint:** `GET /api/alerts/diagnostics/user/{user_id}`

**Description:** Admin-only endpoint to view all alerts for a specific user

**Authentication:** Required + Admin role

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| user_id   | integer | User ID     |

**Query Parameters:**

| Parameter | Type    | Description                           |
| --------- | ------- | ------------------------------------- |
| limit     | integer | Max results (default: 100, max: 1000) |
| skip      | integer | Pagination offset (default: 0)        |

**Response:** `200 OK`

```json
{
  "user_id": 5,
  "total": 45,
  "returned": 45,
  "skip": 0,
  "limit": 100,
  "alerts": [
    {
      "id": 12,
      "user_id": 5,
      "event_id": "evt001",
      "priority": "HIGH",
      "status": "read",
      "created_at": "2026-03-06T14:00:00",
      "channels": ["email"],
      "is_broadcast": false
    },
    {
      "id": 15,
      "user_id": 0,
      "event_id": "evt002",
      "priority": "MEDIUM",
      "status": "pending",
      "created_at": "2026-03-06T14:05:00",
      "channels": ["web"],
      "is_broadcast": true
    }
  ]
}
```

**Note:**

- `is_broadcast: true` = system broadcast alert (user_id=0) visible to all users
- `is_broadcast: false` = personal alert assigned to user

---

## Admin Module

### ⚠️ Admin Security Overview

**Role-Based Access Control (RBAC):**

- Only users with `admin` role can access `/api/admin/*` endpoints
- All requests require valid JWT token + admin role check
- Non-admins get `403 Forbidden` error
- Invalid tokens get `401 Unauthorized` error
- Bootstrap endpoint creates the first admin (one-time only)

**Protected Endpoints:**

- ✅ `POST /api/bootstrap/create-first-admin` - Create first admin (token-protected)
- ✅ `GET /api/admin/users/` - List all users
- ✅ `GET /api/admin/users/{user_id}` - Get user details
- ✅ `PATCH /api/admin/users/{user_id}/toggle` - Toggle user active status
- ✅ `GET /api/admin/metrics` - System metrics
- ✅ `GET /api/admin/roles/` - List all roles
- ✅ `GET /api/admin/roles/admins` - List admins only
- ✅ `GET /api/admin/roles/{user_id}` - Get user's role
- ✅ `POST /api/admin/roles/{user_id}/assign` - Assign role
- ✅ `DELETE /api/admin/roles/{user_id}/remove` - Remove role
- ✅ `GET /api/admin/protected/secret` - Admin-only test endpoint
- ✅ `GET /api/alerts/diagnostics/all` - View all system alerts (debug)
- ✅ `GET /api/alerts/diagnostics/user/{user_id}` - View user's alerts (debug)

---

### Bootstrap: Creating the First Admin

**Problem:** How to create the first admin if no admin exists yet?

**Solution:** Use the bootstrap endpoint ONE TIME during initial setup.

#### Step 1: Set Environment Variable (Render)

```bash
BOOTSTRAP_TOKEN=your-secret-bootstrap-token-12345
```

#### Step 2: Call Bootstrap Endpoint (ONCE ONLY)

**Endpoint:** `POST /api/bootstrap/create-first-admin`

**Description:** Create the first admin user (one-time only)

**Authentication:** Not required (but BOOTSTRAP_TOKEN must match)

**Request Body:**

```json
{
  "user_id": 2,
  "bootstrap_token": "your-secret-bootstrap-token-12345"
}
```

**Response:** `200 OK`

```json
{
  "status": "success",
  "message": "✅ User 2 (user@example.com) is now ADMIN",
  "user_id": 2,
  "email": "user@example.com",
  "role": "admin",
  "warning": "⚠️ This endpoint is now DISABLED (bootstrap disabled)"
}
```

**Error Response:** `403 Forbidden`

```json
{
  "detail": "Invalid bootstrap token"
}
```

**Important:** After the first admin is created, the bootstrap endpoint becomes **permanently disabled** for security. No other user can use it.

---

### List All Users

**Endpoint:** `GET /api/admin/users/`

**Description:** List all users in the system

**Authentication:** Required + Admin role

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "email": "admin@example.com",
    "active": true,
    "created_at": "2026-02-15T10:00:00"
  },
  {
    "id": 2,
    "email": "user@example.com",
    "active": true,
    "created_at": "2026-02-16T11:00:00"
  }
]
```

**Error Response:** `401 Unauthorized` or `403 Forbidden`

```json
{
  "detail": "Not authenticated" | "Access denied - admin role required"
}
```

---

### Get User Details

**Endpoint:** `GET /api/admin/users/{user_id}`

**Description:** Get detailed information about a specific user

**Authentication:** Required + Admin role

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| user_id   | integer | User ID     |

**Response:** `200 OK`

```json
{
  "id": 2,
  "email": "user@example.com",
  "active": true,
  "created_at": "2026-02-16T11:00:00",
  "telegram_id": "123456789",
  "preferences": {
    "notifications_enabled": true,
    "email_frequency": "daily"
  }
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "User not found"
}
```

---

### Toggle User Active Status

**Endpoint:** `PATCH /api/admin/users/{user_id}/toggle`

**Description:** Toggle user email_verified (active) status

**Authentication:** Required + Admin role

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| user_id   | integer | User ID     |

**Response:** `200 OK`

```json
{
  "id": 2,
  "active": false
}
```

---

### Get System Metrics

**Endpoint:** `GET /api/admin/metrics`

**Description:** Get admin dashboard metrics

**Authentication:** Required + Admin role

**Response:** `200 OK`

```json
{
  "events_ingested_hourly": 120,
  "events_ingested_daily": 2400,
  "events_processed": 2300,
  "alerts_generated": 500,
  "active_users": 42,
  "system_uptime": "3 days, 4 hours",
  "error_rate": 0.01
}
```

---

### List All Roles

**Endpoint:** `GET /api/admin/roles/`

**Description:** List all user role assignments

**Authentication:** Required + Admin role

**Response:** `200 OK`

```json
{
  "total": 2,
  "roles": [
    {
      "user_id": 1,
      "email": "admin@example.com",
      "role": "admin"
    },
    {
      "user_id": 2,
      "email": "user@example.com",
      "role": "viewer"
    }
  ]
}
```

---

### List Only Admins

**Endpoint:** `GET /api/admin/roles/admins`

**Description:** List only users with admin role

**Authentication:** Required + Admin role

**Response:** `200 OK`

```json
{
  "total": 1,
  "admins": [
    {
      "user_id": 1,
      "email": "admin@example.com",
      "role": "admin"
    }
  ]
}
```

---

### Get User's Current Role

**Endpoint:** `GET /api/admin/roles/{user_id}`

**Description:** Check a specific user's role

**Authentication:** Required + Admin role

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| user_id   | integer | User ID     |

**Response:** `200 OK`

```json
{
  "user_id": 2,
  "email": "user@example.com",
  "role": "viewer",
  "has_admin": false
}
```

---

### Assign Role to User

**Endpoint:** `POST /api/admin/roles/{user_id}/assign`

**Description:** Assign a role to a user

**Authentication:** Required + Admin role

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| user_id   | integer | User ID     |

**Request Body:**

```json
{
  "role": "admin"
}
```

**Response:** `200 OK`

```json
{
  "user_id": 3,
  "email": "newadmin@example.com",
  "role": "admin",
  "message": "✅ User assigned admin role"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Invalid role name. Use: admin, viewer, editor"
}
```

---

### Remove Role from User

**Endpoint:** `DELETE /api/admin/roles/{user_id}/remove`

**Description:** Remove admin role from user (revert to viewer)

**Authentication:** Required + Admin role

**Path Parameters:**

| Parameter | Type    | Description |
| --------- | ------- | ----------- |
| user_id   | integer | User ID     |

**Response:** `200 OK`

```json
{
  "user_id": 3,
  "email": "newadmin@example.com",
  "role": "viewer",
  "message": "✅ Admin role removed"
}
```

---

### Admin Protected Test Endpoint

**Endpoint:** `GET /api/admin/protected/secret`

**Description:** Admin-only test endpoint with input sanitization

**Authentication:** Required + Admin role

**Query Parameters:**

| Parameter | Type   | Description                    |
| --------- | ------ | ------------------------------ |
| msg       | string | Message to sanitize (optional) |

**Response:** `200 OK`

```json
{
  "message": "This is an admin-only endpoint!"
}
```

**Example with message:**

```bash
curl -H "Authorization: Bearer TOKEN" \
  "https://aeterna-autonomous-alpha-engine.onrender.com/api/admin/protected/secret?msg=Hello%20Admin"
```

---

## WebSocket (Real-time)

### Connect to WebSocket

**Endpoint:** `ws://aeterna-autonomous-alpha-engine.onrender.com/socket.io/`

**Description:** Real-time WebSocket connection for alerts and updates

**Authentication:** JWT token passed in auth payload

**Connection Example (JavaScript):**

```javascript
const socket = io("https://aeterna-autonomous-alpha-engine.onrender.com", {
  auth: {
    token: localStorage.getItem("token"),
  },
});

// Listen for alerts
socket.on("alert", (data) => {
  console.log("New alert:", data);
});

// Heartbeat
socket.on("pong", () => {
  console.log("Pong received");
});

// Send ping
socket.emit("ping");
```

**Events:**

- **alert** - New alert pushed to user
- **pong** - Response to ping (heartbeat)
- **disconnect** - Connection closed

---

## Error Codes

| HTTP Code | Error Code            | Meaning                     | Solution                                             |
| --------- | --------------------- | --------------------------- | ---------------------------------------------------- |
| 400       | `BAD_REQUEST`         | Invalid input               | Check request body and parameters                    |
| 401       | `UNAUTHORIZED`        | Missing or invalid token    | Include valid `Authorization: Bearer <token>` header |
| 403       | `FORBIDDEN`           | Authenticated but no access | Contact admin for role assignment                    |
| 404       | `NOT_FOUND`           | Resource doesn't exist      | Check resource ID is valid                           |
| 409       | `CONFLICT`            | Resource already exists     | Email already registered or duplicate entry          |
| 429       | `RATE_LIMITED`        | Too many requests           | Wait before retrying                                 |
| 500       | `INTERNAL_ERROR`      | Server error                | Contact support team                                 |
| 503       | `SERVICE_UNAVAILABLE` | Dependency down             | Check system status (/health/system)                 |

---

## Rate Limiting

**Global Rate Limit:**

- 100 requests per minute per IP address
- 1000 requests per hour per authenticated user

**Endpoint-Specific Limits:**

- `/auth/login`: 5 attempts per 5 minutes per IP
- `/auth/register`: 3 new accounts per hour per IP
- `/ingestion/events`: 1000 requests per minute
- `/api/alerts/*`: 100 requests per minute per user

**Response Headers:**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1614556800
```

**Rate Limit Exceeded Response:** `429 Too Many Requests`

```json
{
  "detail": "Rate limit exceeded. Retry after 45 seconds"
}
```

---

## Frontend Examples

### JavaScript / Vue / React

```javascript
// 1. Configure API
const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://aeterna-autonomous-alpha-engine.onrender.com";

// 2. Helper function for API calls
async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

// 3. Register user
async function register(email, password) {
  return apiCall("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// 4. Login
async function login(email, password) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `username=${email}&password=${password}`,
  });
  const data = await response.json();
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

// 5. Get events
async function getEvents(limit = 20, source = null) {
  let url = `/ingestion/events?limit=${limit}`;
  if (source) url += `&source=${source}`;
  return apiCall(url);
}

// 6. Get alerts
async function getAlerts() {
  return apiCall("/api/alerts/history?limit=50");
}

// 7. Mark alert as read
async function markAlertRead(alertId) {
  return apiCall(`/api/alerts/${alertId}`, {
    method: "PATCH",
  });
}

// 8. Delete alert
async function deleteAlert(alertId) {
  return apiCall(`/api/alerts/${alertId}`, {
    method: "DELETE",
  });
}

// 9. Get stats
async function getStats() {
  return apiCall("/ingestion/stats");
}

// 10. Auto-update status
async function checkAutoUpdates() {
  return apiCall("/ingestion/auto-update-status");
}

// 11. Get user profile
async function getProfile() {
  return apiCall("/auth/profile");
}

// 12. List admin users (admin only)
async function listAdminUsers() {
  return apiCall("/api/admin/users/");
}
```

### React Hook Example

```javascript
import { useState, useEffect } from "react";

function useEvents(limit = 20) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const data = await apiCall(`/ingestion/events?limit=${limit}`);
        setEvents(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
    // Refresh every 30 seconds
    const interval = setInterval(fetchEvents, 30000);
    return () => clearInterval(interval);
  }, [limit]);

  return { events, loading, error };
}

// Usage
function EventsComponent() {
  const { events, loading, error } = useEvents(20);

  if (loading) return <p>Loading events...</p>;
  if (error) return <p>Error: {error}</p>;

  return (
    <div>
      <h2>Crypto News ({events.length} events)</h2>
      {events.map((event) => (
        <div key={event.id}>
          <h3>{event.content.title}</h3>
          <p>{event.content.summary}</p>
          <small>
            {event.source} • {event.timestamp}
          </small>
        </div>
      ))}
    </div>
  );
}
```

### Python Example

```python
import requests
import os
from datetime import datetime, timedelta

BASE_URL = "https://aeterna-autonomous-alpha-engine.onrender.com"

# 1. Register
def register(email: str, password: str):
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password}
    )
    return response.json()

# 2. Login
def login(email: str, password: str):
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": email, "password": password}
    )
    data = response.json()
    with open(".token", "w") as f:
        f.write(data["access_token"])
    return data

# 3. Get token from storage
def get_token():
    try:
        with open(".token", "r") as f:
            return f.read()
    except:
        return None

# 4. Get headers with auth
def get_headers():
    token = get_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

# 5. Get events
def get_events(limit: int = 20, source: str = None):
    url = f"{BASE_URL}/ingestion/events?limit={limit}"
    if source:
        url += f"&source={source}"
    response = requests.get(url)
    return response.json()

# 6. Get alerts
def get_alerts(limit: int = 50):
    response = requests.get(
        f"{BASE_URL}/api/alerts/history?limit={limit}",
        headers=get_headers()
    )
    return response.json()

# 7. Mark alert as read
def mark_alert_read(alert_id: int):
    response = requests.patch(
        f"{BASE_URL}/api/alerts/{alert_id}",
        headers=get_headers()
    )
    return response.json()

# 8. Get stats
def get_stats():
    response = requests.get(f"{BASE_URL}/ingestion/stats")
    return response.json()

# 9. Check auto-updates
def check_auto_updates():
    response = requests.get(f"{BASE_URL}/ingestion/auto-update-status")
    return response.json()

# 10. Example usage
if __name__ == "__main__":
    # Check stats
    stats = get_stats()
    print(f"Total events: {stats['total_events']}")
    print(f"By source: {stats['by_source']}")

    # Get recent events
    events = get_events(limit=10)
    print(f"Latest events: {len(events)}")

    # Check auto-updates
    status = check_auto_updates()
    print(f"Auto-updates: {status['status']}")
```

### cURL Examples

```bash
# 1. Get events (no auth)
curl https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/events

# 2. Get recent news
curl "https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/events?limit=10&source=coindesk"

# 3. Check stats
curl https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/stats

# 4. Check auto-updates
curl https://aeterna-autonomous-alpha-engine.onrender.com/ingestion/auto-update-status

# 5. Register
curl -X POST https://aeterna-autonomous-alpha-engine.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# 6. Login
curl -X POST https://aeterna-autonomous-alpha-engine.onrender.com/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"

# 7. Get alerts (replace TOKEN)
curl -H "Authorization: Bearer TOKEN" \
  https://aeterna-autonomous-alpha-engine.onrender.com/api/alerts/history

# 8. Get user profile (replace TOKEN)
curl -H "Authorization: Bearer TOKEN" \
  https://aeterna-autonomous-alpha-engine.onrender.com/auth/profile

# 9. List admin users (replace TOKEN)
curl -H "Authorization: Bearer TOKEN" \
  https://aeterna-autonomous-alpha-engine.onrender.com/api/admin/users/

# 10. System health check
curl https://aeterna-autonomous-alpha-engine.onrender.com/health/system
```

---

## Swagger/OpenAPI UI

Interactive API documentation available at:

- **Swagger UI:** `https://aeterna-autonomous-alpha-engine.onrender.com/docs`
- **ReDoc:** `https://aeterna-autonomous-alpha-engine.onrender.com/redoc`

These provide:

- Interactive endpoint testing
- Parameter documentation
- Request/response examples
- Schema definitions
- Real-time API exploration

---

## Summary

**AETERNA API** provides a complete REST API for:

- ✅ Cryptocurrency event ingestion (3,390+ events from 3 sources)
- ✅ **Automatic alerts** - HIGH/MEDIUM priority events auto-generate system broadcast alerts
- ✅ **Broadcast alerts** - System-wide alerts (user_id=0) visible to all users
- ✅ Real-time alerts and notifications
- ✅ User authentication and profile management
- ✅ Admin dashboard and role management with diagnostic tools
- ✅ WebSocket real-time updates
- ✅ CORS enabled for Vercel frontend
- ✅ Rate limiting and security

**Total Endpoints:** 40+  
**Authentication:** JWT tokens (24h access, 30d refresh)  
**Authorization:** Role-based access control (RBAC)  
**Performance:** Sub-100ms response times  
**Uptime:** 99.9% SLA on Render

---

_For questions or issues, please contact the backend team._
