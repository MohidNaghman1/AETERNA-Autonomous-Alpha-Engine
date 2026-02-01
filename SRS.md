# Software Requirements Specification (SRS)
## AETERNA: Autonomous Alpha Engine

**Document Version:** 1.0  
**Date:** January 2025  
**Project Phase:** MVP (2-3 Month Development)  
**Status:** Draft for Review  
**Prepared By:** Development Team  
**Classification:** Confidential

---

## Document Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | Jan 2025 | Dev Team | Initial SRS for MVP |

---

## Table of Contents

1. Introduction
   - 1.1 Purpose
   - 1.2 Scope
   - 1.3 Definitions, Acronyms, and Abbreviations
   - 1.4 References
   - 1.5 Overview

2. Overall Description
   - 2.1 Product Perspective
   - 2.2 Product Functions
   - 2.3 User Characteristics
   - 2.4 Constraints
   - 2.5 Assumptions and Dependencies

3. Specific Requirements
   - 3.1 Functional Requirements
   - 3.2 Non-Functional Requirements

4. System Features
   - 4.1 Data Ingestion System
   - 4.2 Event Processing System
   - 4.3 Alert Delivery System
   - 4.4 User Management System
   - 4.5 Web Dashboard

5. External Interface Requirements
   - 5.1 User Interfaces
   - 5.2 Hardware Interfaces
   - 5.3 Software Interfaces
   - 5.4 Communication Interfaces

6. Performance Requirements

7. Design Constraints

8. Software System Attributes
   - 8.1 Reliability
   - 8.2 Availability
   - 8.3 Security
   - 8.4 Maintainability
   - 8.5 Portability

9. Other Requirements

---

# 1. INTRODUCTION

## 1.1 Purpose

This Software Requirements Specification (SRS) document provides a complete description of the AETERNA (Autonomous Alpha Engine) system. It details the functional and non-functional requirements for the Minimum Viable Product (MVP) to be developed over a 2-3 month period.

This document is intended for:
- Development team members (developers, architects)
- Project stakeholders (founders, investors)
- Quality assurance team
- Future maintenance teams

## 1.2 Scope

**Product Name:** AETERNA - Autonomous Alpha Engine

**Product Objectives:**
- Reduce cryptocurrency information overload by 99% (from 10,000+ daily signals to 3-5 actionable alerts)
- Provide real-time, intelligent crypto market alerts within 10 seconds of event occurrence
- Filter spam, bots, and low-quality information with 90%+ accuracy
- Deliver personalized alerts via multiple channels (Telegram, Email, Web Dashboard)

**Benefits:**
- Time Savings: Users spend 5 minutes reviewing alerts vs. 2+ hours monitoring multiple sources
- Better Decision Making: High-quality, contextualized information leads to informed trading decisions
- 24/7 Coverage: System monitors markets continuously without human fatigue
- Cost Efficiency: Replaces need for multiple paid subscriptions and manual monitoring

**Scope of MVP (Version 1.0):**
- Data collection from 4 sources: News (RSS), Twitter, Ethereum blockchain, Price APIs
- Agent A (Noise Filter) implementation with rule-based filtering
- Alert delivery via Telegram bot, Email, and Web Dashboard
- User authentication and basic preference management
- Support for 500+ concurrent users
- Processing capacity of 10,000+ events per hour

**Out of Scope for MVP:**
- Agent B (Wallet Attribution), Agent C (Sentiment Analysis), Agent D (Portfolio Strategist)
- Multi-chain support (Solana, BSC, L2s)
- Mobile native applications (iOS/Android)
- B2B API access
- Advanced portfolio analytics
- Automated trading execution

## 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| **AETERNA** | Autonomous Alpha Engine - the system name |
| **Agent A** | The Sieve - noise filtering component |
| **Agent B** | The Profiler - wallet attribution (Phase II) |
| **Agent C** | The Quant - sentiment analysis (Phase II) |
| **Agent D** | The Strategist - portfolio personalization (Phase II) |
| **Alpha** | Excess returns or market edge in trading |
| **API** | Application Programming Interface |
| **DEX** | Decentralized Exchange |
| **DeFi** | Decentralized Finance |
| **Event** | A normalized data point from any source (news, tweet, transaction, price change) |
| **JWT** | JSON Web Token (authentication) |
| **L2** | Layer 2 blockchain scaling solution |
| **MAS** | Multi-Agent System |
| **MVP** | Minimum Viable Product |
| **On-Chain** | Activity recorded on a blockchain |
| **REST** | Representational State Transfer (API architecture) |
| **RSS** | Really Simple Syndication (news feed format) |
| **SRS** | Software Requirements Specification |
| **TPS** | Transactions Per Second |
| **UI/UX** | User Interface / User Experience |
| **Whale** | Large cryptocurrency holder/trader |
| **WebSocket** | Protocol for real-time bidirectional communication |

## 1.4 References

1. AETERNA Product Requirements Document (PRD.md) - v1.0
2. AETERNA Technical Architecture Document (ARCHITECTURE.md) - v1.0
3. AETERNA Development Roadmap (ROADMAP.md) - v1.0
4. AETERNA Risk Assessment (RISK_ASSESSMENT.md) - v1.0
5. IEEE Std 830-1998 - IEEE Recommended Practice for Software Requirements Specifications
6. Twitter API v2 Documentation - https://developer.twitter.com/en/docs/twitter-api
7. Ethereum JSON-RPC API Specification - https://ethereum.github.io/execution-apis/api-documentation/
8. Telegram Bot API Documentation - https://core.telegram.org/bots/api

## 1.5 Overview

This SRS is organized into 9 major sections:

- **Section 2** provides an overview of the system functions, user characteristics, constraints, and assumptions
- **Section 3** details specific functional and non-functional requirements
- **Section 4** describes system features in detail
- **Section 5** specifies external interfaces (user, hardware, software, communication)
- **Section 6** defines performance requirements
- **Section 7** outlines design constraints
- **Section 8** describes software system attributes (reliability, security, etc.)
- **Section 9** covers additional requirements not captured elsewhere

---

# 2. OVERALL DESCRIPTION

## 2.1 Product Perspective

### 2.1.1 System Context

AETERNA is a new, self-contained system that operates as a cloud-based SaaS application. It interfaces with:

**External Systems:**
- Twitter/X API (data source)
- Ethereum blockchain nodes via JSON-RPC (data source)
- News RSS feeds (data source)
- CoinGecko API (data source)
- Telegram Bot API (delivery channel)
- SendGrid Email API (delivery channel)
- Payment processors (Stripe - Phase II)

**System Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│                   EXTERNAL DATA SOURCES                 │
│   Twitter │ News RSS │ Ethereum │ Price APIs           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              LAYER 1: INGESTION ENGINE                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │Collectors│  │Normalizer│  │Validator │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
└───────┼─────────────┼─────────────┼───────────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      ▼
        ┌──────────────────────────┐
        │    EVENT QUEUE           │
        │    (RabbitMQ)            │
        └──────────┬───────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│         LAYER 2: PROCESSING ENGINE (Agent A)            │
│  ┌──────────────────────────────────────────┐          │
│  │  Multi-Source │ Engagement │ Bot Detection│          │
│  │  Verification │  Analysis  │ & Dedup      │          │
│  └──────────────┬───────────────────────────┘          │
│                 │                                        │
│                 ▼                                        │
│  ┌──────────────────────────┐                          │
│  │  Scoring & Prioritization│                          │
│  └──────────┬───────────────┘                          │
└─────────────┼──────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────┐
│           LAYER 3: DELIVERY ENGINE                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Telegram │  │  Email   │  │Dashboard │             │
│  │   Bot    │  │  Sender  │  │WebSocket │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
└───────┼─────────────┼─────────────┼───────────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      ▼
              ┌──────────────┐
              │   END USERS  │
              └──────────────┘
```

### 2.1.2 System Interfaces

**Data Storage:**
- PostgreSQL 15+ (primary database)
- Redis 7+ (caching and session management)

**Message Queue:**
- RabbitMQ 3.11+ (event streaming)

**Web Server:**
- FastAPI (backend REST API)
- React 18+ (frontend web application)

**Deployment Platform:**
- Railway or Render (cloud hosting)
- Docker containers

### 2.1.3 User Interfaces

1. **Web Dashboard** - Browser-based interface (desktop and mobile responsive)
2. **Telegram Bot Interface** - Command-based interaction via Telegram messenger
3. **Email Interface** - HTML email alerts with links to dashboard

### 2.1.4 Hardware Interfaces

None. AETERNA is a cloud-based application with no direct hardware interfaces.

### 2.1.5 Software Interfaces

**External APIs:**

| API | Purpose | Protocol | Authentication |
|-----|---------|----------|----------------|
| Twitter API v2 | Tweet collection | REST + WebSocket | Bearer Token (OAuth 2.0) |
| QuickNode/Alchemy | Ethereum data | JSON-RPC over HTTPS | API Key |
| CoinGecko API | Price data | REST | API Key (optional) |
| Telegram Bot API | Alert delivery | REST | Bot Token |
| SendGrid API | Email delivery | REST | API Key |

### 2.1.6 Communication Interfaces

- **HTTP/HTTPS** - All external API communications
- **WebSocket** - Real-time updates to web dashboard
- **AMQP** - Internal message queue protocol (RabbitMQ)
- **PostgreSQL Protocol** - Database connections

### 2.1.7 Memory Constraints

- Backend services: 512MB - 2GB RAM per service
- Database: Minimum 4GB RAM, recommended 8GB+
- Redis cache: 512MB - 1GB

### 2.1.8 Operations

**Normal Operations:**
- System runs 24/7 with minimal manual intervention
- Automated data collection and processing
- Self-healing services with automatic restart on failure

**Maintenance Operations:**
- Weekly database backups
- Monthly dependency updates
- Quarterly security audits

## 2.2 Product Functions

### 2.2.1 High-Level Functions

1. **Data Collection**
   - Continuously monitor 4 external data sources
   - Collect 10,000+ events per hour
   - Normalize data into unified format

2. **Intelligent Filtering**
   - Eliminate 90%+ of spam and noise
   - Score events by importance (0-100)
   - Prioritize events (HIGH/MEDIUM/LOW)

3. **Alert Generation**
   - Convert high-priority events into user alerts
   - Format alerts for different channels
   - Apply user preferences and rate limits

4. **Multi-Channel Delivery**
   - Deliver alerts via Telegram (primary)
   - Send email alerts (secondary)
   - Display in web dashboard (real-time)

5. **User Management**
   - User registration and authentication
   - Account linking (Telegram, email)
   - Preference management

6. **Analytics & Monitoring**
   - Track alert quality metrics
   - Monitor system performance
   - Collect user feedback

## 2.3 User Characteristics

### 2.3.1 User Personas

**Primary User: Active Crypto Trader**
- **Technical Expertise:** Medium to High
- **Domain Knowledge:** High (understands crypto markets)
- **Age Range:** 25-45
- **Usage Pattern:** Daily, multiple times per day
- **Goals:** Stay informed, make profitable trades, save time
- **Pain Points:** Information overload, missing important signals, late to market moves

**Secondary User: Part-Time Investor**
- **Technical Expertise:** Low to Medium
- **Domain Knowledge:** Medium (basic crypto understanding)
- **Age Range:** 30-55
- **Usage Pattern:** Few times per week
- **Goals:** Monitor portfolio, catch major news, avoid scams
- **Pain Points:** Don't have time to research, overwhelmed by complexity

**Tertiary User: Community Manager**
- **Technical Expertise:** Medium
- **Domain Knowledge:** High
- **Age Range:** 25-40
- **Usage Pattern:** Daily, needs to inform community
- **Goals:** Keep community updated, provide value, grow community
- **Pain Points:** Can't monitor 24/7, needs automated solution

## 2.4 Constraints

### 2.4.1 Regulatory Constraints

1. **Financial Disclaimer:** System must clearly state it provides information only, not financial advice
2. **GDPR Compliance:** Must comply with EU data protection regulations for EU users
3. **Data Privacy:** User data must be encrypted and securely stored
4. **Terms of Service:** Must have clear ToS and Privacy Policy

### 2.4.2 Hardware Limitations

1. **Cloud Resource Limits:** Initial deployment limited to budget constraints ($50-100/month)
2. **API Rate Limits:** Twitter API limited to 50 tweets/second (Basic tier)
3. **Database Size:** Initial PostgreSQL instance limited to 10GB storage

### 2.4.3 Interface Constraints

1. **Third-Party API Dependencies:** System reliability depends on external API availability
2. **Browser Compatibility:** Web dashboard must support Chrome, Firefox, Safari, Edge (last 2 versions)
3. **Mobile Responsiveness:** Dashboard must work on screens ≥320px wide

### 2.4.4 Parallel Operations

1. System must handle 1,000+ concurrent users
2. Multiple data collectors must run simultaneously
3. Alert delivery to multiple channels must be parallel (not sequential)

### 2.4.5 Audit Functions

1. All user actions must be logged (login, preferences, feedback)
2. All alerts sent must be tracked with delivery status
3. System errors must be logged with context

### 2.4.6 Higher-Order Language Requirements

1. Backend must be written in Python 3.11+
2. Frontend must use modern JavaScript (ES6+) with React
3. No legacy code dependencies

## 2.5 Assumptions and Dependencies

### 2.5.1 Assumptions

1. **User Assumptions:**
   - Users have basic understanding of cryptocurrency markets
   - Users have access to internet and modern web browsers
   - Users have Telegram accounts or can create one
   - Users are willing to pay $29/month for premium features

2. **Technical Assumptions:**
   - External APIs (Twitter, Ethereum nodes) will remain available and stable
   - Cloud hosting platform (Railway/Render) will maintain 99.5%+ uptime
   - PostgreSQL database will handle expected data volume (7M+ events/month)
   - Current technology stack will remain supported for 2+ years

3. **Business Assumptions:**
   - Crypto market will remain active (volatility drives demand for alerts)
   - Users prefer Telegram over other messaging platforms
   - Free tier will convert to paid at 10%+ rate
   - Competition won't drastically undercut pricing

### 2.5.2 Dependencies

**External Service Dependencies:**

1. **Critical (System Failure if Unavailable):**
   - PostgreSQL database
   - RabbitMQ message queue
   - Cloud hosting platform (Railway/Render)

2. **High Priority (Degraded Service if Unavailable):**
   - Twitter API (can operate without, but reduced value)
   - Ethereum node API (QuickNode/Alchemy)
   - Telegram Bot API

3. **Medium Priority (Graceful Degradation):**
   - SendGrid Email API (can queue and retry)
   - CoinGecko Price API (can use cached data temporarily)

**Library Dependencies:**
- Python: FastAPI, Celery, SQLAlchemy, Web3.py, python-telegram-bot
- JavaScript: React, Socket.io-client, TailwindCSS
- Infrastructure: Docker, Nginx

---

# 3. SPECIFIC REQUIREMENTS

## 3.1 Functional Requirements

### 3.1.1 Data Ingestion Requirements

**FR-DI-001: News Collection**
- **Priority:** P0 (Critical)
- **Description:** System shall collect cryptocurrency news from RSS feeds
- **Input:** RSS feed URLs (CoinDesk, CoinTelegraph, Decrypt)
- **Processing:** Parse RSS XML, extract article data
- **Output:** Normalized news event in JSON format
- **Performance:** Fetch new articles every 60 seconds
- **Error Handling:** Retry 3 times on failure, log errors

**FR-DI-002: Twitter Data Collection**
- **Priority:** P0 (Critical)
- **Description:** System shall collect crypto-related tweets in real-time
- **Input:** Twitter Filtered Stream API with crypto keywords
- **Processing:** Extract tweet text, author info, engagement metrics
- **Output:** Normalized social event in JSON format
- **Performance:** Handle 50+ tweets per second
- **Error Handling:** Reconnect automatically on stream disconnect

**FR-DI-003: Blockchain Data Collection**
- **Priority:** P0 (Critical)
- **Description:** System shall monitor Ethereum blockchain for large transactions
- **Input:** Ethereum node WebSocket connection
- **Processing:** Filter transactions >$1M USD, identify exchange addresses
- **Output:** Normalized on-chain event in JSON format
- **Performance:** <15 second latency (1-2 blocks)
- **Error Handling:** Switch to backup node on primary failure

**FR-DI-004: Price Data Collection**
- **Priority:** P1 (High)
- **Description:** System shall track cryptocurrency prices for top 100 assets
- **Input:** CoinGecko API (or similar)
- **Processing:** Calculate price changes (1h, 24h), detect significant moves (>5%)
- **Output:** Normalized price event in JSON format
- **Performance:** Poll every 60 seconds
- **Error Handling:** Use cached data if API unavailable, retry after 5 minutes

**FR-DI-005: Data Normalization**
- **Priority:** P0 (Critical)
- **Description:** System shall convert all source data into unified event schema
- **Input:** Raw events from any collector
- **Processing:** 
  - Map fields to standard schema
  - Extract mentioned entities (BTC, ETH, etc.)
  - Normalize timestamps to UTC ISO8601
  - Generate unique event ID
- **Output:** Normalized event conforming to schema
- **Performance:** <50ms per event
- **Validation:** All required fields must be present, reject invalid events

**FR-DI-006: Deduplication**
- **Priority:** P1 (High)
- **Description:** System shall prevent duplicate events within 1-hour window
- **Input:** Normalized event
- **Processing:** Generate content hash, check against recent events (Redis cache)
- **Output:** Boolean (duplicate or not)
- **Performance:** <10ms lookup time
- **Action:** If duplicate detected, discard event and log

### 3.1.2 Event Processing Requirements (Agent A)

**FR-EP-001: Multi-Source Verification**
- **Priority:** P0 (Critical)
- **Description:** System shall score events based on number of reporting sources
- **Input:** Event content, timestamp
- **Processing:** Query database for similar events in last 30 minutes
- **Output:** Source count (integer), similarity score (0-100)
- **Scoring Logic:**
  - 3+ sources = 100 points
  - 2 sources = 70 points
  - 1 source = 40 points
- **Performance:** <200ms per event

**FR-EP-002: Engagement Analysis**
- **Priority:** P1 (High)
- **Description:** System shall analyze social media engagement metrics
- **Input:** Social event with likes, retweets, followers
- **Processing:** Calculate engagement rate = (likes + retweets) / followers
- **Output:** Engagement score (0-100)
- **Scoring Logic:**
  - Engagement rate >5% = 100 points
  - Engagement rate 1-5% = 70 points
  - Engagement rate 0.1-1% = 40 points
  - Engagement rate <0.1% = 20 points
  - Verified account = +20 bonus points
- **Performance:** <50ms per event
- **Applicability:** Social media events only (skip for news/on-chain)

**FR-EP-003: Bot Detection**
- **Priority:** P1 (High)
- **Description:** System shall identify and filter bot-generated content
- **Input:** Event content and metadata
- **Processing:** Check for spam patterns:
  - Spam keywords ("airdrop", "giveaway", "click here", etc.)
  - Excessive links (>2)
  - Excessive hashtags (>5)
  - Generic username pattern (e.g., user12345)
- **Output:** Bot probability (0-100), Quality score (0-100)
- **Scoring Logic:** Quality score = 100 - bot probability
- **Performance:** <100ms per event

**FR-EP-004: Semantic Deduplication**
- **Priority:** P1 (High)
- **Description:** System shall detect semantically similar events (same story, different wording)
- **Input:** Event content
- **Processing:** 
  - Generate sentence embedding using sentence-transformers
  - Compare with recent events using cosine similarity
  - Threshold: similarity >0.9 = duplicate
- **Output:** Similarity score (0-1), duplicate flag (boolean)
- **Performance:** <500ms per event (including embedding generation)
- **Storage:** Store embeddings in database for future comparison

**FR-EP-005: Aggregate Scoring**
- **Priority:** P0 (Critical)
- **Description:** System shall calculate final event score from all checks
- **Input:** Scores from FR-EP-001 through FR-EP-004
- **Processing:** Weighted average:
  - Multi-source: 30%
  - Engagement: 20%
  - Bot detection: 30%
  - Semantic dedup: 20%
- **Output:** Final score (0-100), Priority (HIGH/MEDIUM/LOW)
- **Priority Thresholds:**
  - Score ≥80 = HIGH
  - Score 50-79 = MEDIUM
  - Score <50 = LOW
- **Performance:** <50ms calculation

**FR-EP-006: Event Storage**
- **Priority:** P0 (Critical)
- **Description:** System shall store processed events in database
- **Input:** Scored and prioritized event
- **Processing:** Insert into PostgreSQL `events` table with all metadata
- **Output:** Database record with unique ID
- **Performance:** <100ms per insert
- **Retention:** Delete events older than 7 days (automated cleanup job)

### 3.1.3 Alert Generation Requirements

**FR-AG-001: Alert Threshold Filtering**
- **Priority:** P0 (Critical)
- **Description:** System shall generate alerts only for HIGH and MEDIUM priority events
- **Input:** Processed event with priority
- **Processing:** 
  - If priority = HIGH: Generate alert immediately
  - If priority = MEDIUM: Check user preferences
  - If priority = LOW: Store but don't alert
- **Output:** Alert object or null
- **Performance:** <50ms decision time

**FR-AG-002: User Preference Filtering**
- **Priority:** P1 (High)
- **Description:** System shall respect user alert preferences
- **Input:** Alert candidate, user preferences
- **Processing:** Check:
  - Entity watchlist (if user specified tokens to track)
  - Alert frequency limit (max alerts per hour)
  - Quiet hours (if user enabled)
  - Channel preferences (Telegram, Email, Dashboard)
- **Output:** Filtered alert list per user
- **Performance:** <100ms per user

**FR-AG-003: Alert Formatting**
- **Priority:** P0 (Critical)
- **Description:** System shall format alerts for each delivery channel
- **Input:** Alert object
- **Processing:** Generate formatted message:
  - **Telegram:** Markdown format with emojis, max 4096 chars
  - **Email:** HTML format with styling, responsive design
  - **Dashboard:** JSON object for React component
- **Output:** Channel-specific formatted message
- **Template:** Include priority, event type, time, source, brief description, link
- **Performance:** <50ms per format

**FR-AG-004: Rate Limiting**
- **Priority:** P1 (High)
- **Description:** System shall limit alerts to prevent spam
- **Input:** User ID, timestamp
- **Processing:** Check alert count in last hour
- **Limit:** Maximum 10 alerts per hour per user (configurable)
- **Action:** If limit exceeded, queue additional alerts for next hour
- **Output:** Boolean (send now or queue)
- **Performance:** <10ms check

### 3.1.4 Alert Delivery Requirements

**FR-AD-001: Telegram Bot Delivery**
- **Priority:** P0 (Critical)
- **Description:** System shall deliver alerts via Telegram bot
- **Input:** Formatted Telegram message, user's telegram_id
- **Processing:** Call Telegram Bot API sendMessage endpoint
- **Output:** Delivery confirmation (success/failure)
- **Performance:** <2 seconds per message
- **Error Handling:** Retry up to 3 times on failure, then mark as failed
- **Fallback:** If Telegram fails, send email instead (if configured)

**FR-AD-002: Email Delivery**
- **Priority:** P1 (High)
- **Description:** System shall deliver alerts via email
- **Input:** Formatted HTML email, user's email address
- **Processing:** Call SendGrid API to send email
- **Output:** Delivery confirmation (success/failure)
- **Performance:** <3 seconds per email
- **Error Handling:** Retry up to 3 times with exponential backoff
- **Unsubscribe:** Include unsubscribe link in all emails

**FR-AD-003: Dashboard Real-Time Updates**
- **Priority:** P1 (High)
- **Description:** System shall push alerts to web dashboard in real-time
- **Input:** Alert object, list of connected users
- **Processing:** Send via WebSocket to all active dashboard connections
- **Output:** WebSocket message received by browser
- **Performance:** <1 second from alert generation to browser
- **Fallback:** If WebSocket unavailable, user sees alerts on page refresh

**FR-AD-004: Delivery Status Tracking**
- **Priority:** P1 (High)
- **Description:** System shall track alert delivery status
- **Input:** Alert ID, channel, delivery result
- **Processing:** Update `alerts` table with status and timestamp
- **Status Values:** PENDING, SENT, FAILED, QUEUED
- **Output:** Updated database record
- **Reporting:** Admin dashboard shows delivery success rate

### 3.1.5 User Management Requirements

**FR-UM-001: User Registration**
- **Priority:** P0 (Critical)
- **Description:** System shall allow new user registration
- **Input:** Email, password (min 8 chars, must include number and special char)
- **Processing:** 
  - Validate email format
  - Hash password using bcrypt
  - Create user record in database
  - Send email verification link
- **Output:** User account created, verification email sent
- **Performance:** <500ms
- **Validation:** Email must be unique, password must meet requirements

**FR-UM-002: User Authentication**
- **Priority:** P0 (Critical)
- **Description:** System shall authenticate users via JWT tokens
- **Input:** Email, password
- **Processing:** 
  - Verify email exists
  - Compare password hash
  - Generate JWT token (24-hour expiry)
- **Output:** JWT token or error message
- **Performance:** <200ms
- **Security:** Lock account after 5 failed attempts (15-minute cooldown)

**FR-UM-003: Telegram Account Linking**
- **Priority:** P0 (Critical)
- **Description:** System shall link user's Telegram account for alerts
- **Input:** User clicks /start command in Telegram bot
- **Processing:** 
  - Extract telegram_id from Telegram API
  - Generate unique linking code
  - User enters code on dashboard
  - Link telegram_id to user account
- **Output:** Telegram account linked, ready for alerts
- **Performance:** <2 seconds
- **Validation:** One Telegram account per user

**FR-UM-004: Preference Management**
- **Priority:** P1 (High)
- **Description:** System shall allow users to customize alert preferences
- **Input:** User selections via settings page
- **Preferences:**
  - Alert frequency (all, important only, daily digest)
  - Entity watchlist (specific tokens to monitor)
  - Quiet hours (start time, end time)
  - Delivery channels (Telegram on/off, Email on/off)
- **Processing:** Validate and save to `users.preferences` JSON field
- **Output:** Preferences updated confirmation
- **Performance:** <200ms

**FR-UM-005: Email Verification**
- **Priority:** P1 (High)
- **Description:** System shall verify user email addresses
- **Input:** User clicks verification link from email
- **Processing:** 
  - Validate token (must be <24 hours old)
  - Update user record: email_verified = true
- **Output:** Email verified, full access granted
- **Restriction:** Unverified users see alerts on dashboard only (no Telegram/Email)

### 3.1.6 Web Dashboard Requirements

**FR-WD-001: Landing Page**
- **Priority:** P0 (Critical)
- **Description:** System shall provide marketing landing page
- **Content:**
  - Value proposition headline
  - Feature highlights (3-5 key benefits)
  - Pricing information
  - Call-to-action buttons (Sign Up, Login)
  - Demo screenshots or video
- **Performance:** <2 second load time
- **Responsive:** Mobile-friendly design

**FR-WD-002: Authentication Pages**
- **Priority:** P0 (Critical)
- **Description:** System shall provide login and signup pages
- **Features:**
  - Email and password fields
  - Form validation (client-side and server-side)
  - Password strength indicator
  - "Forgot Password" link
  - "Remember Me" checkbox
- **Performance:** <1 second load time
- **Security:** HTTPS only, CSRF protection

**FR-WD-003: Main Dashboard**
- **Priority:** P0 (Critical)
- **Description:** System shall provide main alert feed interface
- **Layout:**
  - Header with user info and navigation
  - Sidebar with filters (priority, entity, date range)
  - Main content area with alert feed
  - Alert cards showing: priority badge, title, source, time, brief description
- **Functionality:**
  - Real-time updates via WebSocket
  - Infinite scroll or pagination
  - Click alert card to see details
  - Feedback buttons (useful / not relevant)
- **Performance:** Load initial 20 alerts in <2 seconds
- **Update:** New alerts appear within 1 second of generation

**FR-WD-004: Alert Details View**
- **Priority:** P1 (High)
- **Description:** System shall show detailed alert information
- **Content:**
  - Full event content
  - All metadata (source, time, entities, scores)
  - Link to original source (tweet, article, blockchain explorer)
  - Related alerts (same entity or topic)
- **Performance:** <500ms load time
- **Actions:** Share, Mark as read, Provide feedback

**FR-WD-005: Settings Page**
- **Priority:** P1 (High)
- **Description:** System shall provide user settings interface
- **Sections:**
  - Account (email, password change)
  - Notifications (Telegram linking, Email preferences)
  - Alert Preferences (watchlist, frequency, quiet hours)
  - Subscription (current plan, billing - Phase II)
- **Performance:** <1 second load time
- **Validation:** Real-time form validation

**FR-WD-006: Alert History**
- **Priority:** P2 (Medium)
- **Description:** System shall show past alerts
- **Features:**
  - List of all alerts sent to user
  - Filters by date, priority, entity
  - Search functionality
  - Export to CSV
- **Performance:** Load 50 alerts per page in <2 seconds
- **Retention:** Show alerts from last 30 days

### 3.1.7 Administrative Requirements

**FR-AD-001: System Monitoring**
- **Priority:** P1 (High)
- **Description:** System shall provide admin dashboard for monitoring
- **Metrics:**
  - Events ingested per hour
  - Events processed per hour
  - Alerts generated per hour
  - System uptime percentage
  - Error rate
  - Active users count
- **Performance:** Update metrics every 60 seconds
- **Access:** Admin users only

**FR-AD-002: Error Logging**
- **Priority:** P1 (High)
- **Description:** System shall log all errors with context
- **Information:**
  - Timestamp
  - Error message
  - Stack trace
  - User ID (if applicable)
  - Request context
- **Storage:** Send to Sentry or similar service
- **Retention:** 30 days
- **Alerting:** Send critical errors to admin via email

## 3.2 Non-Functional Requirements

### 3.2.1 Performance Requirements

**NFR-PERF-001: Data Ingestion Throughput**
- System shall process minimum 10,000 events per hour
- Target: 20,000+ events per hour
- Measurement: Events successfully added to queue / time period

**NFR-PERF-002: End-to-End Latency**
- System shall deliver alerts within 10 seconds of event occurrence
- Target: <5 seconds for critical alerts
- Measurement: Event timestamp → Alert delivery timestamp

**NFR-PERF-003: API Response Time**
- 95th percentile: <500ms
- 99th percentile: <1000ms
- Target: p50 <200ms
- Measurement: Time from request received to response sent

**NFR-PERF-004: Web Dashboard Load Time**
- Initial page load: <2 seconds (on 4G connection)
- Subsequent page loads: <1 second (with caching)
- Time to interactive: <3 seconds
- Measurement: Lighthouse performance score >80

**NFR-PERF-005: Database Query Performance**
- Simple queries (single table): <50ms
- Complex queries (joins): <200ms
- Full-text search: <500ms
- Measurement: Query execution time in PostgreSQL logs

**NFR-PERF-006: Concurrent User Capacity**
- System shall support 1,000+ concurrent users
- Target: 5,000+ concurrent users
- Measurement: Load testing with realistic user behavior

### 3.2.2 Reliability Requirements

**NFR-REL-001: System Uptime**
- Availability: 99.5% (minimum)
- Target: 99.9%
- Allowable downtime: 3.6 hours per month (minimum), 43 minutes per month (target)
- Measurement: Uptime monitoring service (UptimeRobot)

**NFR-REL-002: Data Durability**
- Zero data loss for user accounts and preferences
- Maximum 1-hour event data loss in disaster scenario
- Database backups: Every 6 hours, retained for 30 days

**NFR-REL-003: Error Rate**
- Application error rate: <1% of requests
- Alert delivery success rate: >99%
- Data collection success rate: >95% per source
- Measurement: Error count / Total requests

**NFR-REL-004: Graceful Degradation**
- If Twitter API fails: Continue with other sources, notify users
- If Telegram API fails: Fall back to email delivery
- If database becomes slow: Use Redis cache for reads
- If WebSocket fails: Fall back to HTTP polling

**NFR-REL-005: Recovery Time**
- Service restart: <60 seconds
- Database recovery: <10 minutes
- Full system recovery: <30 minutes
- Measurement: Mean Time To Recovery (MTTR)

### 3.2.3 Security Requirements

**NFR-SEC-001: Authentication & Authorization**
- All API endpoints (except public) require authentication
- JWT tokens expire after 24 hours
- Refresh tokens valid for 30 days
- Role-based access control (User, Admin)

**NFR-SEC-002: Password Security**
- Passwords hashed using bcrypt (cost factor 12)
- Minimum password length: 8 characters
- Must contain: uppercase, lowercase, number, special character
- Password reset tokens expire after 1 hour

**NFR-SEC-003: Data Encryption**
- All communications over HTTPS/TLS 1.3
- Database connections encrypted
- Sensitive data encrypted at rest (API keys, tokens)
- API keys stored in environment variables, never in code

**NFR-SEC-004: Input Validation**
- All user inputs validated and sanitized
- SQL injection prevention (parameterized queries)
- XSS prevention (escape HTML output)
- CSRF tokens on all state-changing operations

**NFR-SEC-005: Rate Limiting**
- API endpoints: 100 requests per minute per user
- Authentication endpoints: 5 attempts per 15 minutes per IP
- Public endpoints: 20 requests per minute per IP
- Action: Return HTTP 429 (Too Many Requests) when exceeded

**NFR-SEC-006: Security Auditing**
- Log all authentication attempts (success and failure)
- Log all privilege escalations
- Log all data access by admin users
- Retention: 90 days

### 3.2.4 Usability Requirements

**NFR-USA-001: User Onboarding**
- New user should complete onboarding in <2 minutes
- Maximum 3 steps to receive first alert
- Contextual help available on all pages
- Onboarding completion rate: >70%

**NFR-USA-002: User Interface Consistency**
- Consistent design system (colors, typography, spacing)
- All interactive elements clearly identifiable
- Feedback for all user actions (loading states, success/error messages)
- Mobile-responsive on all pages

**NFR-USA-003: Accessibility**
- WCAG 2.1 Level A compliance (minimum)
- Target: Level AA compliance
- Keyboard navigation support
- Screen reader compatible
- Color contrast ratio ≥4.5:1 for text

**NFR-USA-004: Error Messages**
- User-friendly error messages (no technical jargon)
- Provide actionable guidance ("Click here to...")
- Include error codes for support reference
- Examples:
  - Good: "Email address already in use. Try logging in instead."
  - Bad: "Error 409: Duplicate key constraint violation"

**NFR-USA-005: Documentation**
- In-app help documentation
- FAQ page covering common questions
- Video tutorials for key features
- API documentation (Phase II)

### 3.2.5 Scalability Requirements

**NFR-SCAL-001: Horizontal Scaling**
- Backend services must be stateless (scale by adding instances)
- Database must support read replicas for scaling reads
- Message queue must support clustering
- Target: 10x current capacity without architecture changes

**NFR-SCAL-002: Database Scalability**
- Support 10 million+ events in database
- Query performance must not degrade with data volume
- Use partitioning for large tables (by date)
- Archive strategy for old data

**NFR-SCAL-003: User Growth**
- Support 10,000+ users without infrastructure changes
- Support 100,000+ users with horizontal scaling
- Cost per user should decrease with scale (economies of scale)

### 3.2.6 Maintainability Requirements

**NFR-MAINT-001: Code Quality**
- Code coverage: Minimum 70% for critical paths
- Linting: All code must pass linters (Black for Python, ESLint for JavaScript)
- Type hints: All Python functions must have type hints
- Documentation: All public functions must have docstrings

**NFR-MAINT-002: Modularity**
- Each data collector must be independent (can run standalone)
- Agents must be loosely coupled (communicate via queue)
- Frontend components should be reusable
- Configuration must be externalized (environment variables)

**NFR-MAINT-003: Monitoring & Debugging**
- All services must expose health check endpoints
- All services must emit structured logs (JSON format)
- All services must expose Prometheus metrics
- Distributed tracing for request flows (optional: OpenTelemetry)

**NFR-MAINT-004: Deployment**
- Deployment must be automated (CI/CD pipeline)
- Zero-downtime deployments (rolling updates)
- Easy rollback mechanism (previous Docker image)
- Deployment time: <10 minutes

### 3.2.7 Portability Requirements

**NFR-PORT-001: Platform Independence**
- Backend must run on any platform supporting Docker
- Frontend must work in all modern browsers (last 2 versions)
- No OS-specific dependencies

**NFR-PORT-002: Cloud Provider Flexibility**
- System should not be tightly coupled to specific cloud provider
- Use standard protocols (HTTP, WebSocket, AMQP)
- Avoid vendor-specific services for core functionality
- Target: Migrate to different provider in <1 week

**NFR-PORT-003: Data Portability**
- User data must be exportable (JSON format)
- Event data must be exportable (CSV format)
- Standard database (PostgreSQL) for easy migration
- No proprietary data formats

### 3.2.8 Localization Requirements (Future)

**NFR-LOC-001: Internationalization Support**
- MVP: English only
- Phase II: Support for additional languages (Spanish, Chinese)
- All user-facing strings must be externalized (i18n files)
- Date/time formatting based on user locale
- Currency formatting for international pricing

---

# 4. SYSTEM FEATURES

This section describes major system features in detail using the format:
- Feature ID
- Description
- Priority
- Stimulus/Response Sequences
- Functional Requirements

## 4.1 Data Ingestion System

### 4.1.1 Feature: News Article Collection

**Feature ID:** F-DI-NEWS  
**Description:** Continuously collect cryptocurrency news from RSS feeds  
**Priority:** P0 (Critical)  

**Stimulus/Response:**

1. **Stimulus:** System timer triggers every 60 seconds
2. **Response:** 
   - Connect to RSS feed URLs (CoinDesk, CoinTelegraph, Decrypt)
   - Parse XML response
   - Extract: title, content, author, published date, URL
   - Normalize into event format
   - Publish to event queue
   - Log success/failure

**Inputs:**
- RSS feed URLs (configured in environment variables)
- Feed format: RSS 2.0 or Atom XML

**Processing:**
```python
def collect_news():
    feeds = [
        'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'https://cointelegraph.com/rss',
        'https://decrypt.co/feed'
    ]
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                event = {
                    'event_id': generate_uuid(),
                    'source_type': 'news',
                    'source_name': extract_source_name(feed_url),
                    'timestamp': parse_date(entry.published),
                    'title': entry.title,
                    'content': entry.summary,
                    'url': entry.link,
                    'entities': extract_entities(entry.title + entry.summary)
                }
                publish_to_queue(event)
        except Exception as e:
            log_error(f"Failed to fetch {feed_url}", e)
```

**Outputs:**
- Normalized news events published to RabbitMQ queue
- Metrics: articles collected per feed, errors encountered

**Performance Requirements:**
- Poll frequency: Every 60 seconds
- Processing time: <5 seconds per feed
- Throughput: 50+ articles per hour

**Error Handling:**
- Network errors: Retry 3 times with exponential backoff
- Parse errors: Log and skip malformed entries
- Queue errors: Log and alert admin

**Related Requirements:**
- FR-DI-001
- FR-DI-005
- NFR-PERF-001
- NFR-REL-003

---

### 4.1.2 Feature: Twitter Stream Processing

**Feature ID:** F-DI-TWITTER  
**Description:** Real-time collection of crypto-related tweets  
**Priority:** P0 (Critical)  

**Stimulus/Response:**

1. **Stimulus:** Tweet matching filter rules arrives via Twitter Filtered Stream API
2. **Response:**
   - Receive tweet JSON
   - Extract: text, author info, engagement metrics, timestamp
   - Normalize into event format
   - Publish to event queue
   - Maintain connection health

**Inputs:**
- Twitter Filtered Stream API WebSocket connection
- Filter rules: Keywords ($BTC, $ETH, Bitcoin, Ethereum) + influencer accounts

**Processing:**
```python
def process_twitter_stream():
    stream_rules = [
        {'value': '$BTC OR $ETH OR Bitcoin OR Ethereum', 'tag': 'crypto_keywords'},
        {'value': 'from:VitalikButerin OR from:cz_binance', 'tag': 'influencers'}
    ]
    
    stream = TwitterStream(bearer_token=TWITTER_TOKEN, rules=stream_rules)
    
    for tweet in stream:
        event = {
            'event_id': tweet['id'],
            'source_type': 'social',
            'source_name': 'twitter',
            'timestamp': tweet['created_at'],
            'content': tweet['text'],
            'author': {
                'username': tweet['author']['username'],
                'followers': tweet['author']['public_metrics']['followers_count'],
                'verified': tweet['author']['verified']
            },
            'engagement': {
                'likes': tweet['public_metrics']['like_count'],
                'retweets': tweet['public_metrics']['retweet_count'],
                'replies': tweet['public_metrics']['reply_count']
            },
            'entities': extract_entities(tweet['text'])
        }
        publish_to_queue(event)
```

**Outputs:**
- Normalized social events published to RabbitMQ queue
- Metrics: tweets collected per minute, stream uptime

**Performance Requirements:**
- Latency: <100ms from tweet creation to event publication
- Throughput: 50+ tweets per second (API limit)
- Uptime: >99% (auto-reconnect on disconnect)

**Error Handling:**
- Connection drop: Auto-reconnect with exponential backoff (max 5 minutes)
- Rate limit exceeded: Wait and log warning
- Parse errors: Log and skip malformed tweets

**Related Requirements:**
- FR-DI-002
- FR-DI-005
- NFR-PERF-001
- NFR-REL-001

---

### 4.1.3 Feature: Blockchain Transaction Monitoring

**Feature ID:** F-DI-BLOCKCHAIN  
**Description:** Monitor Ethereum blockchain for large transactions  
**Priority:** P0 (Critical)  

**Stimulus/Response:**

1. **Stimulus:** New block confirmed on Ethereum blockchain
2. **Response:**
   - Receive block data via WebSocket
   - Extract all transactions
   - Filter: USD value >$1M
   - Identify exchange addresses (Binance, Coinbase, etc.)
   - Normalize into event format
   - Publish to event queue

**Inputs:**
- Ethereum node WebSocket connection (QuickNode/Alchemy)
- Exchange address database (pre-populated)

**Processing:**
```python
def monitor_ethereum():
    w3 = Web3(Web3.WebsocketProvider(ETHEREUM_NODE_URL))
    
    # Subscribe to new blocks
    block_filter = w3.eth.filter('latest')
    
    for block_hash in block_filter.get_new_entries():
        block = w3.eth.get_block(block_hash, full_transactions=True)
        
        for tx in block.transactions:
            # Calculate USD value
            eth_amount = w3.fromWei(tx.value, 'ether')
            usd_value = eth_amount * get_eth_price()
            
            if usd_value > 1_000_000:  # $1M threshold
                event = {
                    'event_id': tx.hash.hex(),
                    'source_type': 'onchain',
                    'blockchain': 'ethereum',
                    'timestamp': datetime.utcfromtimestamp(block.timestamp),
                    'from_address': tx['from'],
                    'to_address': tx['to'],
                    'amount_eth': float(eth_amount),
                    'usd_value': usd_value,
                    'metadata': {
                        'from_label': get_address_label(tx['from']),
                        'to_label': get_address_label(tx['to'])
                    },
                    'entities': ['ETH']
                }
                publish_to_queue(event)
```

**Outputs:**
- Normalized on-chain events published to RabbitMQ queue
- Metrics: transactions monitored, large transfers detected

**Performance Requirements:**
- Latency: <15 seconds (1-2 block delay)
- Throughput: Monitor all Ethereum transactions (~1M per day)
- Connection uptime: >99%

**Error Handling:**
- Connection drop: Switch to backup node, reconnect
- Price API failure: Use cached ETH price (warn if >5 minutes old)
- Parse errors: Log and skip malformed transactions

**Related Requirements:**
- FR-DI-003
- FR-DI-005
- NFR-PERF-002
- NFR-REL-004

---

## 4.2 Event Processing System (Agent A)

### 4.2.1 Feature: Intelligent Noise Filtering

**Feature ID:** F-EP-FILTER  
**Description:** Filter spam and low-quality events using multi-factor scoring  
**Priority:** P0 (Critical)  

**Stimulus/Response:**

1. **Stimulus:** Event arrives in processing queue
2. **Response:**
   - Run multi-source verification
   - Analyze engagement (if social)
   - Detect bot patterns
   - Check semantic similarity
   - Calculate final score
   - Assign priority (HIGH/MEDIUM/LOW)
   - Store in database
   - Forward HIGH/MEDIUM to alert generation

**Inputs:**
- Normalized event from ingestion queue
- Historical events (for comparison)
- Configuration: scoring weights, thresholds

**Processing Flow:**
```
┌─────────────────┐
│  Event from     │
│  Queue          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Multi-Source    │ → Score 1 (0-100)
│ Verification    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Engagement      │ → Score 2 (0-100)
│ Analysis        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Bot Detection   │ → Score 3 (0-100)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Semantic        │ → Score 4 (0-100)
│ Deduplication   │   + Duplicate flag
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Aggregate       │ → Final Score (0-100)
│ Scoring         │   + Priority (H/M/L)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  [Store]  [Alert?]
```

**Outputs:**
- Scored event with final_score and priority
- Database record in `events` table
- HIGH/MEDIUM events forwarded to alert generation
- LOW events stored only

**Performance Requirements:**
- Processing time: <5 seconds per event (including all checks)
- Throughput: 100+ events per second
- Accuracy: 90%+ of HIGH priority events are actually important (measured via user feedback)

**Configuration:**
```yaml
scoring_weights:
  multi_source: 0.30
  engagement: 0.20
  bot_detection: 0.30
  semantic_dedup: 0.20

priority_thresholds:
  high: 80
  medium: 50
```

**Related Requirements:**
- FR-EP-001 through FR-EP-006
- NFR-PERF-001
- NFR-USA-004

---

## 4.3 Alert Delivery System

### 4.3.1 Feature: Telegram Bot Alert Delivery

**Feature ID:** F-AD-TELEGRAM  
**Description:** Deliver alerts to users via Telegram bot  
**Priority:** P0 (Critical)  

**Stimulus/Response:**

1. **Stimulus:** HIGH or MEDIUM priority alert generated
2. **Response:**
   - Check user has Telegram linked
   - Format alert for Telegram (Markdown)
   - Send via Telegram Bot API
   - Record delivery status
   - Handle delivery errors

**Inputs:**
- Alert object (event + priority + formatting)
- User's telegram_id
- Telegram bot token

**Alert Format:**
```markdown
🚨 [HIGH] Whale Alert

📊 **Event:** 50M USDT moved to Binance

🕒 **Time:** 2 minutes ago

🔗 **Source:** Ethereum Blockchain

💡 **Context:** Large transfer to exchange often precedes selling

👁️ View Details: https://app.aeterna.ai/alerts/abc123
```

**Processing:**
```python
async def send_telegram_alert(user_id, alert):
    user = get_user(user_id)
    
    if not user.telegram_id:
        log_warning(f"User {user_id} has no Telegram linked")
        return False
    
    # Format message
    message = format_telegram_message(alert)
    
    # Send via Telegram Bot API
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        
        # Record success
        update_alert_status(alert.id, 'SENT', 'telegram')
        return True
        
    except TelegramError as e:
        # Handle errors
        if "bot was blocked by the user" in str(e):
            # User blocked bot, disable Telegram for this user
            disable_telegram_alerts(user_id)
        
        # Retry logic
        if retry_count < 3:
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            return await send_telegram_alert(user_id, alert, retry_count + 1)
        else:
            # Max retries exceeded, try email fallback
            update_alert_status(alert.id, 'FAILED', 'telegram')
            await send_email_alert(user_id, alert)  # Fallback
            return False
```

**Outputs:**
- Telegram message delivered to user
- Alert status updated in database
- Delivery metrics logged

**Performance Requirements:**
- Delivery time: <2 seconds
- Success rate: >99%
- Retry attempts: Up to 3 with exponential backoff

**Error Scenarios:**
- User blocked bot → Disable Telegram, notify user via email
- Rate limit exceeded → Queue and retry after cooldown
- Network error → Retry with backoff
- Bot token invalid → Alert admin immediately

**Related Requirements:**
- FR-AD-001
- FR-AD-004
- NFR-PERF-002
- NFR-REL-003

---

## 4.4 User Management System

### 4.4.1 Feature: User Registration & Onboarding

**Feature ID:** F-UM-REGISTER  
**Description:** Allow new users to create accounts and complete onboarding  
**Priority:** P0 (Critical)  

**Stimulus/Response:**

1. **Stimulus:** User submits registration form
2. **Response:**
   - Validate input (email format, password strength)
   - Check email uniqueness
   - Hash password (bcrypt)
   - Create user record
   - Send verification email
   - Log user in with JWT token
   - Redirect to onboarding flow

**Onboarding Flow:**
```
Step 1: Account Created
   ↓
Step 2: Verify Email (optional skip)
   ↓
Step 3: Link Telegram (required for alerts)
   ↓
Step 4: Set Preferences (optional skip)
   ↓
Step 5: Complete! → Dashboard
```

**Inputs:**
- Registration form:
  - Email (required)
  - Password (required, min 8 chars)
  - Terms acceptance (required)

**Validation Rules:**
```python
def validate_registration(email, password):
    errors = []
    
    # Email validation
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        errors.append("Invalid email format")
    
    if User.query.filter_by(email=email).first():
        errors.append("Email already in use")
    
    # Password validation
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain uppercase letter")
    
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain number")
    
    if not re.search(r'[!@#$%^&*]', password):
        errors.append("Password must contain special character")
    
    return errors
```

**Outputs:**
- User account created in database
- JWT token for authentication
- Verification email sent
- Onboarding status tracked

**Success Metrics:**
- Registration completion rate: >90%
- Onboarding completion rate: >70%
- Time to first alert: <24 hours

**Related Requirements:**
- FR-UM-001
- FR-UM-003
- FR-UM-004
- FR-UM-005
- NFR-USA-001

---

## 4.5 Web Dashboard

### 4.5.1 Feature: Real-Time Alert Feed

**Feature ID:** F-WD-FEED  
**Description:** Display real-time stream of personalized alerts  
**Priority:** P0 (Critical)  

**Stimulus/Response:**

1. **Stimulus:** User navigates to dashboard
2. **Response:**
   - Authenticate user (JWT)
   - Load initial 20 alerts from database
   - Establish WebSocket connection
   - Display alerts in feed
   - Receive new alerts in real-time via WebSocket
   - Update feed without page refresh

**UI Layout:**
```
┌────────────────────────────────────────────────────────┐
│  AETERNA          [Search]       [Profile] [Settings]  │
├──────────┬─────────────────────────────────────────────┤
│          │                                             │
│ Filters  │  ┌──────────────────────────────────────┐ │
│          │  │ 🚨 HIGH | Whale Alert                │ │
│ Priority │  │ 50M USDT moved to Binance            │ │
│ ☑ HIGH   │  │ ⏰ 2 minutes ago  📍 Ethereum        │ │
│ ☑ MEDIUM │  │ [View Details]                        │ │
│ ☐ LOW    │  └──────────────────────────────────────┘ │
│          │                                             │
│ Entity   │  ┌──────────────────────────────────────┐ │
│ ☑ BTC    │  │ ⚠️ MEDIUM | Price Alert              │ │
│ ☑ ETH    │  │ Bitcoin up 5.2% in last hour         │ │
│ ☐ SOL    │  │ ⏰ 15 minutes ago  📍 CoinGecko       │ │
│          │  │ [View Details]                        │ │
│ Date     │  └──────────────────────────────────────┘ │
│ [Today ▼]│                                             │
│          │  [Load More Alerts...]                     │
│          │                                             │
└──────────┴─────────────────────────────────────────────┘
```

**WebSocket Integration:**
```javascript
// Client-side
import { io } from 'socket.io-client';

const socket = io(BACKEND_URL, {
  auth: { token: getJWTToken() }
});

socket.on('connect', () => {
  console.log('Connected to alert stream');
});

socket.on('new_alert', (alert) => {
  // Prepend new alert to feed
  setAlerts(prevAlerts => [alert, ...prevAlerts]);
  
  // Show browser notification if enabled
  if (Notification.permission === 'granted') {
    new Notification(alert.title, {
      body: alert.description,
      icon: '/logo.png'
    });
  }
});

socket.on('disconnect', () => {
  console.log('Disconnected, will reconnect...');
  // Socket.io handles reconnection automatically
});
```

**Server-side:**
```python
# FastAPI + Socket.IO
from socketio import AsyncServer

sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.on('connect')
async def connect(sid, environ, auth):
    # Authenticate user
    token = auth.get('token')
    user = verify_jwt(token)
    
    if user:
        # Associate socket with user
        await sio.save_session(sid, {'user_id': user.id})
        return True
    else:
        return False  # Reject connection

async def broadcast_alert(user_id, alert):
    # Find user's socket sessions
    for sid in get_user_sessions(user_id):
        await sio.emit('new_alert', alert, room=sid)
```

**Outputs:**
- Real-time alert feed displayed to user
- Browser notifications (if permitted)
- Alert count badge updated

**Performance Requirements:**
- Initial load: <2 seconds
- WebSocket latency: <1 second
- Smooth scrolling (60 FPS)

**Responsive Design:**
- Desktop: 2-column layout (sidebar + feed)
- Tablet: Collapsible sidebar
- Mobile: Single column, filters in modal

**Related Requirements:**
- FR-WD-003
- FR-AD-003
- NFR-PERF-004
- NFR-USA-002

---

# 5. EXTERNAL INTERFACE REQUIREMENTS

## 5.1 User Interfaces

### 5.1.1 Web Application Interface

**Browser Support:**
- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

**Screen Resolutions:**
- Desktop: 1920×1080 (primary), down to 1280×720
- Tablet: 768×1024 (portrait and landscape)
- Mobile: 375×667 minimum (iPhone SE)

**Color Scheme:**
- Primary: #3B82F6 (Blue)
- Secondary: #10B981 (Green)
- Danger: #EF4444 (Red)
- Warning: #F59E0B (Amber)
- Background: #F9FAFB (Light), #111827 (Dark mode)
- Text: #111827 (Light mode), #F9FAFB (Dark mode)

**Typography:**
- Font Family: Inter (sans-serif)
- Headings: 600 weight
- Body: 400 weight
- Code: JetBrains Mono (monospace)

**Accessibility:**
- WCAG 2.1 Level A compliance (minimum)
- Keyboard navigation support
- Focus indicators on all interactive elements
- Alt text for all images
- ARIA labels where appropriate

### 5.1.2 Telegram Bot Interface

**Commands:**
```
/start - Link your AETERNA account
/status - View your alert settings
/alerts - View recent alerts (last 24h)
/portfolio - View your portfolio (Phase II)
/settings - Quick settings menu
/help - Get help
/stop - Pause all alerts
```

**Message Format:**
- Use Markdown formatting
- Emojis for visual clarity
- Max 4096 characters per message
- Inline buttons for quick actions

**Example Interaction:**
```
User: /start

Bot: Welcome to AETERNA! 🚀

To receive crypto alerts, link your Telegram account:

1. Go to https://app.aeterna.ai/settings
2. Click "Link Telegram"
3. Enter this code: ABC123

Code expires in 10 minutes.

[Link Now]
```

## 5.2 Hardware Interfaces

**Not Applicable** - AETERNA is a cloud-based application with no direct hardware interfaces.

## 5.3 Software Interfaces

### 5.3.1 Twitter API v2

**Interface Type:** REST API + WebSocket Streaming  
**Purpose:** Collect real-time tweets  
**Protocol:** HTTPS  
**Data Format:** JSON  

**Endpoints Used:**
- `POST /2/tweets/search/stream/rules` - Add filter rules
- `GET /2/tweets/search/stream` - Receive filtered tweets (stream)
- `GET /2/tweets/:id` - Get tweet details
- `GET /2/users/:id` - Get user details

**Authentication:** Bearer Token (OAuth 2.0)

**Rate Limits:**
- Filtered stream: 50 tweets/second (Basic tier)
- Tweet lookup: 300 requests per 15 minutes

**Error Codes:**
- 429: Rate limit exceeded
- 401: Invalid authentication
- 503: Service unavailable

**Sample Request:**
```bash
GET /2/tweets/search/stream
Authorization: Bearer <token>
```

**Sample Response:**
```json
{
  "data": {
    "id": "1234567890",
    "text": "Bitcoin just hit $50K! 🚀 #BTC",
    "created_at": "2025-01-15T10:30:00.000Z",
    "author_id": "987654321",
    "public_metrics": {
      "like_count": 150,
      "retweet_count": 45,
      "reply_count": 12
    }
  },
  "includes": {
    "users": [{
      "id": "987654321",
      "username": "crypto_whale",
      "public_metrics": {
        "followers_count": 100000
      },
      "verified": true
    }]
  }
}
```

### 5.3.2 Ethereum JSON-RPC API

**Interface Type:** JSON-RPC over HTTPS/WebSocket  
**Purpose:** Monitor blockchain transactions  
**Protocol:** HTTPS (polling) or WSS (streaming)  
**Data Format:** JSON

**Methods Used:**
- `eth_blockNumber` - Get latest block number
- `eth_getBlockByNumber` - Get block with transactions
- `eth_getTransactionReceipt` - Get transaction details
- `eth_subscribe` (WebSocket) - Subscribe to new blocks

**Authentication:** API Key in URL or header

**Rate Limits:**
- QuickNode: 300 compute units/second (free tier)
- Alchemy: 330 compute units/second (free tier)

**Sample Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "eth_getBlockByNumber",
  "params": ["latest", true],
  "id": 1
}
```

**Sample Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "number": "0x1234567",
    "timestamp": "0x61e2c3d0",
    "transactions": [{
      "hash": "0xabc123...",
      "from": "0xdef456...",
      "to": "0x789abc...",
      "value": "0x8ac7230489e80000"
    }]
  }
}
```

### 5.3.3 CoinGecko API

**Interface Type:** REST API  
**Purpose:** Fetch cryptocurrency prices  
**Protocol:** HTTPS  
**Data Format:** JSON

**Endpoints Used:**
- `GET /api/v3/simple/price` - Get current prices
- `GET /api/v3/coins/markets` - Get market data

**Authentication:** API Key (optional, higher rate limits)

**Rate Limits:**
- Free: 10-50 calls/minute
- Pro: 500 calls/minute

**Sample Request:**
```bash
GET /api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true
```

**Sample Response:**
```json
{
  "bitcoin": {
    "usd": 50000,
    "usd_24h_change": 3.5
  },
  "ethereum": {
    "usd": 3000,
    "usd_24h_change": -2.1
  }
}
```

### 5.3.4 Telegram Bot API

**Interface Type:** REST API  
**Purpose:** Send alerts to users  
**Protocol:** HTTPS  
**Data Format:** JSON

**Endpoints Used:**
- `POST /bot<token>/sendMessage` - Send text message
- `POST /bot<token>/getUpdates` - Receive bot commands
- `POST /bot<token>/setWebhook` - Set webhook for updates

**Authentication:** Bot token in URL

**Rate Limits:**
- 30 messages per second to different users
- 1 message per second to same user

**Sample Request:**
```json
{
  "chat_id": 123456789,
  "text": "🚨 *HIGH* Whale Alert\n\n50M USDT moved to Binance",
  "parse_mode": "Markdown",
  "disable_web_page_preview": false
}
```

**Sample Response:**
```json
{
  "ok": true,
  "result": {
    "message_id": 456,
    "date": 1642253400,
    "text": "🚨 HIGH Whale Alert..."
  }
}
```

### 5.3.5 SendGrid Email API

**Interface Type:** REST API  
**Purpose:** Send email alerts  
**Protocol:** HTTPS  
**Data Format:** JSON

**Endpoints Used:**
- `POST /v3/mail/send` - Send email

**Authentication:** API Key in header

**Rate Limits:**
- Free: 100 emails/day
- Essentials: 40,000 emails/month

**Sample Request:**
```json
{
  "personalizations": [{
    "to": [{"email": "user@example.com"}],
    "subject": "[AETERNA] High Priority Alert"
  }],
  "from": {"email": "alerts@aeterna.ai"},
  "content": [{
    "type": "text/html",
    "value": "<html>...</html>"
  }]
}
```

## 5.4 Communication Interfaces

### 5.4.1 HTTP/HTTPS Protocol

**Usage:**
- All external API calls (Twitter, Ethereum, CoinGecko, Telegram, SendGrid)
- Frontend ↔ Backend API communication
- Webhook callbacks

**Requirements:**
- TLS 1.3 minimum
- Certificate validation
- Timeout: 30 seconds for HTTP requests

### 5.4.2 WebSocket Protocol

**Usage:**
- Real-time updates from backend to web dashboard
- Twitter Filtered Stream
- Ethereum block subscription

**Requirements:**
- WSS (WebSocket Secure) only
- Automatic reconnection with exponential backoff
- Ping/pong heartbeat every 30 seconds

**WebSocket Events:**
```javascript
// Client → Server
'connect' - Establish connection
'authenticate' - Send JWT token
'subscribe' - Subscribe to alert feed

// Server → Client  
'authenticated' - Authentication successful
'new_alert' - New alert available
'disconnect' - Connection closed
```

### 5.4.3 Database Protocol

**Protocol:** PostgreSQL native protocol  
**Port:** 5432 (default)  
**Encryption:** SSL/TLS required  
**Connection Pool:** 10-50 connections

### 5.4.4 Message Queue Protocol

**Protocol:** AMQP 0-9-1 (RabbitMQ)  
**Port:** 5672 (AMQP), 5671 (AMQPS)  
**Exchange Type:** Topic exchange  
**Routing Keys:** `events.{source_type}.{entity}`

**Example:**
- `events.news.btc`
- `events.social.eth`
- `events.onchain.usdt`

---

# 6. PERFORMANCE REQUIREMENTS

## 6.1 Response Time

**API Endpoints:**
- Authentication: <200ms (p95)
- GET requests: <500ms (p95)
- POST requests: <1000ms (p95)
- WebSocket latency: <100ms

**Page Load:**
- Landing page: <2 seconds (First Contentful Paint)
- Dashboard: <2 seconds (with 20 alerts)
- Settings page: <1 second

**Alert Delivery:**
- Event occurrence → Alert delivery: <10 seconds (p95)
- Critical alerts: <5 seconds (p95)

## 6.2 Throughput

**Data Ingestion:**
- Minimum: 10,000 events per hour
- Target: 20,000 events per hour
- Peak: 50,000 events per hour (burst capacity)

**Event Processing:**
- Minimum: 100 events per second
- Target: 200 events per second

**Alert Delivery:**
- 1,000 alerts per minute across all channels
- 100 concurrent Telegram sends
- 50 concurrent email sends

**API Requests:**
- 1,000 requests per second (total)
- 10 requests per second per user

## 6.3 Capacity

**User Capacity:**
- Concurrent users: 1,000+ (minimum), 5,000+ (target)
- Total registered users: 10,000+ (6 months)

**Data Storage:**
- Events: 10 million records (1-month retention at 10K/hour)
- Users: 10,000 records with preferences
- Alerts: 1 million records (7-day retention)

**Database Size:**
- Initial: 1GB
- 6 months: 20GB
- Growth rate: ~3GB per month

## 6.4 Degradation Modes

**Graceful Degradation:**

1. **High Load (>80% capacity):**
   - Reduce polling frequency for price data
   - Increase alert batching interval
   - Disable LOW priority alert processing

2. **Very High Load (>95% capacity):**
   - Process only HIGH priority events
   - Delay MEDIUM priority processing
   - Rate limit API requests more aggressively

3. **Service Failure:**
   - Twitter unavailable: Continue with other sources
   - Database slow: Use Redis cache for reads
   - Telegram unavailable: Fall back to email

**Performance Monitoring:**
- Alert if p95 latency >2× target
- Alert if throughput <50% of minimum
- Alert if error rate >5%

---

# 7. DESIGN CONSTRAINTS

## 7.1 Technology Constraints

**Backend:**
- Must use Python 3.11+ (no earlier versions)
- Must use async/await patterns for I/O operations
- Cannot use blocking operations in event loop

**Frontend:**
- Must use React 18+ (for concurrent features)
- Must support browsers with JavaScript enabled only
- No Flash, Java applets, or other plugins

**Database:**
- PostgreSQL 15+ required (for JSONB improvements)
- Cannot use NoSQL for primary data storage (consistency requirements)
- Must use connection pooling (pgBouncer or SQLAlchemy pool)

**Deployment:**
- Must run in Docker containers
- Must support horizontal scaling (stateless services)
- Cannot require specific cloud provider features

## 7.2 Standards Compliance

**Security Standards:**
- OWASP Top 10 compliance
- PCI DSS Level 2 (when payment processing added)
- GDPR compliance for EU users

**Web Standards:**
- HTML5 semantic markup
- CSS3 for styling
- ECMAScript 2020+ (ES11+)
- WCAG 2.1 Level A accessibility

**API Standards:**
- RESTful API design principles
- JSON:API specification (optional, preferred)
- OpenAPI 3.0 specification for documentation

**Coding Standards:**
- Python: PEP 8 style guide
- JavaScript: Airbnb style guide
- Consistent naming conventions
- Code review required before merge

## 7.3 Resource Constraints

**Budget:**
- Infrastructure: $50-100/month (MVP)
- APIs: $200-500/month
- Total: $250-600/month

**Development Time:**
- Total: 12 weeks (3 months)
- Team: 1-2 developers
- No more than 600 development hours

**Memory:**
- Backend service: <2GB RAM per instance
- Database: 4-8GB RAM
- Redis: 512MB-1GB RAM

**Storage:**
- Database: 10GB initial, 50GB max (first 6 months)
- File storage: <1GB (logs, backups)

## 7.4 Regulatory Constraints

**Financial Regulations:**
- Cannot provide financial advice (must have disclaimer)
- Cannot execute trades on behalf of users (MVP)
- Must not store payment card data (use Stripe)

**Data Privacy:**
- GDPR compliance (right to access, delete, export)
- CCPA compliance (California users)
- User consent for email marketing
- Clear privacy policy and ToS

**Crypto Regulations:**
- Not a crypto exchange (no trading)
- Information service only
- No custody of user funds
- No KYC/AML requirements (information service)

---

# 8. SOFTWARE SYSTEM ATTRIBUTES

## 8.1 Reliability

**Mean Time Between Failures (MTBF):**
- Target: >720 hours (30 days)
- Minimum: >168 hours (7 days)

**Mean Time To Repair (MTTR):**
- Critical failures: <30 minutes
- Non-critical failures: <2 hours

**Fault Tolerance:**
- Services must auto-restart on crash
- Database must have point-in-time recovery
- Message queue must persist messages

**Data Integrity:**
- All database transactions use ACID guarantees
- Event processing is idempotent (safe to retry)
- No duplicate alerts sent to users

**Backup and Recovery:**
- Database backups every 6 hours
- Backup retention: 30 days
- Recovery Point Objective (RPO): 6 hours
- Recovery Time Objective (RTO): 30 minutes

## 8.2 Availability

**Uptime Target:**
- 99.5% availability (minimum)
- 99.9% availability (target)
- Measured monthly

**Downtime Allowance:**
- 99.5% = 3.6 hours per month
- 99.9% = 43 minutes per month

**Planned Maintenance:**
- Maximum 2 hours per month
- Scheduled during low-traffic hours (3-5 AM UTC)
- Announced 24 hours in advance

**Monitoring:**
- Uptime monitoring via UptimeRobot (1-minute checks)
- Health checks on all services
- Alerting via PagerDuty or email

**High Availability Features:**
- Multiple backend instances (load balanced)
- Database read replicas (future)
- CDN for static assets (Vercel/Cloudflare)

## 8.3 Security

**Authentication:**
- JWT tokens with 24-hour expiry
- Refresh tokens with 30-day expiry
- Bcrypt password hashing (cost factor 12)
- Multi-factor authentication (Phase II)

**Authorization:**
- Role-based access control (RBAC)
- Principle of least privilege
- Admin actions require separate authentication

**Data Protection:**
- TLS 1.3 for all communications
- Encrypted database connections
- API keys stored in environment variables
- Secrets managed via cloud provider (not in code)

**Vulnerability Management:**
- Automated dependency scanning (Dependabot)
- Weekly security updates
- Quarterly security audits (Phase II)
- Bug bounty program (Phase II)

**Security Headers:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

**Input Validation:**
- Server-side validation for all inputs
- SQL injection prevention (parameterized queries)
- XSS prevention (escape HTML output)
- CSRF tokens for state-changing operations

**Rate Limiting:**
- Authentication: 5 attempts per 15 minutes per IP
- API endpoints: 100 requests per minute per user
- Public endpoints: 20 requests per minute per IP

## 8.4 Maintainability

**Code Quality:**
- Test coverage: 70%+ for critical paths
- Linting: Black (Python), ESLint (JavaScript)
- Type checking: mypy (Python), TypeScript (future)
- Code reviews required for all changes

**Documentation:**
- README in every directory
- Docstrings for all public functions
- API documentation (auto-generated from OpenAPI spec)
- Architecture decision records (ADRs)

**Modularity:**
- Microservices architecture (loosely coupled)
- Clear separation of concerns
- Dependency injection where appropriate
- Configuration externalized

**Logging:**
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for tracing requests
- Log aggregation (Sentry, CloudWatch)

**Monitoring:**
- Prometheus metrics for all services
- Grafana dashboards for visualization
- Alerting on anomalies
- Performance profiling (cProfile, React DevTools)

**Deployment:**
- CI/CD pipeline (GitHub Actions)
- Automated tests before deployment
- Blue-green deployments (zero downtime)
- Rollback mechanism (<5 minutes)

## 8.5 Portability

**Platform Independence:**
- Docker containers (runs on any OS)
- No OS-specific code
- Standard protocols (HTTP, WebSocket, AMQP)

**Cloud Portability:**
- Not locked to specific cloud provider
- Infrastructure as Code (Docker Compose, Terraform)
- Standard managed services (PostgreSQL, Redis)
- Can migrate between Railway, Render, AWS, GCP

**Data Portability:**
- Standard data formats (JSON, CSV)
- Export functionality for user data
- Database dumps in standard SQL format
- API for programmatic data access (Phase II)

**Browser Portability:**
- Works in all modern browsers
- Progressive enhancement (core features work without JavaScript)
- No browser-specific features

---

# 9. OTHER REQUIREMENTS

## 9.1 Legal Requirements

**Terms of Service:**
- Clear terms for service usage
- Service provided "as-is" without guarantees
- Limitation of liability
- Dispute resolution process

**Privacy Policy:**
- What data is collected (email, preferences, usage data)
- How data is used (alerts, analytics, product improvement)
- Data sharing practices (no selling to third parties)
- User rights (access, deletion, export)
- Cookie policy

**Disclaimers:**
- "AETERNA provides information only, not financial advice"
- "Past performance does not guarantee future results"
- "Cryptocurrency investing carries risk, invest responsibly"
- Displayed prominently on landing page and ToS

**Intellectual Property:**
- Copyright notice on all pages
- AETERNA name and logo trademarked (Phase II)
- Open source licenses for dependencies (MIT, Apache 2.0)

**DMCA Compliance:**
- Designated agent for copyright claims
- Takedown process for user-generated content (future)

## 9.2 Operational Requirements

**Deployment:**
- Must deploy to production weekly (during development)
- Must deploy hotfixes within 4 hours of critical bugs
- Deployment must be automated (no manual steps)

**Backup:**
- Database backups every 6 hours (automated)
- Backup testing monthly (restore to staging)
- Backup storage: 30-day retention

**Monitoring:**
- 24/7 uptime monitoring
- Real-time error tracking (Sentry)
- Performance monitoring (Prometheus + Grafana)
- Cost monitoring (AWS Cost Explorer, Railway dashboard)

**Support:**
- MVP: Email support only (support@aeterna.ai)
- Response time: <24 hours for general inquiries
- Response time: <4 hours for critical issues
- Phase II: In-app chat support

## 9.3 Business Rules

**User Account Rules:**
- One account per email address
- One Telegram account per user account
- Unverified emails can view dashboard only (no alerts)
- Account deletion: 30-day grace period before permanent deletion

**Alert Rules:**
- Maximum 10 alerts per hour per user (configurable)
- HIGH priority always delivered (unless rate limit)
- MEDIUM priority respects user preferences
- LOW priority stored but not delivered
- Duplicate detection: 1-hour window

**Free Tier Limits:**
- All features accessible during beta (no paid tier yet)
- Phase II: Free tier = 5 alerts/day, 24-hour delay

**Subscription Rules:**
- Monthly billing cycle
- Cancel anytime (no refunds for partial months)
- Downgrade takes effect at end of billing period
- Upgrade takes effect immediately

## 9.4 Database Requirements

**Schema Version Control:**
- All schema changes via migrations (Alembic for Python)
- Migration files in version control
- Rollback capability for all migrations

**Data Retention:**
- Events: 7 days
- Alerts: 30 days (user-facing)
- User data: Until account deletion + 30 days
- Logs: 90 days
- Backups: 30 days

**Indexes:**
- Primary key on all tables (UUID)
- Index on `events.timestamp` (for time-range queries)
- Index on `events.priority` (for filtering)
- Index on `alerts.user_id` (for user queries)
- Index on `alerts.sent_at` (for history queries)

**Data Privacy:**
- Personal data encrypted at rest
- No sensitive data in logs
- User data anonymized in analytics

## 9.5 Internationalization (Future)

**Language Support:**
- MVP: English only
- Phase II: Spanish, Chinese (Simplified)
- All user-facing strings externalized

**Localization:**
- Date/time formatting per locale
- Number formatting (comma vs. period)
- Currency symbols and formatting
- Time zone conversion (UTC internally, user TZ on display)

## 9.6 Analytics Requirements

**User Analytics:**
- Track user signups, logins, feature usage
- Funnel analysis (signup → verify → link Telegram → first alert)
- Retention cohorts (weekly, monthly)
- Churn analysis

**System Analytics:**
- Events ingested per source per day
- Alert delivery success rate per channel
- Processing latency percentiles
- Error rates by component

**Business Analytics:**
- Daily/Monthly Active Users (DAU/MAU)
- Conversion rate (free → paid)
- Churn rate
- Net Promoter Score (NPS)

**Privacy:**
- No personally identifiable information (PII) in analytics
- IP addresses anonymized
- GDPR-compliant analytics (consent required)
- Optional: Self-hosted Plausible or Matomo (no Google Analytics)

## 9.7 Testing Requirements

**Unit Tests:**
- All filtering functions (Agent A)
- All API endpoints
- All database models
- Coverage: 70%+ for critical paths

**Integration Tests:**
- End-to-end event flow (collector → processor → alert)
- User registration and authentication
- Telegram bot linking
- Alert delivery to all channels

**Performance Tests:**
- Load test: 10,000 events per hour
- Stress test: 50,000 events per hour (burst)
- Concurrency test: 1,000 simultaneous users
- Database query performance test

**Security Tests:**
- Penetration testing (Phase II)
- SQL injection attempts
- XSS attempts
- CSRF attempts
- Authentication bypass attempts

**Usability Tests:**
- User onboarding flow (5-10 testers)
- Dashboard navigation
- Mobile responsiveness
- Accessibility testing (screen reader)

---

# APPENDICES

## Appendix A: Glossary

See Section 1.3 for definitions.

## Appendix B: Database Schema

See Section 3.1.6 (FR-EP-006) and ARCHITECTURE.md for full schema.

## Appendix C: API Endpoints

See ARCHITECTURE.md Appendix C for complete API reference.


**Document Status: DRAFT - Pending Review & Approval**
