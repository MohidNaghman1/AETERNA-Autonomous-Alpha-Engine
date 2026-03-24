# AETERNA API Reference

**Version:** 1.0.0  
**Last Updated:** March 2026

> **Interactive Docs:** Once deployed, visit `/docs` (Swagger UI) or `/redoc` (ReDoc) for live, interactive API exploration.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Events (Ingestion)](#events-ingestion)
3. [Data Structure Reference](#data-structure-reference)
4. [Alerts](#alerts)
5. [User Profile](#user-profile)
6. [System & Health](#system--health)
7. [WebSocket (Real-time)](#websocket-real-time)
8. [Error Handling](#error-handling)

---

## Quick Start

```bash
# Set your API base URL
export API_URL="https://your-deployment-url.com"

# Get crypto events (no auth required)
curl $API_URL/ingestion/events?limit=10

# Register
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepassword123"}'

# Login (returns JWT token)
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword123"

# Use token for protected endpoints
curl -H "Authorization: Bearer <YOUR_TOKEN>" \
  $API_URL/api/alerts/history
```

---

## Authentication

All protected endpoints require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

- **Access Token:** Expires in 24 hours
- **Refresh Token:** Expires in 30 days

### Register

```
POST /auth/register
```

| Field    | Type   | Required | Description     |
|----------|--------|----------|-----------------|
| email    | string | Yes      | Email address   |
| password | string | Yes      | Account password |

**Response:** `200 OK`
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Login

```
POST /auth/login
Content-Type: application/x-www-form-urlencoded
```

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| username | string | Yes      | Email       |
| password | string | Yes      | Password    |

**Response:** `200 OK` — Same as register response.

### Refresh Token

```
POST /auth/refresh
```

```json
{ "refresh_token": "eyJ..." }
```

**Response:** `200 OK` — New access and refresh tokens.

### Password Reset

```
POST /auth/password-reset/request    → Send reset email
POST /auth/password-reset/confirm    → Confirm with token + new password
```

### Unsubscribe from Emails

```
GET /auth/unsubscribe?email=user@example.com
```

---

## Events (Ingestion)

### List Events

```
GET /ingestion/events
```

| Parameter  | Type    | Default | Description                    |
|------------|---------|---------|--------------------------------|
| skip       | integer | 0       | Pagination offset              |
| limit      | integer | 100     | Results per page (max 500)     |
| source     | string  | —       | Filter by source               |
| type       | string  | —       | Filter by type (`news`/`price`)|
| start_date | string  | —       | ISO 8601 start filter          |
| end_date   | string  | —       | ISO 8601 end filter            |

**Auth:** Not required

**Response:** `200 OK` — Returns an array of event objects. See [Data Structure Reference](#data-structure-reference) for full field details.

```json
[
  {
    "id": 1,
    "source": "coindesk",
    "type": "news",
    "timestamp": "2026-03-09T12:00:00Z",
    "content": {
      "title": "Bitcoin Hits New High",
      "summary": "Clean HTML-free text...",
      "link": "https://...",
      "published": "2026-03-09T10:00:00Z",
      "author": "Jane Smith",
      "categories": ["Bitcoin", "Market News"],
      "image_url": "https://...jpg",
      "word_count": 1250,
      "read_time_minutes": 6,
      "quality_score": 85.5,
      "urls": ["https://url1", "https://url2"],
      "hashtags": ["#bitcoin", "#crypto"],
      "mentions": ["@CoinDesk"],
      "has_image": true,
      "url_count": 2
    },
    "entities": ["Bitcoin", "BTC", "Cryptocurrency"]
  },
  {
    "id": 2,
    "source": "coingecko",
    "type": "price",
    "timestamp": "2026-03-09T12:30:00Z",
    "content": {
      "id": "bitcoin",
      "symbol": "BTC",
      "name": "Bitcoin",
      "current_price": 98500.00,
      "change_1h_pct": 1.5,
      "change_24h_pct": 2.3,
      "change_7d_pct": -0.5,
      "market_cap": 1940000000000,
      "market_cap_rank": 1,
      "trading_volume_24h": 25000000000,
      "risk_score": 42.0,
      "price_volatility_category": "medium",
      "significant_moves": ["1h: ↑ 1.50%", "Sustained trend"],
      "should_alert": true,
      "alert_reasons": "1h: ↑ 1.50% | Sustained trend"
    },
    "entities": ["Bitcoin", "BTC"]
  },
  {
    "id": 3,
    "source": "ethereum",
    "type": "onchain",
    "timestamp": "2026-03-09T12:45:00Z",
    "content": {
      "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
      "from_address": "0xabc...",
      "to_address": "0xdef...",
      "amount": "1000000000",
      "token": "USDT",
      "token_decimals": 6,
      "usd_value": 1000.0,
      "exchange_from": "Binance",
      "exchange_to": null,
      "exchange_detected": "Binance",
      "transaction_type": "transfer",
      "blockchain": "ethereum",
      "title": "Large USDT Transfer: $1,000",
      "summary": "Binance activity: 0xabc... → 0xdef... | USDT | $1,000 USD",
      "mentions": ["USDT", "Binance"],
      "alert_reason": "Large USDT transfer detected on-chain",
      "priority_marker": "MEDIUM",
      "priority_reason": "Threshold: $1,000 >= $10,000 (MEDIUM) | Exchange: Binance",
      "engagement_rate": 0.0
    },
    "entities": ["USDT", "Binance"]
  }
]
```

### Get Single Event

```
GET /ingestion/events/{event_id}
```

### Search by Source

```
GET /ingestion/search/by-source/{source}
```

### Search by Type

```
GET /ingestion/search/by-type/{event_type}
```

### Event Statistics

```
GET /ingestion/stats
```

**Response:**
```json
{
  "total_events": 3400,
  "by_source": { "coindesk": 1200, "cointelegraph": 1100 },
  "by_type": { "news": 3400, "price": 0 }
}
```

### Auto-Update Status

```
GET /ingestion/auto-update-status
```

Shows whether automatic collectors (RSS, Price, On-Chain) are running.

---

## Data Structure Reference

### RSS/News Event (`type: "news"`)

| Field | Type | Description |
|---|---|---|
| `content.title` | string | Article headline |
| `content.summary` | string | Clean, HTML-free article text |
| `content.link` | string | URL to original article |
| `content.published` | string | Original publication timestamp |
| `content.author` | string | Article author |
| `content.categories` | string[] | Article categories/tags |
| `content.image_url` | string | Article image URL (if available) |
| `content.word_count` | integer | Article word count |
| `content.read_time_minutes` | integer | Estimated reading time |
| `content.quality_score` | float | Content quality score (0–100) |
| `content.urls` | string[] | URLs found in article |
| `content.hashtags` | string[] | Extracted hashtags |
| `content.mentions` | string[] | Extracted mentions |
| `content.has_image` | boolean | Whether the article has an image |
| `content.url_count` | integer | Number of URLs in article |
| `entities` | string[] | Extracted crypto entities (e.g. `["Bitcoin", "BTC"]`) |

### Price Event (`type: "price"`)

| Field | Type | Description |
|---|---|---|
| `content.id` | string | CoinGecko asset ID |
| `content.symbol` | string | Ticker symbol (e.g. `BTC`) |
| `content.name` | string | Full asset name |
| `content.current_price` | float | Current USD price |
| `content.price_position_24h` | float | Position in 24h range (0–1) |
| `content.ath` / `content.atl` | float | All-time high / low |
| `content.high_24h` / `content.low_24h` | float | 24-hour high / low |
| `content.change_1h_pct` | float | 1-hour price change % |
| `content.change_24h_pct` | float | 24-hour price change % |
| `content.change_7d_pct` | float | 7-day price change % |
| `content.change_14d_pct` | float | 14-day price change % |
| `content.change_30d_pct` | float | 30-day price change % |
| `content.change_1y_pct` | float | 1-year price change % |
| `content.market_cap` | float | Market capitalization (USD) |
| `content.market_cap_rank` | integer | Rank by market cap |
| `content.fully_diluted_valuation` | float | Fully diluted market cap |
| `content.trading_volume_24h` | float | 24-hour trading volume |
| `content.volume_to_market_cap_ratio` | float | Liquidity indicator |
| `content.circulating_supply` | float | Circulating token supply |
| `content.max_supply` | float | Maximum token supply |
| `content.circulating_to_max_ratio` | float | Circulating / max supply ratio |
| `content.risk_score` | float | Risk assessment (0–100, higher = riskier) |
| `content.price_volatility_category` | string | `"low"`, `"medium"`, or `"high"` |
| `content.significant_moves` | string[] | Notable price movements |
| `content.should_alert` | boolean | Whether this event should trigger alerts |
| `content.alert_reasons` | string | Human-readable alert reasoning |
| `entities` | string[] | Extracted crypto entities |

### On-Chain Event (`type: "onchain"`)

| Field | Type | Description |
|---|---|---|
| `content.transaction_hash` | string | Blockchain transaction hash |
| `content.blockchain` | string | Blockchain network (e.g. `ethereum`) |
| `content.transaction_type` | string | `transfer`, `dex_swap`, etc. |
| `content.from_address` | string | Source address |
| `content.to_address` | string | Destination address |
| `content.amount` | string | Token amount (raw wei/string) |
| `content.token` | string | Token symbol (e.g., `USDT`, `ETH`) |
| `content.token_decimals` | integer | Token decimals (e.g., `18`, `6`) |
| `content.usd_value` | float | Calculated USD value of transfer |
| `content.exchange_from` | string / null | Source exchange name (if known) |
| `content.exchange_to` | string / null | Destination exchange name (if known) |
| `content.exchange_detected` | string | Any central exchange identified |
| `content.dex` | string | DEX name (for swap events) |
| `content.title` | string | System-generated alert title |
| `content.summary` | string | Human-readable transaction summary |
| `content.priority_marker` | string | Objectively calculated (`HIGH`, `MEDIUM`, `LOW`) |
| `content.priority_reason` | string | Rationale for the priority marker |
| `content.alert_reason` | string | Detailed alert context |
| `content.engagement_rate` | float | Ignored for on-chain, fixed at `0.0` |
| `entities` | string[] | Tokens and exchanges involved |

---

## Alerts

### Alert System

- HIGH and MEDIUM priority events automatically generate alerts
- Alerts are scored by the intelligence pipeline (Agent A)
- Broadcast alerts (system-wide) are visible to all authenticated users
- Alert statuses: `pending`, `read`, `dismissed`

### Get Alert History

```
GET /api/alerts/history
```

**Auth:** Required

| Parameter  | Type    | Default | Description                     |
|------------|---------|---------|----------------------------------|
| skip       | integer | 0       | Pagination offset                |
| limit      | integer | 20      | Results per page (max 50)        |
| priority   | string  | —       | `HIGH`, `MEDIUM`, or `LOW`       |
| start_date | string  | —       | ISO 8601 filter                  |
| end_date   | string  | —       | ISO 8601 filter                  |

**Response:** `200 OK`
```json
[
  {
    "alert_id": "51555",
    "created_at": "2026-03-12T09:51:51",
    "title": "Bitcoin Price Alert - Near ATH",
    "priority": "HIGH",
    "entity": "bitcoin",
    "status": "pending",
    "read_at": null
  }
]
```

### Get Single Alert

```
GET /api/alerts/{alert_id}
```

### Mark Alert as Read

```
PATCH /api/alerts/{alert_id}
```

### Dismiss Alert

```
DELETE /api/alerts/{alert_id}
```

### Export Alerts as CSV

```
GET /api/alerts/history/export
```

---

## User Profile

### Get Profile

```
GET /auth/profile
```

**Auth:** Required

**Response:**
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

### Update Profile

```
PATCH /auth/profile
```

**Auth:** Required

```json
{
  "telegram_id": "987654321",
  "preferences": {
    "notifications_enabled": true,
    "email_frequency": "daily_digest"
  }
}
```

---

## System & Health

| Endpoint | Description | Auth |
|---|---|---|
| `GET /` | Welcome message | No |
| `GET /health` | Simple health check | No |
| `GET /health/system` | Dependency status (PostgreSQL, Redis, RabbitMQ) | No |
| `GET /metrics` | Prometheus-format metrics | No |

---

## WebSocket (Real-time)

Connect via Socket.IO for real-time alert push:

```javascript
import { io } from "socket.io-client";

const socket = io("https://your-deployment-url.com", {
  auth: { token: "your-jwt-token" }
});

socket.on("alert", (data) => {
  console.log("New alert:", data);
});

socket.on("pong", () => {
  console.log("Connection alive");
});

socket.emit("ping");
```

**Events:**
- `alert` — New alert pushed to authenticated user
- `pong` — Heartbeat response
- `disconnect` — Connection closed

---

## Admin Endpoints

Admin endpoints require JWT authentication **and** the `admin` role. Non-admins receive `403 Forbidden`.

| Endpoint | Method | Description |
|---|---|---|
| `/api/admin/users/` | GET | List all users |
| `/api/admin/users/{id}` | GET | Get user details |
| `/api/admin/users/{id}/toggle` | PATCH | Toggle user active status |
| `/api/admin/metrics` | GET | System metrics dashboard |
| `/api/admin/roles/` | GET | List all role assignments |
| `/api/admin/roles/admins` | GET | List admin users |
| `/api/admin/roles/{id}` | GET | Get user's role |
| `/api/admin/roles/{id}/assign` | POST | Assign a role |
| `/api/admin/roles/{id}/remove` | DELETE | Remove admin role |

---

## Error Handling

### HTTP Error Codes

| HTTP | Meaning | Solution |
|---|---|---|
| 400 | Invalid input | Check request body/params |
| 401 | Missing or invalid token | Include valid Bearer token |
| 403 | No access (wrong role) | Contact admin for access |
| 404 | Resource not found | Check resource ID |
| 409 | Already exists | Email already registered |
| 429 | Rate limited | Wait and retry |
| 500 | Server error | Report to maintainers |
| 503 | Dependency down | Check `/health/system` |

### Dead Letter Queue (DLQ)

Failed messages are handled automatically by the consumer pipeline:

- ✅ Failed messages are retried up to **3 times**
- ✅ Permanently failed messages are routed to the `events_dlq` queue
- ✅ Each retry attempt tracks the error message for debugging
- ✅ Prevents infinite retry loops

---

## Client Examples

### JavaScript

```javascript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem("token");
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// Usage
const events = await apiCall("/ingestion/events?limit=20");
const alerts = await apiCall("/api/alerts/history");
```

### Python

```python
import requests

BASE_URL = "http://localhost:8000"  # or your deployment URL

# Login
resp = requests.post(f"{BASE_URL}/auth/login",
    data={"username": "user@example.com", "password": "pass123"})
token = resp.json()["access_token"]

# Get alerts
alerts = requests.get(f"{BASE_URL}/api/alerts/history",
    headers={"Authorization": f"Bearer {token}"}).json()
```

---

**Total Endpoints:** 40+  
**Auth:** JWT tokens (24h access, 30d refresh)  
**Authorization:** Role-based access control (RBAC)  
**Docs:** `/docs` (Swagger) · `/redoc` (ReDoc)
