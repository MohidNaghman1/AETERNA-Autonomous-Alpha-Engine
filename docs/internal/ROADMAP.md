# AETERNA: 2-3 Month Development Roadmap
## Sprint Planning & Execution Timeline

**Version:** 1.0  
**Target Timeline:** 2-3 Months (8-12 weeks)  
**Team Size:** 1-2 developers  
**Methodology:** Agile with 2-week sprints

---

## Overview

This roadmap breaks down the AETERNA MVP into **6 sprints** (2 weeks each), totaling **12 weeks (3 months)**.

**Goal:** Launch a functional MVP with:
- ✅ Multi-source data ingestion
- ✅ Intelligent noise filtering (Agent A)
- ✅ Real-time alerts via Telegram & Email
- ✅ Web dashboard
- ✅ 500+ beta users

---

## Sprint Structure

Each sprint includes:
1. **Goals:** What we're building
2. **Deliverables:** Specific outputs
3. **Tasks:** Step-by-step implementation
4. **Success Criteria:** How we know it's done
5. **Risks:** Potential blockers

---

## 📅 Timeline Overview

```
┌────────────────────────────────────────────────────┐
│                   PROJECT TIMELINE                         │
│                                                              │
│  Sprint 1  │  Sprint 2  │  Sprint 3  │  Sprint 4-6      │
│ (Week 1-2)│ (Week 3-4)│ (Week 5-6)│ (Week 7-12)      │
│           │           │           │                  │
│ Foundation│ Processing│ Delivery  │ Integration &    │
│ & Ingestion│ Engine    │ Layer     │ Launch           │
└────────────────────────────────────────────────────┘
```

---

# SPRINT 1: Foundation & Data Ingestion
**Duration:** Week 1-2 (10 working days)  
**Focus:** Set up infrastructure + build data collectors

## Goals
1. Set up development environment
2. Build and test 4 data collectors
3. Implement data normalization pipeline
4. Set up event queue (RabbitMQ)
5. Basic database schema

## Detailed Tasks

### Day 1-2: Project Setup & Infrastructure

**Tasks:**
- [ ] **Day 1 Morning:** Project structure setup
  ```
  aeterna/
  ├── backend/
  │   ├── collectors/      # Data collection services
  │   ├── agents/          # Processing agents
  │   ├── api/             # REST API
  │   ├── database/        # DB models & migrations
  │   ├── utils/           # Helpers
  │   ├── config.py
  │   └── requirements.txt
  ├── frontend/
  │   ├── src/
  │   ├── public/
  │   ├── package.json
  │   └── tailwind.config.js
  ├── docker-compose.yml
  ├── .env.example
  └── README.md
  ```

- [ ] **Day 1 Afternoon:** Docker setup
  - Docker Compose with PostgreSQL, Redis, RabbitMQ
  - Test all services are running
  - Create `.env` file with configuration

- [ ] **Day 2 Morning:** Database schema
  - Create tables: `users`, `events`, `alerts`, `portfolios`
  - Set up SQLAlchemy models
  - Run initial migrations

- [ ] **Day 2 Afternoon:** API keys & accounts
  - Register Twitter Developer account
  - Get QuickNode/Alchemy API key (Ethereum)
  - Set up Telegram bot via BotFather
  - Configure SendGrid for emails
  - Store all keys in `.env`

**Deliverables:**
- ✅ Working Docker environment
- ✅ Database schema created
- ✅ All API keys obtained
- ✅ Git repository initialized

---

### Day 3-4: News & Price Data Collectors

**Tasks:**
- [ ] **Day 3:** News Collector
  - Implement RSS feed parser (CoinDesk, CoinTelegraph, Decrypt)
  - Test fetching articles every 60 seconds
  - Output to console (JSON format)
  - Add basic error handling

- [ ] **Day 4:** Price Data Collector
  - Integrate CoinGecko API
  - Fetch top 100 cryptos every 60 seconds
  - Calculate price change alerts (>5% in 1 hour)
  - Test and validate output

**Deliverables:**
- ✅ News collector fetching 10+ articles/hour
- ✅ Price collector tracking 100+ assets
- ✅ Both outputting normalized JSON

---

### Day 5-6: Social & On-Chain Collectors

**Tasks:**
- [ ] **Day 5:** Twitter Collector
  - Implement Twitter Filtered Stream API
  - Filter by crypto keywords ($BTC, $ETH, etc.)
  - Track engagement metrics (likes, retweets)
  - Test with live stream (monitor 10+ tweets/min)

- [ ] **Day 6:** On-Chain Collector (Ethereum)
  - Connect to Ethereum node (QuickNode/Alchemy)
  - Monitor large transfers (>$1M)
  - Detect exchange deposits (Binance, Coinbase)
  - Parse transaction data
  - Test with recent transactions

**Deliverables:**
- ✅ Twitter collector streaming live tweets
- ✅ On-chain collector detecting whale moves
- ✅ Both integrated with error handling

---

### Day 7-8: Data Normalization & Queue

**Tasks:**
- [ ] **Day 7:** Data Normalizer
  - Unified event schema (see Architecture doc)
  - Entity extraction (extract crypto mentions: BTC, ETH, etc.)
  - Timestamp normalization (UTC)
  - Content hash generation for deduplication
  - Test with sample data from all 4 collectors

- [ ] **Day 8:** Event Queue Setup
  - Configure RabbitMQ queue
  - Implement publisher (collectors → queue)
  - Implement consumer (queue → processors)
  - Test end-to-end flow
  - Monitor queue depth

**Deliverables:**
- ✅ All collectors publishing to unified queue
- ✅ Events normalized and deduplicated
- ✅ Queue handling 100+ events/minute

---

### Day 9-10: Testing & Validation

**Tasks:**
- [ ] **Day 9:** Integration Testing
  - Test all 4 collectors running simultaneously
  - Verify event deduplication
  - Check queue performance under load
  - Fix any bugs

- [ ] **Day 10:** Monitoring & Documentation
  - Add logging to all collectors
  - Set up basic Prometheus metrics
  - Document API endpoints
  - Write README for setup instructions

**Deliverables:**
- ✅ All collectors running 24/7 without crashes
- ✅ Processing 1,000+ events/hour
- ✅ Basic monitoring dashboard
- ✅ Documentation complete

---

## Sprint 1 Success Criteria

✅ **Functional:**
- 4 data collectors running continuously
- Events normalized and queued
- No data loss for 24-hour test period

✅ **Performance:**
- 1,000+ events/hour processed
- <100ms ingestion latency per event
- <5% error rate

✅ **Quality:**
- Unit tests for normalizer (80% coverage)
- No crashes for 24 hours
- All code documented

---

## Sprint 1 Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Twitter API approval delay | Medium | High | Apply immediately, use mock data while waiting |
| Blockchain node costs | Low | Medium | Use free tier initially (Alchemy) |
| RabbitMQ setup complexity | Low | Low | Use Docker image, follow tutorials |
| Collector crashes | Medium | Medium | Implement retry logic, error handling |

---

# SPRINT 2: Processing Engine (Agent A)
**Duration:** Week 3-4 (10 working days)  
**Focus:** Build Agent A (Noise Filter)

## Goals
1. Implement Agent A filtering logic
2. Score and prioritize events
3. Store processed events in database
4. Basic API for querying events

## Detailed Tasks

### Day 11-12: Agent A Architecture

**Tasks:**
- [ ] **Day 11:** Celery Worker Setup
  - Configure Celery for distributed processing
  - Create worker pool (3 workers)
  - Test task distribution

- [ ] **Day 12:** Multi-Source Verification
  - Implement `multi_source_check()` function
  - Query database for similar events (last 30 min)
  - Score based on source count
  - Test with sample news stories

**Deliverables:**
- ✅ Celery workers processing events
- ✅ Multi-source verification working

---

### Day 13-14: Engagement & Bot Detection

**Tasks:**
- [ ] **Day 13:** Engagement Analysis
  - Implement `engagement_analysis()` for tweets
  - Calculate engagement rate
  - Boost score for verified accounts
  - Test with sample tweets

- [ ] **Day 14:** Bot Detection
  - Implement `bot_detection()` heuristics
  - Detect spam patterns, excessive links, hashtags
  - Test with known bot accounts
  - Fine-tune thresholds

**Deliverables:**
- ✅ Engagement scoring functional
- ✅ Bot detection filtering 80%+ of spam

---

### Day 15-16: Semantic Deduplication

**Tasks:**
- [ ] **Day 15:** Embedding Model Setup
  - Install sentence-transformers
  - Load `all-MiniLM-L6-v2` model
  - Test generating embeddings
  - Store embeddings in database

- [ ] **Day 16:** Similarity Matching
  - Implement `semantic_deduplication()`
  - Calculate cosine similarity
  - Test with duplicate news stories
  - Tune similarity threshold (0.7-0.9)

**Deliverables:**
- ✅ Semantic deduplication working
- ✅ Eliminating 90%+ of duplicate stories

---

### Day 17-18: Scoring & Prioritization

**Tasks:**
- [ ] **Day 17:** Aggregate Scoring
  - Implement `calculate_final_score()`
  - Weighted average of all checks
  - Assign priority (HIGH/MEDIUM/LOW)
  - Test with diverse events

- [ ] **Day 18:** Database Storage
  - Store scored events in `events` table
  - Add indexes for performance
  - Implement cleanup (delete events >7 days)
  - Test database performance

**Deliverables:**
- ✅ All events scored and prioritized
- ✅ Database storing 10,000+ events efficiently

---

### Day 19-20: API & Testing

**Tasks:**
- [ ] **Day 19:** REST API
  - `/api/events` - Get recent events (with filters)
  - `/api/events/:id` - Get single event details
  - `/api/stats` - System statistics
  - Add pagination, filtering by priority

- [ ] **Day 20:** End-to-End Testing
  - Test full pipeline (collector → agent → database)
  - Load test with 10,000 events/hour
  - Fix performance bottlenecks
  - Validate filtering accuracy

**Deliverables:**
- ✅ API endpoints functional
- ✅ System processing 10,000+ events/hour
- ✅ 90%+ spam filtered out

---

## Sprint 2 Success Criteria

✅ **Functional:**
- Agent A processing all events
- 90%+ of spam/noise filtered
- Events stored in database with scores

✅ **Performance:**
- Processing 10,000+ events/hour
- <5 seconds per event (end-to-end)
- <1% event loss

✅ **Quality:**
- Unit tests for all filtering functions
- Manual validation: 80%+ of HIGH priority events are actually important

---

## Sprint 2 Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Embeddings too slow | Medium | Medium | Use lighter model, batch processing |
| False positive filtering | High | High | Tune thresholds, collect user feedback |
| Database performance | Low | Medium | Add indexes, use connection pooling |
| Celery worker crashes | Medium | Medium | Auto-restart, error monitoring |

---

# SPRINT 3: Delivery Layer
**Duration:** Week 5-6 (10 working days)  
**Focus:** Build alert delivery (Telegram, Email, Dashboard)

## Goals
1. Telegram bot with alert delivery
2. Email alert system
3. Basic web dashboard (React)
4. User authentication

## Detailed Tasks

### Day 21-22: Telegram Bot

**Tasks:**
- [ ] **Day 21:** Bot Setup
  - Register bot with BotFather
  - Implement `/start` command (account linking)
  - Implement `/status`, `/alerts` commands
  - Test basic interactions

- [ ] **Day 22:** Alert Delivery
  - Format alerts for Telegram
  - Implement `send_alert()` function
  - Test sending alerts to users
  - Add rate limiting (max 10 alerts/hour)

**Deliverables:**
- ✅ Telegram bot responding to commands
- ✅ Alerts delivered to Telegram

---

### Day 23-24: Email System

**Tasks:**
- [ ] **Day 23:** SendGrid Integration
  - Set up SendGrid account
  - Create email templates (HTML)
  - Implement email sending function
  - Test email delivery

- [ ] **Day 24:** Email Preferences
  - User preferences (email frequency)
  - Daily digest feature
  - Unsubscribe handling
  - Test with multiple users

**Deliverables:**
- ✅ Email alerts sending successfully
- ✅ User preferences working

---

### Day 25-27: Web Dashboard (Frontend)

**Tasks:**
- [ ] **Day 25:** React Setup
  - Create React app (Vite)
  - Set up TailwindCSS
  - Create basic layout (header, sidebar)
  - Implement routing (React Router)

- [ ] **Day 26:** Dashboard Pages
  - Landing page
  - Login/Signup pages
  - Dashboard (alert feed)
  - Alert history page
  - Settings page

- [ ] **Day 27:** Real-Time Updates
  - Implement Socket.io client
  - Connect to backend WebSocket
  - Display alerts in real-time
  - Test with live data

**Deliverables:**
- ✅ Web dashboard accessible
- ✅ Real-time alert feed working
- ✅ Mobile-responsive design

---

### Day 28-29: User Authentication

**Tasks:**
- [ ] **Day 28:** Backend Auth
  - Implement JWT authentication
  - `/api/auth/signup` endpoint
  - `/api/auth/login` endpoint
  - Password hashing (bcrypt)
  - Test authentication flow

- [ ] **Day 29:** Frontend Auth
  - Login/Signup forms
  - JWT storage (localStorage)
  - Protected routes
  - Test user flows

**Deliverables:**
- ✅ Users can sign up and log in
- ✅ Authentication working end-to-end

---

### Day 30: Integration & Testing

**Tasks:**
- [ ] **Day 30:** Full Integration
  - Connect all components
  - Test user journey: signup → link Telegram → receive alert
  - Fix bugs
  - Prepare for beta testing

**Deliverables:**
- ✅ Complete user flow working
- ✅ Ready for beta testing

---

## Sprint 3 Success Criteria

✅ **Functional:**
- Telegram bot delivering alerts
- Email alerts working
- Web dashboard live
- User authentication functional

✅ **User Experience:**
- <2 minutes to complete onboarding
- Real-time updates (<2 second delay)
- Mobile-friendly interface

✅ **Quality:**
- No critical bugs
- Works on Chrome, Safari, Firefox
- Telegram bot 99% uptime

---

## Sprint 3 Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| WebSocket connection issues | Medium | Medium | Fallback to polling, better error handling |
| UI/UX not intuitive | High | High | User testing, iterate quickly |
| Telegram rate limits | Low | Low | Implement queuing, respect limits |
| Email deliverability | Medium | Low | Use reputable provider (SendGrid), SPF/DKIM |

---

# SPRINT 4-6: Integration, Testing & Launch
**Duration:** Week 7-12 (6 weeks)  
**Focus:** Polish, beta testing, launch preparation

## Sprint 4: Beta Testing & Iteration (Week 7-8)

### Goals
1. Launch private beta (50 users)
2. Collect feedback
3. Fix critical bugs
4. Improve alert quality

### Tasks

**Week 7:**
- [ ] Deploy to production environment (Railway/Render)
- [ ] Create beta signup page
- [ ] Recruit 50 beta testers (friends, crypto communities)
- [ ] Monitor system performance 24/7
- [ ] Set up error tracking (Sentry)

**Week 8:**
- [ ] Collect user feedback (surveys, interviews)
- [ ] Analyze alert quality metrics
- [ ] Fix top 10 reported bugs
- [ ] Tune Agent A thresholds based on feedback
- [ ] Improve UI based on user complaints

### Deliverables
- ✅ 50 active beta users
- ✅ 80%+ user satisfaction
- ✅ <3 critical bugs remaining
- ✅ System stable for 7 days

---

## Sprint 5: Features & Polish (Week 9-10)

### Goals
1. Add portfolio tracking
2. Improve dashboard analytics
3. Implement user preferences
4. Add referral system

### Tasks

**Week 9:**
- [ ] **Portfolio Feature:**
  - UI for adding holdings
  - Backend storage
  - Portfolio value tracking
  - Alert relevance based on portfolio

- [ ] **Analytics Dashboard:**
  - Alert history charts
  - User statistics
  - System performance metrics

**Week 10:**
- [ ] **User Preferences:**
  - Alert frequency controls
  - Token watchlist
  - Quiet hours
  - Notification channels

- [ ] **Referral System:**
  - Unique referral links
  - Track signups
  - Rewards (extended free trial)

### Deliverables
- ✅ Portfolio tracking live
- ✅ Advanced preferences working
- ✅ Referral system functional

---

## Sprint 6: Launch Preparation (Week 11-12)

### Goals
1. Expand beta to 500 users
2. Set up payment system (Stripe)
3. Marketing materials
4. Public launch

### Tasks

**Week 11:**
- [ ] **Payment Integration:**
  - Stripe setup
  - Subscription plans (Free, Pro)
  - Billing dashboard
  - Test payment flow

- [ ] **Scalability:**
  - Load test (10,000 users simulation)
  - Optimize database queries
  - Set up auto-scaling
  - Monitor costs

**Week 12:**
- [ ] **Marketing:**
  - Create landing page copy
  - Demo video
  - Social media accounts
  - Product Hunt launch post

- [ ] **Public Launch:**
  - Announce on Twitter, Reddit (r/cryptocurrency)
  - Post on Product Hunt
  - Reach out to crypto influencers
  - Monitor launch metrics

### Deliverables
- ✅ 500+ total users
- ✅ 50+ paying users ($1,450 MRR)
- ✅ Featured on Product Hunt
- ✅ Stable system under real load

---

## Sprint 4-6 Success Criteria

✅ **Users:**
- 500+ registered users
- 50+ paying subscribers
- 30% weekly active rate

✅ **Product:**
- All core features working
- <1% critical bugs
- 99%+ uptime

✅ **Business:**
- $1,500+ MRR
- 70%+ user satisfaction (NPS)
- Featured in 2+ crypto publications

---

# Post-Launch: Month 4-6 (Phase II)

## Goals
1. Implement Agent B (Wallet Attribution)
2. Implement Agent C (Sentiment Analysis)
3. Implement Agent D (Portfolio Personalization)
4. Scale to 1,000+ users
5. Reach $10K MRR

## High-Level Roadmap

### Month 4: Agent B (Wallet Attribution)
- Wallet clustering algorithm
- Entity identification
- Win-rate calculation
- Historical backtesting
- "Whale Resume" feature

### Month 5: Agent C (Sentiment Analysis)
- Fine-tune LLM for crypto sentiment
- Historical event comparison
- Volatility scoring
- "Priced-in" assessment

### Month 6: Agent D (Portfolio Strategist)
- Risk profile engine
- Personalized impact scoring
- Suggested actions (BUY/SELL/HOLD)
- Advanced portfolio analytics

---

# Resource Requirements

## Team

**Minimum (Solo Founder):**
- 1 Full-stack Developer (you)
- Part-time Designer (contract, ~$2K)

**Ideal:**
- 1 Full-stack Developer
- 1 Backend/AI Engineer
- 1 Part-time Designer

## Budget (Monthly)

### Development (First 3 Months)
| Item | Cost |
|------|------|
| Infrastructure (Railway/Render) | $50 |
| API Costs (Twitter, Ethereum, etc.) | $200-500 |
| Tools (Figma, etc.) | $20 |
| Domain & Hosting | $15 |
| **Total** | **$285-585/month** |

### Post-Launch (Month 4+)
| Item | Cost |
|------|------|
| Infrastructure (scaled) | $100-200 |
| API Costs | $500-1000 |
| Marketing | $500 |
| Tools & Services | $100 |
| **Total** | **$1,200-1,800/month** |

**First 3 Months Total: ~$1,000-2,000**  
**Months 4-6 Total: ~$4,000-6,000**

---

# Key Milestones

✅ **Week 2:** Data ingestion working (1,000+ events/hour)  
✅ **Week 4:** Agent A filtering 90%+ of noise  
✅ **Week 6:** MVP complete, first alerts delivered  
✅ **Week 8:** 50 beta users, stable system  
✅ **Week 12:** Public launch, 500 users, $1.5K MRR  
✅ **Month 6:** 1,000+ users, $10K MRR, all agents live

---

# Risk Management

## High-Priority Risks

### Risk 1: Slow User Growth
**Mitigation:**
- Launch referral program early
- Partner with crypto communities
- Content marketing (blog, Twitter)
- Product Hunt launch

### Risk 2: Technical Scalability
**Mitigation:**
- Design for horizontal scaling from day 1
- Monitor performance metrics daily
- Load test before each major milestone
- Budget for infrastructure scaling

### Risk 3: Alert Quality Issues
**Mitigation:**
- Continuous feedback collection
- Weekly tuning of Agent A thresholds
- A/B test different filtering strategies
- Manual review of HIGH priority alerts

### Risk 4: API Cost Overruns
**Mitigation:**
- Monitor API usage daily
- Set spending alerts
- Implement caching aggressively
- Consider cheaper alternatives if needed

---

# Success Metrics (KPIs)

## Product Metrics
- **Event Processing Rate:** >10,000 events/hour
- **Filtering Accuracy:** >85% of HIGH priority alerts are useful
- **System Uptime:** >99.5%
- **Alert Latency:** <10 seconds end-to-end

## User Metrics
- **Total Users:** 500+ by Month 3
- **Weekly Active Users:** 30%+
- **Retention (Week 2):** >50%
- **Avg. Alerts/User/Day:** 3-5

## Business Metrics
- **Free → Paid Conversion:** 10%+
- **Monthly Recurring Revenue:** $1,500+ by Month 3
- **Churn Rate:** <10% monthly
- **Net Promoter Score:** >30

---

# Development Best Practices

## Daily Workflow
1. **Morning:** Review metrics, check error logs
2. **Mid-Day:** Development (4-6 hour focused block)
3. **Evening:** Testing, documentation, git commits
4. **Weekly:** User interviews, roadmap review

## Code Quality
- Write unit tests for critical functions
- Code review (if team) or self-review (if solo)
- Document all APIs and complex logic
- Use linting (Black, ESLint)

## Deployment
- Deploy to staging first
- Test manually before production
- Deploy during low-traffic hours
- Monitor for 1 hour post-deployment
- Have rollback plan ready

---

# Conclusion

## What Makes This Roadmap Achievable?

✅ **Focused Scope:** MVP includes only essential features (Agent A only)  
✅ **Proven Tech Stack:** Using mature, well-documented technologies  
✅ **Iterative Approach:** Ship fast, iterate based on feedback  
✅ **Realistic Timeline:** 12 weeks with buffer for unexpected issues  
✅ **Clear Milestones:** Each sprint has concrete deliverables

## What Could Go Wrong?

❌ **Scope Creep:** Temptation to add features (resist!)  
❌ **Underestimating Complexity:** Agent A tuning may take longer  
❌ **API Issues:** Twitter or blockchain APIs changing/breaking  
❌ **Slow User Adoption:** May need more marketing effort

## Contingency Plans

**If Behind Schedule:**
- Cut non-essential features (email can wait)
- Use more third-party services (less custom code)
- Extend timeline by 2-4 weeks (acceptable for MVP)

**If API Costs Too High:**
- Reduce polling frequency
- Focus on fewer data sources initially
- Implement aggressive caching

**If User Adoption Slow:**
- Offer extended free trials
- Partner with influencers
- Create viral referral incentives

---

# Next Steps

1. **✅ Review this roadmap** - Do the timelines make sense?
2. **✅ Approve budget** - Can you commit $1-2K for first 3 months?
3. **✅ Clear your calendar** - Block 6-8 hours/day for development
4. **✅ Get API keys** - Start Twitter, Ethereum applications now
5. **🚀 Start Sprint 1** - Day 1 is project setup!

---
