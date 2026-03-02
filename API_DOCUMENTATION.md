# AETERNA API Documentation

**API Base URL:** `http://localhost:8000`  
**Version:** 0.1.0  
**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health & System](#health--system)
3. [Events (Ingestion)](#events-ingestion)
4. [Alerts](#alerts)
5. [Authentication & Identity](#authentication--identity)
6. [Error Codes](#error-codes)
7. [Rate Limiting](#rate-limiting)
8. [Examples](#examples)

---

## Authentication

### OAuth2 Bearer Token

All protected endpoints require an `Authorization` header:

```
Authorization: Bearer <access_token>
```

**Get Token:**

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=password123
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNoIn...",
  "token_type": "bearer"
}
```

---

## Health & System

### Get System Health

**Endpoint:** `GET /health/system`

**Description:** Check health of all system dependencies (RabbitMQ, PostgreSQL, Redis)

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

## Events (Ingestion)

### List All Events

**Endpoint:** `GET /ingestion/events`

**Description:** Retrieve all ingested events with optional filtering

**Authentication:** Not required (public)

**Query Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| skip | integer | No | Offset for pagination | `0` |
| limit | integer | No | Results per page (max 500) | `100` |
| source | string | No | Filter by source | `coindesk` |
| type | string | No | Filter by type | `news` |
| start_date | string (ISO 8601) | No | Events after date | `2026-03-01T00:00:00` |
| end_date | string (ISO 8601) | No | Events before date | `2026-03-02T00:00:00` |

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
    },
    "raw": null
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
    },
    "raw": null
  }
]
```

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Invalid date format. Use ISO 8601: 2026-03-01T00:00:00"
}
```

---

### Get Single Event

**Endpoint:** `GET /ingestion/events/{event_id}`

**Description:** Retrieve a specific event by ID

**Authentication:** Not required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| event_id | integer | Event ID |

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

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| source | string | Source name (e.g., "coindesk", "coingecko") |

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| skip | integer | Pagination offset |
| limit | integer | Results per page (max 500) |

**Response:** `200 OK` (Array of events)

**Example:**

```bash
curl "http://localhost:8000/ingestion/search/by-source/coindesk?limit=10"
```

---

### Get Events by Type

**Endpoint:** `GET /ingestion/search/by-type/{type}`

**Description:** Filter events by type

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| type | string | Type: "news" or "price" |

**Response:** `200 OK` (Array of events)

---

### Get Event Statistics

**Endpoint:** `GET /ingestion/stats`

**Description:** Get aggregated statistics about collected events

**Authentication:** Not required

**Response:** `200 OK`

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

---

## Alerts

### Get Alert History

**Endpoint:** `GET /api/alerts/history`

**Description:** Get alerts for the authenticated user with filtering

**Authentication:** Required (Bearer token)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| skip | integer | Pagination offset (default: 0) |
| limit | integer | Results per page (default: 20, max: 50) |
| priority | string | Filter: "HIGH", "MEDIUM", "LOW" |
| start_date | string (ISO 8601) | Alerts after date |
| end_date | string (ISO 8601) | Alerts before date |

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

**Error Response:** `403 Forbidden`

```json
{
  "detail": "Access denied - different user's alerts"
}
```

---

### Get Single Alert

**Endpoint:** `GET /api/alerts/{alert_id}`

**Description:** Get a specific alert

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| alert_id | integer | Alert ID |

**Response:** `200 OK` (Single alert object)

**Error Response:** `404 Not Found` or `403 Forbidden`

---

### Mark Alert as Read

**Endpoint:** `PATCH /api/alerts/{alert_id}`

**Description:** Mark an alert as read

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| alert_id | integer | Alert ID |

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

### Delete Alert

**Endpoint:** `DELETE /api/alerts/{alert_id}`

**Description:** Dismiss/delete an alert

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| alert_id | integer | Alert ID |

**Response:** `200 OK`

```json
{
  "detail": "Alert dismissed successfully"
}
```

---

### Export Alert History

**Endpoint:** `GET /api/alerts/history/export`

**Description:** Export alerts as CSV file

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

**Description:** Authenticate user and get tokens

**Authentication:** Not required

**Request Body:**

```
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

**Response:** `200 OK` (Same as register)

**Error Response:** `401 Unauthorized`

```json
{
  "detail": "Invalid credentials"
}
```

---

### Refresh AccessToken

**Endpoint:** `POST /auth/refresh`

**Description:** Get a new access token using refresh token

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

---

### Get User Profile

**Endpoint:** `GET /auth/profile`

**Description:** Get current user's profile

**Authentication:** Required

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

---

### Update User Profile

**Endpoint:** `PATCH /auth/profile`

**Description:** Update user profile (Telegram ID, preferences)

**Authentication:** Required

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

**Response:** `200 OK` (Updated profile)

---

### Request Password Reset

**Endpoint:** `POST /auth/password-reset/request`

**Description:** Request a password reset

**P0 Security Fix:** Reset token is sent ONLY via email, not in response

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

---

### Confirm Password Reset

**Endpoint:** `POST /auth/password-reset/confirm`

**Description:** Confirm password reset with token (token from email)

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

## Error Codes

| HTTP Code | Error Code            | Meaning                     | Example                             |
| --------- | --------------------- | --------------------------- | ----------------------------------- |
| 400       | `BAD_REQUEST`         | Invalid input               | Missing required field              |
| 401       | `UNAUTHORIZED`        | Missing or invalid token    | No Authorization header             |
| 403       | `FORBIDDEN`           | Authenticated but no access | User accessing another user's alert |
| 404       | `NOT_FOUND`           | Resource doesn't exist      | Alert ID doesn't exist              |
| 409       | `CONFLICT`            | Resource already exists     | Email already registered            |
| 429       | `RATE_LIMITED`        | Too many requests           | Exceeded rate limit                 |
| 500       | `INTERNAL_ERROR`      | Server error                | Database connection failed          |
| 503       | `SERVICE_UNAVAILABLE` | Dependency down             | RabbitMQ unavailable                |

---

## Rate Limiting

**Global Rate Limit:**

- 100 requests per minute per IP address
- 1000 requests per hour per authenticated user

**Endpoint-Specific Limits:**

- `/auth/login`: 5 attempts per 5 minutes per IP
- `/auth/register`: 3 new accounts per hour per IP
- `/ingestion/events`: 1000 requests per minute

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

## Examples

### Python Example

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# 1. Register
response = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "user@example.com",
    "password": "securepassword123"
})
tokens = response.json()
access_token = tokens["access_token"]

# 2. Get Headers with auth
headers = {"Authorization": f"Bearer {access_token}"}

# 3. Get events
response = requests.get(f"{BASE_URL}/ingestion/events?limit=10", headers=headers)
events = response.json()
print(f"Total events: {len(events)}")

# 4. Get alerts
response = requests.get(f"{BASE_URL}/api/alerts/history", headers=headers)
alerts = response.json()
print(f"Alerts: {alerts}")

# 5. Mark alert as read
alert_id = alerts[0]["alert_id"] if alerts else None
if alert_id:
    response = requests.patch(f"{BASE_URL}/api/alerts/{alert_id}", headers=headers)
    print(f"Alert marked as read: {response.json()}")
```

### PowerShell Example

```powershell
$BASE_URL = "http://localhost:8000"

# 1. Register
$registerBody = @{
    email = "user@example.com"
    password = "securepassword123"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "$BASE_URL/auth/register" `
    -Method Post `
    -ContentType "application/json" `
    -Body $registerBody

$tokens = $response.Content | ConvertFrom-Json
$accessToken = $tokens.access_token

# 2. Set Headers
$headers = @{
    "Authorization" = "Bearer $accessToken"
}

# 3. Get Events
$response = Invoke-WebRequest -Uri "$BASE_URL/ingestion/events?limit=10" `
    -Headers $headers

$events = $response.Content | ConvertFrom-Json
Write-Host "Total events: $($events.Count)"

# 4. Get Alerts
$response = Invoke-WebRequest -Uri "$BASE_URL/api/alerts/history" `
    -Headers $headers

$alerts = $response.Content | ConvertFrom-Json
Write-Host "Alerts: $($alerts.Count)"
```

### cURL Example

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepassword123"}'

# 2. Store token
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# 3. Get events
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/ingestion/events?limit=10

# 4. Get alerts
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/alerts/history

# 5. Mark alert as read
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/alerts/1
```

---

## Swagger/OpenAPI UI

Interactive API documentation available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

These provide:

- Interactive endpoint testing
- Parameter documentation
- Request/response examples
- Schema definitions
