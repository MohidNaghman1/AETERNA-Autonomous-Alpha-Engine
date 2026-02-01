# AETERNA: Autonomous Alpha Engine
## Product Requirements Document (PRD)

**Version:** 1.0  
**Date:** January 2025  
**Status:** Pre-Development Planning  
**Timeline:** 2-3 Month MVP Development

---

## 1. Executive Summary

### Product Vision
AETERNA is a next-generation Synthetic Research Desk that transforms overwhelming crypto market data into actionable trading insights. It replaces a team of junior analysts by processing 1,000+ data points per second and delivering 3-5 high-value alerts daily.

### Core Value Proposition
**"From 10 Million Daily Signals to 5 Actionable Alerts"**

AETERNA provides contextual intelligence like:
> "The trader who correctly predicted the last 3 BTC crashes just moved $10M to an exchange—and you hold 32% of your portfolio in the affected asset."

### Target Market
- **Primary:** Active crypto traders managing $10K-$500K portfolios
- **Secondary:** Crypto trading communities (Discord/Telegram)
- **Future:** Hedge funds, trading desks, fintech platforms

---

## 2. Problem Statement

### The Core Problem
Modern crypto traders face an **information overload crisis**:
- 500,000+ tweets/day about crypto
- 10,000+ on-chain transactions/minute
- 50+ news sources publishing 24/7
- 100s of whale wallets to monitor

### Human Limitations
- Can process only ~50 items/day
- Reaction time: minutes to hours (market moves in seconds)
- Emotional bias and fatigue
- Can't operate 24/7

### Why Existing Solutions Fail

| Solution Type | Problem |
|--------------|----------|
| **News Aggregators** | No context, no prioritization, information overload |
| **Alert Bots** | Spam everything, no intelligence, alert fatigue |
| **On-Chain Trackers** | Anonymous addresses, no attribution, no "why" |
| **Trading Dashboards** | Display data but don't analyze, passive not active |

---

## 3. Product Goals & Success Metrics

### Primary Goals (2-3 Month MVP)

#### Goal 1: Intelligent Signal Filtering
**Objective:** Reduce information overload by 99%  
**Success Metric:** Process 10,000+ events/day → deliver 3-5 high-quality alerts

#### Goal 2: Contextual Intelligence
**Objective:** Transform raw data into actionable insights  
**Success Metric:** 80%+ of alerts lead to user action (trade, portfolio adjustment, or watchlist add)

#### Goal 3: Real-Time Performance
**Objective:** Beat human reaction time  
**Success Metric:** <10 seconds from event occurrence to alert delivery

#### Goal 4: User Engagement
**Objective:** Build initial user base and validate product-market fit  
**Success Metric:** 
- 500+ beta users in first month
- 30% weekly active user rate
- <5 average daily alerts per user

### North Star Metric
**"Time from Signal to Action"**  
Target: <10 seconds (vs. industry average of 30+ seconds)

---

## 4. User Personas

### Persona 1: Active Retail Trader "Alex"
- **Demographics:** 28 years old, full-time trader
- **Portfolio Size:** $50K-$200K
- **Pain Points:** 
  - Misses important news while sleeping
  - Can't track all whale wallets manually
  - Often enters trades too late
- **Needs:** Real-time alerts, whale tracking, portfolio-specific insights
- **Willingness to Pay:** $50-100/month

### Persona 2: Part-Time Trader "Sarah"
- **Demographics:** 35 years old, trades after work
- **Portfolio Size:** $10K-$50K
- **Pain Points:**
  - Limited time to research
  - Overwhelmed by crypto Twitter
  - Wants to know only what matters to her portfolio
- **Needs:** Filtered news, personalized alerts, simple interface
- **Willingness to Pay:** $20-50/month

### Persona 3: Community Manager "Mike"
- **Demographics:** 32 years old, runs a 10K-member crypto Discord
- **Pain Points:**
  - Needs to keep community informed 24/7
  - Can't afford a full analyst team
  - Members want real-time insights
- **Needs:** Community-wide alerts, branded bot, custom watchlists
- **Willingness to Pay:** $300-1000/month

---

## 5. Feature Requirements

### 5.1 MVP Features (Month 1-3) - MUST HAVE

#### Feature 1: Multi-Source Data Ingestion
**Priority:** P0 (Critical)  
**Description:** Collect and normalize data from multiple sources

**Data Sources (MVP):**
1. **Crypto News:** CoinDesk, CoinTelegraph, Decrypt (via RSS/APIs)
2. **Social Media:** Twitter/X API (crypto-related tweets)
3. **On-Chain Data:** Ethereum mainnet (major transfers >$1M)
4. **Market Data:** Price feeds from CoinGecko/CoinMarketCap

**Acceptance Criteria:**
- ✅ Ingest minimum 1,000 events/hour
- ✅ Normalize all events into unified schema
- ✅ <100ms ingestion latency per event
- ✅ 99% uptime for data pipelines

**Technical Requirements:**
- Event streaming architecture (Kafka/RabbitMQ)
- Data normalization layer
- Deduplication logic
- Timestamp synchronization

---

#### Feature 2: Intelligent Noise Filtering (Agent A - "The Sieve")
**Priority:** P0 (Critical)  
**Description:** Filter out spam, bot tweets, and low-signal events

**Filtering Logic:**
1. **Multi-Source Verification:** Event reported by 2+ credible sources
2. **Engagement Analysis:** Check social metrics (likes, retweets, replies)
3. **Bot Detection:** Identify and filter bot-generated content
4. **Semantic Deduplication:** Remove duplicate stories with different wording

**Acceptance Criteria:**
- ✅ Eliminate 90%+ of noise/spam
- ✅ Assign confidence score (0-100) to each event
- ✅ Process 100+ events/second
- ✅ <200ms processing time per event

**Output:** Scored events (HIGH/MEDIUM/LOW priority)

---

#### Feature 3: Basic Alert System
**Priority:** P0 (Critical)  
**Description:** Deliver filtered, prioritized alerts to users

**Alert Types (MVP):**
1. **Price Alerts:** Significant price movements (>5% in 1 hour)
2. **News Alerts:** Breaking news from verified sources
3. **Whale Alerts:** Large on-chain transfers (>$1M)

**Delivery Channels (MVP):**
- Telegram Bot (primary)
- Email (secondary)
- Web Dashboard (read-only)

**Acceptance Criteria:**
- ✅ <10 seconds from event detection to alert delivery
- ✅ Average 3-5 alerts per user per day
- ✅ 99% delivery success rate
- ✅ Zero duplicate alerts

**Alert Format:**
```
🚨 [PRIORITY] Alert Type
📊 Event: <Clear description>
⏰ Time: <Timestamp>
🔗 Source: <Link to source>
📈 Potential Impact: <Brief analysis>
```

---

#### Feature 4: Web Dashboard (Read-Only MVP)
**Priority:** P1 (High)  
**Description:** Simple web interface to view alerts and configure preferences

**Core Pages:**
1. **Live Feed:** Real-time stream of filtered events
2. **My Alerts:** Personal alert history
3. **Settings:** Alert preferences, notification channels
4. **Portfolio (Basic):** Manual portfolio entry for context

**Acceptance Criteria:**
- ✅ Mobile-responsive design
- ✅ Real-time updates (WebSocket)
- ✅ <2 second page load time
- ✅ Clean, intuitive UI

**Tech Stack:**
- Frontend: React.js + TailwindCSS
- Real-time: Socket.io / WebSocket
- Hosting: Vercel/Netlify

---

#### Feature 5: User Authentication & Onboarding
**Priority:** P1 (High)  
**Description:** Simple sign-up, login, and onboarding flow

**Authentication:**
- Email + Password (primary)
- Google OAuth (optional)
- Telegram OAuth (for bot linking)

**Onboarding Flow:**
1. Sign up / Login
2. Connect Telegram account
3. (Optional) Add portfolio holdings
4. Set alert preferences
5. Receive first alert within 24 hours

**Acceptance Criteria:**
- ✅ <2 minutes to complete onboarding
- ✅ 70%+ completion rate
- ✅ Email verification within 5 minutes

---

### 5.2 Phase II Features (Month 4-6) - SHOULD HAVE

#### Feature 6: Wallet Clustering & Attribution (Agent B - "The Profiler")
**Description:** Identify whale entities and calculate win-rates

**Capabilities:**
- Cluster wallets by behavioral patterns
- Attribute wallets to known entities (VCs, whales, funds)
- Calculate historical win-rate for each entity
- Generate "Whale Resume" profiles

**Impact:** Transform "0x1234...abcd moved $10M" into "Andreessen Horowitz (85% win-rate) moved $10M"

---

#### Feature 7: Sentiment & Impact Analysis (Agent C - "The Quant")
**Description:** Determine market impact probability

**Capabilities:**
- Sentiment scoring (bullish/bearish/neutral)
- Volatility prediction (1-10 scale)
- "Priced-in" assessment
- Historical comparison with similar events

---

#### Feature 8: Portfolio-Personalized Alerts (Agent D - "The Strategist")
**Description:** Match global events to user's specific portfolio

**Capabilities:**
- Portfolio impact scoring
- Risk profile customization (conservative/moderate/aggressive)
- Suggested actions (BUY/SELL/HOLD/WATCH)
- Position-weighted relevance

---

### 5.3 Future Features (Month 7+) - NICE TO HAVE

1. **Advanced Analytics:** Historical backtesting, alert performance tracking
2. **Social Features:** Share alerts, community insights, leaderboards
3. **API Access:** For third-party integrations
4. **Mobile Apps:** iOS and Android native apps
5. **Advanced Chains:** Solana, Binance Smart Chain, L2s (Arbitrum, Optimism)
6. **Automated Trading:** Execute trades based on alerts (with user approval)

---

## 6. Non-Functional Requirements

### Performance
- **Latency:** <10 seconds end-to-end (event → alert)
- **Throughput:** Process 10,000+ events/hour
- **Uptime:** 99.5% (target 99.9% in production)

### Scalability
- Support 1,000+ concurrent users (MVP)
- Scale to 10,000+ users (Month 6)
- Horizontally scalable architecture

### Security
- HTTPS/TLS for all communications
- Encrypted storage for user data
- Rate limiting on APIs
- Regular security audits

### Reliability
- Automated failover for critical services
- Data backup every 6 hours
- Disaster recovery plan
- Error monitoring and alerting (Sentry/DataDog)

### Compliance
- GDPR compliance (for EU users)
- User data privacy controls
- Terms of Service & Privacy Policy
- DMCA compliance for content

---

## 7. User Journeys

### Journey 1: New User Onboarding
1. User discovers AETERNA via Twitter/crypto community
2. Lands on marketing website
3. Signs up with email (2 minutes)
4. Connects Telegram bot
5. (Optional) Adds portfolio holdings
6. Sets alert preferences (frequency, types)
7. Receives first high-quality alert within 24 hours
8. Takes action based on alert (trade or add to watchlist)
9. Returns to dashboard to see more insights
10. Converts to paid tier after 7-day trial

### Journey 2: Daily Active User
1. Receives Telegram alert: "🚨 HIGH: Major BTC whale moved $50M to Binance"
2. Opens alert to see full context
3. Checks web dashboard for additional analysis
4. Reviews portfolio impact
5. Makes informed trading decision
6. Marks alert as "Useful" or "Not Relevant" (feedback)
7. Alert quality improves over time based on feedback

### Journey 3: Community Manager
1. Signs up for Community Bot tier
2. Invites AETERNA bot to Discord server
3. Configures alert channel and permissions
4. Sets custom watchlist (specific tokens for community)
5. Bot posts real-time alerts to community
6. Community engagement increases
7. Renews subscription monthly

---

## 8. Business Model & Monetization

### Pricing Strategy (MVP Focus)

#### Free Tier (Lead Generation)
- **Price:** $0/month
- **Features:**
  - Basic news feed (1-hour delay)
  - 5 alerts/day
  - Web dashboard access
  - Community Discord access
- **Goal:** 1,000+ free users in Month 1

#### Pro Tier (Target Market)
- **Price:** $29/month
- **Features:**
  - Real-time news feed
  - 25 alerts/day
  - Telegram notifications
  - Basic whale tracking (top 50 entities)
  - Portfolio integration
- **Goal:** 100+ paid users by Month 3 ($2,900 MRR)

### Revenue Projections (Conservative)

**Month 3 (MVP Launch):**
- 1,000 free users
- 50 paid users × $29 = $1,450 MRR
- Annual run rate: ~$17K ARR

**Month 6 (Phase II):**
- 5,000 free users
- 250 paid users × $29 = $7,250 MRR
- 5 community subscriptions × $500 = $2,500 MRR
- Total: $9,750 MRR (~$117K ARR)

**Month 12 (Full Launch):**
- 20,000 free users
- 1,000 paid users × $29 = $29,000 MRR
- 50 community subscriptions × $500 = $25,000 MRR
- 2 enterprise clients × $5,000 = $10,000 MRR
- Total: $64,000 MRR (~$768K ARR)

---

## 9. Competitive Analysis

### Direct Competitors

| Competitor | Strengths | Weaknesses | AETERNA Advantage |
|-----------|-----------|------------|------------------|
| **Nansen** | Great wallet analytics, strong brand | Expensive ($150/mo), complex UI, no personalization | Better UX, personalized alerts, lower price |
| **Arkham Intelligence** | Good wallet attribution | Limited alert system, no sentiment analysis | Multi-agent intelligence, compound signals |
| **LunarCrush** | Social sentiment tracking | No on-chain data, basic alerts | Combined social + on-chain + news |
| **Glassnode** | Deep on-chain metrics | Too technical, no alerts, expensive | Actionable alerts, simpler interface |
| **CoinMarketAlert** | Simple price alerts | No intelligence, spam alerts | AI-powered filtering, contextual insights |

### AETERNA's Unique Positioning

**"The Only System That Connects All Dots"**

✅ **Multi-Modal Intelligence:** News + Social + On-Chain + Whale Attribution  
✅ **Personalized:** Portfolio-aware alerts  
✅ **Actionable:** Clear insights with suggested actions  
✅ **Fast:** <10 second latency  
✅ **Affordable:** $29/month (vs. competitors at $100-300/month)

---

## 10. Risks & Mitigation Strategies

### Technical Risks

#### Risk 1: Data Source Reliability
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Use multiple redundant data sources
- Implement circuit breakers for failing sources
- Cache recent data for temporary outages
- Monitor source health in real-time

#### Risk 2: AI Model Performance
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Start with rule-based systems, gradually introduce ML
- Use proven models (GPT-4, Claude) for MVP
- Implement human-in-the-loop for quality control
- A/B test model changes before full rollout

#### Risk 3: Scalability Issues
**Impact:** Medium  
**Probability:** High  
**Mitigation:**
- Design for horizontal scaling from day 1
- Use managed services (AWS, GCP) with auto-scaling
- Load test before each major launch
- Implement rate limiting and quotas

### Business Risks

#### Risk 4: Low User Engagement
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Aggressive beta testing program
- Iterate based on user feedback weekly
- Track engagement metrics daily
- Implement referral program for growth

#### Risk 5: Regulatory Changes
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Not providing financial advice (disclaimer)
- User-controlled alert preferences
- Compliance with data privacy laws (GDPR)
- Legal counsel review before launch

#### Risk 6: Competitor Response
**Impact:** Medium  
**Probability:** High  
**Mitigation:**
- Move fast - launch MVP in 2 months
- Focus on unique features (multi-agent system)
- Build network effects (data flywheel)
- Strong brand and community

---

## 11. Dependencies & Assumptions

### Technical Dependencies
- Twitter/X API access (cost: ~$100-500/month)
- OpenAI/Anthropic API access (cost: ~$500-2000/month)
- Blockchain node infrastructure (Ethereum, cost: ~$100-500/month)
- Cloud hosting (AWS/GCP, cost: ~$500-1000/month)

### Team Assumptions
- 1 Full-stack Developer (or yourself)
- 1 ML/AI Engineer (can be same person or contractor)
- 1 Part-time Designer (for UI/UX)
- Total: 1-2 people for MVP

### Market Assumptions
- Crypto market remains active (bull or bear, volatility = need for alerts)
- Telegram remains popular among crypto traders
- Users willing to pay for high-quality filtered information
- Demand for personalized crypto intelligence tools

---

## 12. Success Criteria

### MVP Launch (Month 3)
✅ **Product:**
- 4 core features shipped (ingestion, filtering, alerts, dashboard)
- <10 second latency end-to-end
- 90%+ uptime

✅ **Users:**
- 500+ registered users
- 50+ paying users
- 30% weekly active rate

✅ **Quality:**
- 80%+ of alerts marked "useful" by users
- <5 alerts per user per day
- <1% spam/false positives

### Phase II (Month 6)
✅ **Product:**
- Wallet attribution live
- Sentiment analysis operational
- Portfolio personalization working

✅ **Business:**
- $10K+ MRR
- 5+ community subscriptions
- Featured in 2+ crypto media outlets

✅ **Engagement:**
- 50% weekly active rate
- 3+ NPS score
- 20% monthly user growth

---

## 13. Out of Scope (for MVP)

❌ **Not Building in 2-3 Months:**
- Mobile native apps (iOS/Android)
- Automated trading execution
- Multi-chain support beyond Ethereum
- API access for third parties
- Advanced analytics dashboard
- Social features (leaderboards, sharing)
- Custom AI model training
- White-label solutions
- On-premise deployment

---

## 14. Open Questions

1. **Data Costs:** What is realistic budget for Twitter API, blockchain nodes, and AI APIs?
2. **Legal:** Do we need financial advisor licenses? (Likely no if "for informational purposes only")
3. **Partnerships:** Should we partner with existing platforms (CoinMarketCap, DeFi Llama) for data?
4. **Branding:** Is "AETERNA" the final name? Should we consider something more accessible?
5. **Localization:** Focus on English only, or support multiple languages from day 1?

---

## 15. Approval & Sign-Off

**Document Owner:** Mohid Naghman
**Status:** ✅ Ready for Technical Architecture Phase  
**Next Steps:** 
1. Review and approve this PRD
2. Create detailed technical architecture document
3. Build development roadmap with sprint planning
4. Set up development environment
5. Begin MVP development

---
