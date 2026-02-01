# AETERNA: System Architecture Document
## Technical Architecture & Design

**Version:** 1.0  
**Date:** January 2025  
**Phase:** MVP (2-3 Month Timeline)  
**Status:** Architecture Design

---

## 1. Architecture Overview

### 1.1 System Philosophy

AETERNA follows a **microservices-based, event-driven architecture** designed for:
- ✅ **Scalability:** Handle 10,000+ events/hour, scale to 100,000+
- ✅ **Reliability:** 99.5% uptime with graceful degradation
- ✅ **Low Latency:** <10 seconds from event to user alert
- ✅ **Modularity:** Independent services for easy development and deployment
- ✅ **Cost-Efficiency:** Optimize for startup budget (~$2K-3K/month infrastructure)

### 1.2 High-Level Architecture

```
┌────────────────────────────────────────────────────┐
│              DATA SOURCES (External)                      │
│  Twitter/X │ CoinDesk │ Ethereum Node │ CoinGecko  │
└───────────┬─────────────────┬────────────┬────────────┘
            │                │            │
            │                │            │
            v                v            v
┌────────────────────────────────────────────────────┐
│         LAYER 1: INGESTION ENGINE                        │
│  ┌────────────┐  ┌────────────────┐  ┌──────────┐  │
│  │  Collectors │  │  Normalizer   │  │ Validator│  │
│  └──────┬─────┘  └───────┬────────┘  └────┬─────┘  │
└─────────┬────────────────┬──────────────┬─────────┘
          │                │              │
          v                v              v
┌────────────────────────────────────────────────────┐
│              EVENT QUEUE (RabbitMQ)                       │
│         Unified Event Stream (Normalized)                │
└───────────────────────┬─────────────────────────────┘
                        │
                        v
┌────────────────────────────────────────────────────┐
│       LAYER 2: PROCESSING ENGINE (Agents)                │
│  ┌─────────────┐          ┌────────────────┐      │
│  │  Agent A    │          │  Shared State  │      │
│  │ (Filtering) │ <------> │  (PostgreSQL)  │      │
│  └──────┬───────┘          └──────┬─────────┘      │
│         │                         │              │
│         v                         ^              │
│  ┌─────────────┐                  │              │
│  │Future: Agent│                  │              │
│  │ B,C,D(Phase│ -----------------+              │
│  │     II)     │                                 │
│  └──────┬───────┘                                 │
└────────┬────────────────────────────────────────────┘
         │
         v
┌────────────────────────────────────────────────────┐
│       LAYER 3: DELIVERY ENGINE                           │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Telegram │  │   Email   │  │ Dashboard│  │
│  │    Bot    │  │  Sender  │  │ WebSocket│  │
│  └───────────┘  └──────────┘  └──────────┘  │
└─────────┬────────────┬───────────┬──────────────┘
          │            │           │
          v            v           v
┌────────────────────────────────────────────────────┐
│                    END USERS                             │
│         Traders │ Investors │ Communities            │
└────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: Ingestion Engine

### 2.1 Purpose
Continuously collect, normalize, and validate data from multiple sources.

### 2.2 Components

#### 2.2.1 Data Collectors

Each collector is an independent microservice responsible for one data source.

##### Collector 1: News Collector
**Technology:** Python + FastAPI  
**Sources:** CoinDesk, CoinTelegraph, Decrypt, Cointelegraph  
**Method:** RSS feeds + Web scraping (BeautifulSoup)  
**Frequency:** Poll every 60 seconds  

**Schema Output:**
```json
{
  "event_id": "uuid",
  "source_type": "news",
  "source_name": "CoinDesk",
  "timestamp": "2025-01-15T10:30:00Z",
  "title": "Bitcoin Surges Past $50K",
  "content": "Full article text...",
  "url": "https://...",
  "metadata": {
    "author": "John Doe",
    "tags": ["BTC", "price"]
  }
}
```

**Implementation:**
```python
# news_collector.py
import feedparser
import schedule
from publisher import publish_to_queue

def collect_news():
    feeds = [
        'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'https://cointelegraph.com/rss'
    ]
    
    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            event = normalize_news_event(entry)
            publish_to_queue('raw_events', event)

schedule.every(60).seconds.do(collect_news)
```

---

##### Collector 2: Twitter/X Collector
**Technology:** Python + Twitter API v2  
**Method:** Filtered stream API (real-time)  
**Filters:** Crypto-related keywords, top influencer accounts  
**Rate Limit:** 50 tweets/second (Basic tier)

**Tracked Keywords:**
- `$BTC`, `$ETH`, `Bitcoin`, `Ethereum`
- Top 20 crypto influencers by follower count

**Schema Output:**
```json
{
  "event_id": "uuid",
  "source_type": "social",
  "source_name": "twitter",
  "timestamp": "2025-01-15T10:30:00Z",
  "author": {
    "username": "@crypto_whale",
    "followers": 100000,
    "verified": true
  },
  "content": "Tweet text...",
  "engagement": {
    "likes": 500,
    "retweets": 200,
    "replies": 50
  },
  "url": "https://twitter.com/..."
}
```

**Cost:** ~$100-500/month (Twitter API Basic tier)

---

##### Collector 3: On-Chain Collector (Ethereum)
**Technology:** Python + Web3.py  
**Method:** WebSocket connection to Ethereum node  
**Filters:** Transactions >$1M USD equivalent  
**Latency:** <1 block (~12 seconds)

**Tracked Events:**
- Large ETH transfers (>100 ETH)
- Large stablecoin transfers (>$1M USDT/USDC)
- DEX swaps >$500K
- Whale wallet movements

**Schema Output:**
```json
{
  "event_id": "uuid",
  "source_type": "onchain",
  "blockchain": "ethereum",
  "timestamp": "2025-01-15T10:30:00Z",
  "transaction_hash": "0x123...",
  "from_address": "0xabc...",
  "to_address": "0xdef...",
  "amount": "1000000",
  "token": "USDT",
  "usd_value": 1000000,
  "metadata": {
    "exchange_detected": "Binance",
    "transaction_type": "transfer"
  }
}
```

**Infrastructure:**
- Option A: QuickNode/Alchemy (managed) - $50-200/month
- Option B: Self-hosted node (AWS EC2) - $100-300/month
**Recommendation:** Start with managed service (QuickNode)

---

##### Collector 4: Price Data Collector
**Technology:** Python + REST APIs  
**Sources:** CoinGecko API (free tier)  
**Method:** Poll every 60 seconds  
**Tracked Assets:** Top 100 cryptocurrencies by market cap

**Schema Output:**
```json
{
  "event_id": "uuid",
  "source_type": "price",
  "source_name": "coingecko",
  "timestamp": "2025-01-15T10:30:00Z",
  "symbol": "BTC",
  "price_usd": 50000,
  "change_1h": 2.5,
  "change_24h": -3.2,
  "volume_24h": 25000000000,
  "market_cap": 950000000000
}
```

**Cost:** Free (50 calls/minute limit)

---

#### 2.2.2 Data Normalizer

**Purpose:** Transform diverse data formats into unified schema

**Unified Event Schema:**
```json
{
  "event_id": "uuid",
  "source_type": "news|social|onchain|price",
  "source_name": "string",
  "timestamp": "ISO8601",
  "title": "string",
  "content": "string",
  "entities": ["BTC", "ETH"],  // Extracted entities
  "metadata": {},
  "priority": "low|medium|high",  // Preliminary priority
  "processed": false
}
```

**Operations:**
1. **Schema Mapping:** Convert source-specific fields to unified schema
2. **Entity Extraction:** Identify mentioned cryptocurrencies, exchanges, protocols
3. **Timestamp Normalization:** Convert all times to UTC ISO8601
4. **Deduplication:** Check against recent events (using content hash)
5. **Quality Scoring:** Assign initial quality score (0-100)

**Implementation:**
```python
# normalizer.py
import hashlib
from datetime import datetime

def normalize_event(raw_event):
    # Extract entities (crypto mentions)
    entities = extract_crypto_entities(raw_event['content'])
    
    # Generate content hash for deduplication
    content_hash = hashlib.md5(
        raw_event['content'].encode()
    ).hexdigest()
    
    # Check if duplicate
    if is_duplicate(content_hash, window_minutes=60):
        return None  # Skip duplicate
    
    normalized = {
        'event_id': generate_uuid(),
        'source_type': raw_event['source_type'],
        'source_name': raw_event['source_name'],
        'timestamp': datetime.utcnow().isoformat(),
        'title': raw_event.get('title', ''),
        'content': raw_event['content'],
        'entities': entities,
        'metadata': raw_event.get('metadata', {}),
        'priority': calculate_preliminary_priority(raw_event),
        'processed': False
    }
    
    return normalized
```

---

#### 2.2.3 Validator

**Purpose:** Ensure data quality before entering processing pipeline

**Validation Rules:**
1. ✅ Required fields present (event_id, timestamp, content)
2. ✅ Timestamp within acceptable range (not future, not >24h old)
3. ✅ Content length >10 characters
4. ✅ Valid source_type
5. ✅ No profanity/spam patterns

**Actions:**
- **Pass:** Forward to Event Queue
- **Fail:** Log error, increment metrics, discard

---

### 2.3 Event Queue (RabbitMQ)

**Purpose:** Decouple ingestion from processing

**Queue Configuration:**
```yaml
queue_name: unified_events
type: durable  # Survives broker restart
max_length: 100000  # Max queued events
ttl: 3600000  # 1 hour TTL for unprocessed events
```

**Message Format:**
```json
{
  "event": { /* normalized event */ },
  "priority": 0-10,
  "routing_key": "events.crypto.btc"
}
```

**Performance:**
- Throughput: 10,000+ messages/second
- Latency: <10ms per message
- Persistence: Yes (survives restarts)

**Alternative (for scale):** Apache Kafka (heavier, but better for >100K events/hour)

---

### 2.4 Technology Stack (Layer 1)

| Component | Technology | Reason |
|-----------|-----------|--------|
| **Collectors** | Python 3.11 + FastAPI | Fast development, great API libraries |
| **Event Queue** | RabbitMQ | Lightweight, perfect for <100K msgs/hr |
| **Database** | PostgreSQL | Reliable, great for relational data |
| **Caching** | Redis | Fast lookups for deduplication |
| **Deployment** | Docker + Docker Compose | Easy local development & deployment |
| **Monitoring** | Prometheus + Grafana | Industry standard, free |

---

## 3. Layer 2: Processing Engine (Agents)

### 3.1 Purpose
Transform raw events into actionable intelligence

### 3.2 MVP Scope (Month 1-3)

**For MVP, we implement ONLY Agent A (The Sieve)**  
**Agents B, C, D are Phase II (Month 4-6)**

---

### 3.3 Agent A: The Sieve (Noise Filter)

#### 3.3.1 Purpose
Filter out 90%+ of noise (spam, bots, duplicates, low-quality content)

#### 3.3.2 Architecture

```
┌─────────────────────────────┐
│    Event Queue (Input)    │
└───────────┬─────────────────┘
           │
           v
┌─────────────────────────────┐
│   Agent A Worker Pool    │
│   (10 parallel workers)   │
└───────────┬─────────────────┘
           │
           v
┌─────────────────────────────┐
│  Filtering Pipeline:     │
│  1. Multi-Source Check   │
│  2. Engagement Analysis  │
│  3. Bot Detection        │
│  4. Semantic Dedup       │
│  5. Scoring              │
└───────────┬─────────────────┘
           │
      ┌────┬┴────┐
      v    v    v
   HIGH MED  LOW
   ┌───────────┐
   │  Alert   │
   │ Generator│
   └────┬──────┘
        v
   [Delivery]
```

#### 3.3.3 Filtering Logic

##### Step 1: Multi-Source Verification
**Goal:** Prioritize news reported by multiple sources

```python
def multi_source_check(event, lookback_minutes=30):
    """
    Check if similar event reported by multiple sources
    """
    # Get similar events in last 30 minutes
    similar_events = find_similar_events(
        content=event['content'],
        window_minutes=lookback_minutes
    )
    
    unique_sources = set([e['source_name'] for e in similar_events])
    
    score = 0
    if len(unique_sources) >= 3:
        score = 100  # Multiple credible sources
    elif len(unique_sources) == 2:
        score = 70
    elif len(unique_sources) == 1:
        score = 40  # Only one source
    
    return {
        'score': score,
        'source_count': len(unique_sources),
        'sources': list(unique_sources)
    }
```

---

##### Step 2: Engagement Analysis (Social Media)
**Goal:** Filter low-engagement spam tweets

```python
def engagement_analysis(event):
    """
    Analyze social media engagement metrics
    """
    if event['source_type'] != 'social':
        return {'score': 50, 'reason': 'not_social'}  # N/A
    
    engagement = event.get('engagement', {})
    author = event.get('author', {})
    
    # Calculate engagement score
    likes = engagement.get('likes', 0)
    retweets = engagement.get('retweets', 0)
    followers = author.get('followers', 0)
    verified = author.get('verified', False)
    
    # Engagement rate = (likes + retweets) / followers
    if followers > 0:
        engagement_rate = (likes + retweets) / followers
    else:
        engagement_rate = 0
    
    score = 0
    # High engagement = higher score
    if engagement_rate > 0.05:  # 5%+ engagement
        score = 100
    elif engagement_rate > 0.01:  # 1-5%
        score = 70
    elif engagement_rate > 0.001:  # 0.1-1%
        score = 40
    else:
        score = 20  # Low engagement
    
    # Boost for verified accounts
    if verified:
        score = min(100, score + 20)
    
    return {
        'score': score,
        'engagement_rate': engagement_rate,
        'verified': verified
    }
```

---

##### Step 3: Bot Detection
**Goal:** Filter bot-generated spam

```python
def bot_detection(event):
    """
    Simple heuristics to detect bots
    (Can be enhanced with ML later)
    """
    content = event.get('content', '').lower()
    author = event.get('author', {})
    
    # Bot indicators
    red_flags = 0
    
    # Check for spam patterns
    spam_keywords = ['airdrop', 'giveaway', 'click here', 
                     'dm me', 'send now', 'double your']
    for keyword in spam_keywords:
        if keyword in content:
            red_flags += 1
    
    # Check for excessive links
    link_count = content.count('http')
    if link_count > 2:
        red_flags += 1
    
    # Check for excessive hashtags
    hashtag_count = content.count('#')
    if hashtag_count > 5:
        red_flags += 1
    
    # Check for generic username patterns
    username = author.get('username', '')
    if re.match(r'^\w+\d{4,}$', username):  # e.g., user12345
        red_flags += 1
    
    # Calculate bot probability
    bot_probability = min(100, red_flags * 25)
    
    # Invert for quality score (high bot prob = low score)
    score = 100 - bot_probability
    
    return {
        'score': score,
        'bot_probability': bot_probability,
        'red_flags': red_flags
    }
```

---

##### Step 4: Semantic Deduplication
**Goal:** Remove duplicate stories with different wording

**Approach:** Use sentence embeddings to compare semantic similarity

```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Load model (once at startup)
model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, 80MB

def semantic_deduplication(event, lookback_minutes=60):
    """
    Check for semantically similar events
    """
    # Generate embedding for current event
    event_embedding = model.encode(event['content'])
    
    # Get recent events in same category
    recent_events = get_recent_events(
        entities=event['entities'],
        window_minutes=lookback_minutes
    )
    
    max_similarity = 0
    for recent in recent_events:
        recent_embedding = recent['embedding']
        similarity = cosine_similarity(event_embedding, recent_embedding)
        max_similarity = max(max_similarity, similarity)
    
    # High similarity = likely duplicate
    if max_similarity > 0.9:
        return {'score': 0, 'duplicate': True, 'similarity': max_similarity}
    elif max_similarity > 0.7:
        return {'score': 40, 'duplicate': False, 'similarity': max_similarity}
    else:
        return {'score': 100, 'duplicate': False, 'similarity': max_similarity}
```

**Cost:** Free (using open-source model)

---

##### Step 5: Aggregate Scoring

```python
def calculate_final_score(event, checks):
    """
    Weighted average of all check scores
    """
    weights = {
        'multi_source': 0.3,
        'engagement': 0.2,
        'bot_detection': 0.3,
        'semantic_dedup': 0.2
    }
    
    final_score = sum(
        checks[key]['score'] * weights[key] 
        for key in weights
    )
    
    # Assign priority based on score
    if final_score >= 80:
        priority = 'HIGH'
    elif final_score >= 50:
        priority = 'MEDIUM'
    else:
        priority = 'LOW'
    
    return {
        'final_score': final_score,
        'priority': priority,
        'checks': checks
    }
```

---

#### 3.3.4 Output Format

**Scored Event:**
```json
{
  "event": { /* original event */ },
  "filtering_result": {
    "final_score": 85,
    "priority": "HIGH",
    "checks": {
      "multi_source": {"score": 100, "source_count": 3},
      "engagement": {"score": 70, "engagement_rate": 0.03},
      "bot_detection": {"score": 90, "bot_probability": 10},
      "semantic_dedup": {"score": 80, "duplicate": false}
    },
    "timestamp": "2025-01-15T10:30:05Z"
  },
  "action": "ALERT"  // or "STORE" or "DISCARD"
}
```

---

### 3.4 Shared State (Database)

**Purpose:** Store processed events, user preferences, alert history

#### Database Schema (MVP)

```sql
-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    telegram_id BIGINT UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    preferences JSONB,  -- Alert preferences
    subscription_tier VARCHAR(20)  -- free, pro, elite
);

-- Events table (processed events)
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    source_type VARCHAR(20) NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    entities TEXT[],  -- Mentioned cryptos
    metadata JSONB,
    priority VARCHAR(10),  -- LOW, MEDIUM, HIGH
    final_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_timestamp (timestamp),
    INDEX idx_priority (priority),
    INDEX idx_entities USING GIN(entities)
);

-- Alerts table (sent to users)
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    event_id UUID REFERENCES events(event_id),
    sent_at TIMESTAMP DEFAULT NOW(),
    channel VARCHAR(20),  -- telegram, email, dashboard
    status VARCHAR(20),  -- sent, failed, pending
    user_feedback VARCHAR(20),  -- useful, not_relevant (for learning)
    INDEX idx_user_id (user_id),
    INDEX idx_sent_at (sent_at)
);

-- Portfolio table (user holdings)
CREATE TABLE portfolios (
    portfolio_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    symbol VARCHAR(10) NOT NULL,
    amount DECIMAL(20, 8),
    avg_buy_price DECIMAL(20, 2),
    notes TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 3.5 Technology Stack (Layer 2)

| Component | Technology | Reason |
|-----------|-----------|--------|
| **Agent Workers** | Python 3.11 + Celery | Distributed task processing |
| **Database** | PostgreSQL 15 | Reliable, powerful, free |
| **Cache** | Redis | Fast lookups, deduplication |
| **Embeddings** | sentence-transformers | Free, fast, local |
| **LLM (future)** | GPT-4 Turbo / Claude | For complex analysis (Phase II) |
| **Monitoring** | Sentry | Error tracking |

---

## 4. Layer 3: Delivery Engine

### 4.1 Purpose
Deliver alerts to users via their preferred channels

### 4.2 Components

#### 4.2.1 Alert Generator

**Purpose:** Transform scored events into user-friendly alerts

**Process:**
1. Filter events by priority (HIGH, MEDIUM)
2. Format for each channel (Telegram, Email, Dashboard)
3. Apply user preferences (frequency, types)
4. Queue for delivery

**Alert Template (Telegram):**
```
🚨 [PRIORITY] Alert Type

📊 **Event:** Bitcoin surges past $50K

🕒 **Time:** 2 minutes ago

🔗 **Source:** CoinDesk, CoinTelegraph, Decrypt (3 sources)

📈 **Impact:** High - Reported by multiple credible sources

👁️ View Details: https://app.aeterna.ai/alerts/123
```

---

#### 4.2.2 Telegram Bot

**Technology:** Python + python-telegram-bot library  
**Features:**
- Receive alerts
- Set preferences
- View recent alerts
- Add portfolio holdings

**Commands:**
```
/start - Link Telegram to AETERNA account
/status - View alert settings
/alerts - View recent alerts
/portfolio - Manage portfolio
/settings - Update preferences
/help - Get help
```

**Implementation:**
```python
from telegram import Update
from telegram.ext import Application, CommandHandler

async def start(update: Update, context):
    await update.message.reply_text(
        "Welcome to AETERNA! Link your account: "
        "https://app.aeterna.ai/connect?telegram_id={}".format(
            update.effective_user.id
        )
    )

async def send_alert(telegram_id, alert_text):
    await application.bot.send_message(
        chat_id=telegram_id,
        text=alert_text,
        parse_mode='Markdown'
    )

app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
```

**Cost:** Free (Telegram Bot API)

---

#### 4.2.3 Email Sender

**Technology:** SendGrid / AWS SES  
**Use Case:** Fallback for HIGH priority alerts, daily digest

**Email Template:**
```html
<html>
  <body>
    <h2>🚨 High Priority Alert</h2>
    <p><strong>Event:</strong> Bitcoin surges past $50K</p>
    <p><strong>Time:</strong> 2 minutes ago</p>
    <p><strong>Sources:</strong> CoinDesk, CoinTelegraph</p>
    <a href="https://app.aeterna.ai/alerts/123">View Details</a>
  </body>
</html>
```

**Cost:** ~$0.001 per email (SendGrid: 100 emails/day free)

---

#### 4.2.4 Web Dashboard

**Technology:** React.js + TailwindCSS + Socket.io  
**Deployment:** Vercel (free tier)

**Features:**
- Real-time alert feed (WebSocket)
- Alert history with search/filter
- Portfolio management
- Settings (preferences, notifications)
- Account management

**Pages:**
1. `/` - Landing page
2. `/login` - Authentication
3. `/dashboard` - Main feed
4. `/alerts` - Alert history
5. `/portfolio` - Portfolio management
6. `/settings` - User settings

---

### 4.3 Delivery Logic

**Priority-Based Routing:**

| Priority | Telegram | Email | Dashboard |
|---------|----------|-------|----------|
| **HIGH** | ✅ Immediate | ✅ Immediate | ✅ Real-time |
| **MEDIUM** | ✅ Immediate | ❌ No | ✅ Real-time |
| **LOW** | ❌ No | ❌ No | ✅ Real-time |

**Rate Limiting:**
- Max 10 alerts/hour per user (configurable)
- Batch similar alerts (e.g., multiple price alerts)
- Respect user "quiet hours" preferences

---

### 4.4 Technology Stack (Layer 3)

| Component | Technology | Cost |
|-----------|-----------|------|
| **Telegram Bot** | python-telegram-bot | Free |
| **Email** | SendGrid / AWS SES | $0.001/email |
| **Frontend** | React + TailwindCSS | Free |
| **Real-time** | Socket.io | Free |
| **Hosting** | Vercel | Free (hobby) |

---

## 5. Infrastructure & Deployment

### 5.1 Development Environment

**Local Development:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: aeterna
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"  # AMQP
      - "15672:15672"  # Management UI

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://admin:password@postgres:5432/aeterna
      REDIS_URL: redis://redis:6379
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - rabbitmq

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000
```

---

### 5.2 Production Deployment

**Recommended Platform:** **Railway** / **Render** / **AWS**

**Why Railway/Render?**
- ✅ Easy deployment (Git push to deploy)
- ✅ Affordable ($20-50/month for MVP)
- ✅ Managed PostgreSQL, Redis
- ✅ Automatic SSL certificates
- ✅ Built-in monitoring

**Architecture (Railway):**
```
Services:
  1. Backend API (FastAPI)      - $10/month
  2. Celery Workers (x2)        - $10/month
  3. PostgreSQL (Managed)       - $10/month
  4. Redis (Managed)            - $5/month
  5. RabbitMQ (CloudAMQP)       - $9/month

Frontend: Vercel (Free)

Total: ~$50/month
```

---

### 5.3 Cost Breakdown (Monthly)

#### Infrastructure Costs

| Service | Provider | Cost/Month |
|---------|---------|------------|
| **Compute** | Railway/Render | $30-50 |
| **Database** | Managed PostgreSQL | $10 |
| **Cache** | Managed Redis | $5 |
| **Message Queue** | CloudAMQP | $9 |
| **Frontend Hosting** | Vercel | $0 (free) |
| **Monitoring** | Sentry | $0 (free tier) |
| **TOTAL** | | **$54-74/month** |

#### API Costs (Variable)

| Service | Cost | Usage |
|---------|------|-------|
| **Twitter API** | $100-500/month | Filtered stream |
| **OpenAI API** | $0 (MVP) | Not used in MVP |
| **Ethereum Node** | $50-200/month | QuickNode/Alchemy |
| **SendGrid** | $0-15/month | 100 emails/day free |
| **TOTAL** | | **$150-715/month** |

**Total MVP Cost: ~$200-800/month** (depends on usage)

---

## 6. Security & Compliance

### 6.1 Security Measures

1. **Authentication:**
   - JWT tokens for API access
   - OAuth2 for social login (Google, Telegram)
   - Rate limiting (100 req/min per user)

2. **Data Protection:**
   - Encrypted passwords (bcrypt)
   - HTTPS/TLS for all communications
   - Encrypted database backups

3. **API Security:**
   - API key rotation
   - Input validation & sanitization
   - SQL injection prevention (parameterized queries)
   - XSS protection

4. **Monitoring:**
   - Failed login attempt tracking
   - Unusual activity alerts
   - Error tracking (Sentry)

### 6.2 Compliance

1. **GDPR (EU users):**
   - User data export
   - Right to be forgotten (delete account)
   - Cookie consent
   - Privacy policy

2. **Terms of Service:**
   - Disclaimer: "For informational purposes only, not financial advice"
   - Data usage policies
   - Refund policy

---

## 7. Monitoring & Observability

### 7.1 Key Metrics

#### System Health
- **Uptime:** Target 99.5%
- **API Latency:** p50, p95, p99
- **Event Processing Rate:** events/second
- **Queue Depth:** pending events in queue
- **Error Rate:** errors/second

#### Business Metrics
- **Daily Active Users (DAU)**
- **Alerts Sent:** total, per user, per priority
- **Alert Quality:** % marked "useful" by users
- **Conversion Rate:** free → paid

### 7.2 Tools

| Metric Type | Tool | Cost |
|------------|------|------|
| **Infrastructure** | Prometheus + Grafana | Free |
| **Errors** | Sentry | Free (5K errors/month) |
| **Logs** | Railway/Render logs | Included |
| **Uptime** | UptimeRobot | Free (50 monitors) |

---

## 8. Scalability Plan

### 8.1 Current Capacity (MVP)
- **Users:** 1,000 concurrent
- **Events:** 10,000/hour
- **Alerts:** 5,000/hour

### 8.2 Scaling Strategy

**Phase I (0-1K users):** Single backend server  
**Phase II (1K-10K users):** Horizontal scaling (2-5 workers)  
**Phase III (10K+ users):** Kubernetes cluster, managed services

**Bottlenecks & Solutions:**

| Bottleneck | Solution |
|-----------|----------|
| **Database** | Read replicas, connection pooling |
| **Agent Workers** | Horizontal scaling (add more workers) |
| **Real-time Updates** | Redis Pub/Sub, WebSocket sharding |
| **API Rate Limits** | Caching, request batching |

---

## 9. Testing Strategy

### 9.1 Unit Tests
- All filtering functions
- Data normalization
- Alert generation
- Coverage target: 80%+

### 9.2 Integration Tests
- End-to-end event flow (ingestion → alert)
- Database operations
- API endpoints

### 9.3 Load Tests
- Simulate 10,000 events/hour
- Stress test queue
- API endpoint performance

**Tool:** pytest + locust (load testing)

---

## 10. Future Enhancements (Post-MVP)

### Phase II (Month 4-6)
1. **Agent B:** Wallet clustering & attribution
2. **Agent C:** Sentiment analysis & impact scoring
3. **Agent D:** Portfolio personalization
4. **Advanced Analytics:** Backtesting, performance tracking

### Phase III (Month 7-12)
1. **Multi-Chain Support:** Solana, BSC, L2s
2. **Mobile Apps:** iOS, Android
3. **API Access:** For B2B clients
4. **Custom AI Models:** Fine-tuned for crypto
5. **Social Features:** Community insights, leaderboards

---

## 11. Architecture Decisions

### 11.1 Why These Technologies?

**Python:**
- ✅ Excellent libraries for data processing, ML, APIs
- ✅ Fast development speed
- ✅ Great for MVP
- ❌ Not as performant as Go/Rust (but good enough for MVP)

**PostgreSQL:**
- ✅ Reliable, mature, feature-rich
- ✅ Great for relational data
- ✅ JSON support (JSONB)
- ❌ Harder to scale than NoSQL (but fine for <100K users)

**RabbitMQ:**
- ✅ Simple, reliable
- ✅ Good for <100K events/hour
- ✅ Easy to deploy
- ❌ Not as scalable as Kafka (but we can migrate later)

**React + TailwindCSS:**
- ✅ Fast UI development
- ✅ Great ecosystem
- ✅ Easy to find developers

---

## 12. Open Questions & Decisions Needed

1. **❓ Should we support Discord in MVP?** (In addition to Telegram)  
   **Recommendation:** Start with Telegram only, add Discord in Phase II

2. **❓ Which blockchain node provider?** (QuickNode vs Alchemy vs self-hosted)  
   **Recommendation:** QuickNode (reliable, affordable)

3. **❓ Should we implement custom ML models for MVP?**  
   **Recommendation:** No, use rule-based + open-source models (sentence-transformers)

4. **❓ How to handle user feedback on alert quality?**  
   **Recommendation:** Simple thumbs up/down, store for future learning

---

## 13. Conclusion

This architecture is designed to:
- ✅ **Build fast:** MVP in 2-3 months with small team
- ✅ **Start cheap:** ~$200-800/month initial costs
- ✅ **Scale later:** Architecture supports 10K+ users
- ✅ **Iterate quickly:** Modular design for easy changes

**Next Steps:**
1. Review and approve this architecture
2. Create development roadmap (sprints)
3. Set up development environment
4. Begin implementation (Week 1: Data collectors)
