# AETERNA: Quick Start Guide


## 📊 What We've Created for You

You now have **4 comprehensive planning documents** in `/app/memory/`:

1. **PRD.md** - Product Requirements Document
   - What you're building and why
   - User personas and journeys
   - Feature specifications
   - Success metrics

2. **ARCHITECTURE.md** - Technical Architecture
   - System design (3 layers)
   - Technology stack decisions
   - Database schema
   - API specifications
   - Cost breakdown

3. **ROADMAP.md** - Development Roadmap
   - 6 sprints over 12 weeks
   - Day-by-day tasks
   - Milestones and deliverables
   - Resource requirements

4. **RISK_ASSESSMENT.md** - Risk Analysis & Decisions
   - What can go wrong
   - Critical tradeoffs
   - Budget projections
   - Go/No-Go framework

---

## 🎯 What Changed from Your Original Document?

### Your Vision (From PDF)
- **Timeline:** 18 months (Phase I-III)
- **Agents:** 4 AI agents (Sieve, Profiler, Quant, Strategist)
- **Data:** Multi-chain (Ethereum, Solana, L2s)
- **Delivery:** WhatsApp, Telegram, Discord, SMS, Email, Dashboard
- **Monetization:** B2C ($0-99/mo) + B2B ($500-10K/mo) + White Label

### Our 2-3 Month MVP Recommendation
- **Timeline:** 12 weeks (Phase I only)
- **Agents:** 1 AI agent (Sieve/Agent A only)
- **Data:** Single-chain (Ethereum only) + News + Twitter + Prices
- **Delivery:** Telegram + Email + Dashboard (3 channels)
- **Monetization:** Free beta → Pro tier ($29/mo) in Month 3

### Why These Changes?
- ✅ **Realistic:** 1-2 developers can build this in 12 weeks
- ✅ **Focused:** One core value prop (intelligent filtering)
- ✅ **Testable:** Can validate with real users quickly
- ✅ **Fundable:** Cheaper to build ($2-7K vs. $50K+)
- ✅ **Expandable:** Can add Agents B, C, D in Months 4-6

**Everything else is Phase II (Months 4-6) or Phase III (Months 7-12)**

---

## ✅ MVP Feature List (What You're Building)

### Core Features (Must Have)

1. **Multi-Source Data Ingestion**
   - News feeds (CoinDesk, CoinTelegraph, Decrypt)
   - Twitter/X (crypto-related tweets)
   - Ethereum on-chain (large transfers >$1M)
   - Price data (CoinGecko, top 100 cryptos)

2. **Agent A: Intelligent Filtering**
   - Multi-source verification
   - Engagement analysis (Twitter metrics)
   - Bot detection
   - Semantic deduplication
   - Priority scoring (HIGH/MEDIUM/LOW)

3. **Alert Delivery**
   - Telegram bot (primary channel)
   - Email alerts (secondary)
   - Web dashboard (real-time feed)

4. **User Management**
   - Sign up / Login (email + password)
   - Link Telegram account
   - Set alert preferences
   - View alert history

5. **Web Dashboard**
   - Live event feed
   - Alert history
   - Basic analytics
   - Settings page

### Phase II Features (Months 4-6)
- Agent B: Wallet attribution ("This wallet has 85% win-rate")
- Agent C: Sentiment analysis ("Market impact: HIGH")
- Agent D: Portfolio personalization ("This affects 30% of your holdings")
- Multi-chain support (Solana, BSC, L2s)
- Mobile apps (iOS, Android)

---

## 💰 Budget Overview

### Minimum Budget (Optimistic)
**Total: $1,200 for 3 months**

- Infrastructure: $200/month × 3 = $600
- API costs: $100/month × 3 = $300
- Tools: $50/month × 3 = $150
- Domain: $15/year = $15
- Design: DIY = $0
- Marketing: Word of mouth = $0
- Buffer (15%): $175

**Best if:** Solo developer, using free tiers, DIY design

### Realistic Budget (Recommended)
**Total: $7,000 for 3 months**

- Infrastructure: $400/month × 3 = $1,200
- API costs: $300/month × 3 = $900
- Tools: $100/month × 3 = $300
- Domain + SSL: $50
- Design (contractor): $1,500 (one-time)
- Marketing: $200/month × 3 = $600
- Error tracking (Sentry): $0 (free tier)
- Monitoring: $0 (Grafana free)
- Legal (ToS, Privacy): $500
- Buffer (15%): $750
- Unexpected costs: $1,200

**Best if:** Solo developer with some savings, want professional look

### Premium Budget (If Hiring Help)
**Total: $20,000 for 3 months**

- Everything above: $7,000
- Part-time contractor: $8,000 (20 hrs/week × 12 weeks × $30/hr)
- UI/UX designer: $2,500
- Professional branding: $1,000
- Marketing: $1,500

**Best if:** You have funding or full-time job, hiring help

---

## ⏱️ Time Commitment

### Solo Developer
- **Hours/week:** 40-50 hours
- **Total hours:** 480-600 hours over 12 weeks
- **Breakdown:**
  - Development: 60% (300-360 hrs)
  - Testing/debugging: 20% (100-120 hrs)
  - Deployment/DevOps: 10% (50-60 hrs)
  - Documentation: 5% (25-30 hrs)
  - Meetings/admin: 5% (25-30 hrs)

### With Co-Founder (2 developers)
- **Hours/week (each):** 30-40 hours
- **Total combined:** 720-960 hours over 12 weeks
- **Timeline:** Can finish in 8-10 weeks instead of 12

---

## 🛠️ Technology Stack

### Backend
- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **Task Queue:** Celery + RabbitMQ
- **Database:** PostgreSQL 15
- **Cache:** Redis
- **Embeddings:** sentence-transformers (local)
- **Deployment:** Docker + Railway/Render

### Frontend
- **Framework:** React 18 (Vite)
- **Styling:** TailwindCSS
- **Real-time:** Socket.io
- **State:** React Context API (or Zustand)
- **Deployment:** Vercel (free)

### Infrastructure
- **Hosting:** Railway or Render
- **Database:** Managed PostgreSQL (Railway/Render)
- **Cache:** Managed Redis (Railway/Render)
- **Message Queue:** CloudAMQP (managed RabbitMQ)
- **Monitoring:** Sentry (errors) + Prometheus (metrics)

### APIs & Services
- **Twitter:** Twitter API v2 ($100-500/month)
- **Blockchain:** QuickNode/Alchemy ($50-200/month)
- **Prices:** CoinGecko (free tier)
- **Email:** SendGrid ($0-15/month)
- **Telegram:** Telegram Bot API (free)

**Why these choices?** Fast development, affordable, scalable, well-documented

---

## 🚦 Critical Path (Must-Do Before Starting)

### Week 0 (This Week!) - Validation & Setup

**Day 1-2: Validation**
- [ ] Talk to 10-20 crypto traders (friends, Twitter, Discord)
  - Would they pay $29/month?
  - What alerts do they want?
  - What do they use now?
- [ ] Join 5 crypto Discord/Telegram communities
  - Observe what info they share
  - Note common pain points
- [ ] Sign up for competitors (Nansen free trial, Arkham, etc.)
  - What do they do well?
  - What do users complain about?

**Day 3-4: Legal & Admin**
- [ ] Register business (LLC or sole proprietorship)
- [ ] Open business bank account
- [ ] Get Stripe account (for future payments)
- [ ] Purchase domain name (aeterna.ai or similar)

**Day 5-7: API Keys & Accounts**
- [ ] Apply for Twitter Developer account 🚨 DO THIS FIRST! (can take 1-4 weeks)
- [ ] Sign up for QuickNode or Alchemy (Ethereum node)
- [ ] Create Telegram bot via BotFather
- [ ] Sign up for SendGrid (email)
- [ ] Sign up for CoinGecko (price data)
- [ ] Set up GitHub repository
- [ ] Sign up for Railway or Render

**Day 8-10: Landing Page**
- [ ] Create simple landing page (1 page)
  - Value proposition
  - Email signup form
  - Screenshots/mockups (can be fake)
- [ ] Deploy to Vercel
- [ ] Share on Twitter, Reddit (r/cryptocurrency)
- [ ] Goal: 100 email signups
- [ ] If you can't get 100, reconsider or pivot

---

## 📋 Development Checklist

### Sprint 1 (Week 1-2): Foundation
- [ ] Set up Docker environment (PostgreSQL, Redis, RabbitMQ)
- [ ] Create database schema
- [ ] Build news collector (RSS feeds)
- [ ] Build price collector (CoinGecko)
- [ ] Build Twitter collector (if API approved)
- [ ] Build on-chain collector (Ethereum)
- [ ] Implement data normalizer
- [ ] Set up event queue (RabbitMQ)
- [ ] Test: 1,000+ events/hour processed

### Sprint 2 (Week 3-4): Processing
- [ ] Set up Celery workers
- [ ] Implement Agent A filtering logic
  - [ ] Multi-source verification
  - [ ] Engagement analysis
  - [ ] Bot detection
  - [ ] Semantic deduplication
  - [ ] Scoring algorithm
- [ ] Store events in database
- [ ] Create REST API (/api/events, etc.)
- [ ] Test: 90%+ spam filtered

### Sprint 3 (Week 5-6): Delivery
- [ ] Build Telegram bot
  - [ ] /start, /status, /alerts commands
  - [ ] Alert delivery
  - [ ] Rate limiting
- [ ] Implement email alerts (SendGrid)
- [ ] Build web dashboard (React)
  - [ ] Landing page
  - [ ] Login/Signup
  - [ ] Alert feed (real-time)
  - [ ] Settings
- [ ] Implement user authentication (JWT)
- [ ] Test end-to-end user flow

### Sprint 4 (Week 7-8): Beta Testing
- [ ] Deploy to production (Railway/Render)
- [ ] Invite 50 beta users
- [ ] Monitor system 24/7
- [ ] Collect user feedback
- [ ] Fix critical bugs
- [ ] Tune Agent A thresholds

### Sprint 5 (Week 9-10): Features & Polish
- [ ] Add portfolio tracking (if time)
- [ ] Improve dashboard (analytics)
- [ ] Add referral system
- [ ] Write documentation
- [ ] Create demo video

### Sprint 6 (Week 11-12): Launch
- [ ] Expand beta to 500 users
- [ ] Set up Stripe payments (Pro tier)
- [ ] Load test system
- [ ] Launch on Product Hunt
- [ ] Launch on Twitter, Reddit
- [ ] Goal: 500 users, 50 paid

---

## 📈 Success Metrics

### Week 2 (End of Sprint 1)
- ✅ All 4 data collectors running 24/7
- ✅ Processing 1,000+ events/hour
- ✅ <5% error rate
- ✅ <100ms ingestion latency

### Week 4 (End of Sprint 2)
- ✅ Agent A filtering 90%+ of spam
- ✅ Processing 10,000+ events/hour
- ✅ Events stored in database with scores
- ✅ API endpoints functional

### Week 6 (End of Sprint 3)
- ✅ Telegram bot delivering alerts
- ✅ Web dashboard live
- ✅ <10 seconds latency (event → alert)
- ✅ Complete user flow working

### Week 8 (End of Sprint 4)
- ✅ 50 active beta users
- ✅ System stable for 7+ days
- ✅ 80%+ user satisfaction
- ✅ <3 critical bugs

### Week 12 (Public Launch)
- ✅ 500 registered users
- ✅ 50 paying users ($1,450 MRR)
- ✅ 30% weekly active rate
- ✅ Featured on Product Hunt
- ✅ 99%+ uptime

---

## ⚠️ Red Flags to Watch For

### During Development
- 🚩 **Week 2:** Can't get 1,000 events/hour → Simplify collectors
- 🚩 **Week 4:** Agent A not filtering well → Spend extra week tuning
- 🚩 **Week 6:** MVP not working end-to-end → Cut features
- 🚩 **Week 8:** <20 beta users → Improve onboarding/marketing
- 🚩 **Week 10:** Users say "not useful" → Fix alert quality

### After Launch
- 🚩 **<100 signups in Week 1** → Marketing problem
- 🚩 **>50% churn in Week 2** → Product problem
- 🚩 **<10% free→paid conversion** → Value prop problem
- 🚩 **Users complaining about spam** → Filtering problem
- 🚩 **Costs >$1,000/month** → Efficiency problem

**Rule:** If you see 2+ red flags, pause and fix before continuing.

---

## 🚀 Day 1 Action Items

Ready to start? Here's what to do **TODAY**:

### Morning (3 hours)
1. [ ] Read all 4 planning documents fully
2. [ ] Make a list of questions/concerns
3. [ ] Decide: Are you committed to 40+ hours/week for 12 weeks?
4. [ ] If yes, continue. If no, adjust timeline or get co-founder.

### Afternoon (4 hours)
5. [ ] Apply for Twitter Developer account (🚨 CRITICAL - do first!)
6. [ ] Create GitHub repository
7. [ ] Purchase domain name
8. [ ] Sign up for Railway or Render
9. [ ] Set up project structure (folders)

### Evening (2 hours)
10. [ ] Write Docker Compose file
11. [ ] Test: Can you run PostgreSQL, Redis, RabbitMQ locally?
12. [ ] Create README.md with setup instructions
13. [ ] Commit to GitHub

### Before Bed
14. [ ] Post on Twitter: "Building AETERNA, a crypto intelligence platform. Day 1! 🚀"
15. [ ] Schedule coffee chats with 5 crypto traders (for validation)

**Tomorrow:** Start building news collector (see Roadmap Day 3)

---

## 💬 Common Questions

### Q: Should I build AETERNA?
**A:** Only if you answered "yes" to:
- Do you have 3-6 months of runway?
- Can you commit 40+ hours/week?
- Do you have technical skills (or budget to hire)?
- Have you validated demand (talked to 20+ users)?

If 3+ are "no," reconsider.

### Q: Can I build this solo?
**A:** Yes, but it will take 12-14 weeks (not 8). Cut email alerts and portfolio tracking to save time.

### Q: Do I need ML/AI experience?
**A:** Not for MVP. Agent A uses rule-based filtering + sentence-transformers (easy). You'll need ML for Phase II (Agents B, C, D).

### Q: What if I can't get Twitter API approved?
**A:** Plan B: Start with News + On-chain + Prices (3 sources). Add Twitter later. Still valuable!

### Q: How much should I charge?
**A:** Free for beta (Month 1-2), $29/month for Pro tier (Month 3+). Don't go cheaper—users who won't pay $29 won't pay $19 either.

### Q: Should I pivot if nobody signs up?
**A:** If <100 email signups on landing page after 2 weeks of marketing, YES, reconsider. Talk to more users, understand why.

### Q: When should I raise funding?
**A:** After reaching $5-10K MRR (Month 6-9). Bootstrapping forces you to focus on revenue and real users.

---

## 🔗 Helpful Resources

### Technical Tutorials
- **FastAPI:** https://fastapi.tiangolo.com/tutorial/
- **React + Vite:** https://vitejs.dev/guide/
- **TailwindCSS:** https://tailwindcss.com/docs
- **Telegram Bot:** https://core.telegram.org/bots/tutorial
- **Web3.py (Ethereum):** https://web3py.readthedocs.io/
- **Celery:** https://docs.celeryq.dev/

### Design Resources
- **Figma (UI design):** https://www.figma.com/
- **TailwindUI (components):** https://tailwindui.com/ ($)
- **Heroicons:** https://heroicons.com/ (free icons)
- **Unsplash:** https://unsplash.com/ (free images)

### Marketing Resources
- **Product Hunt:** https://www.producthunt.com/
- **Reddit:** r/cryptocurrency, r/CryptoTechnology
- **Twitter:** #crypto, #bitcoin, #ethereum
- **Crypto Discord/Telegram:** Find via https://discord.me/

---

## 👋 Final Words

Your AETERNA concept is **solid**. The problem (information overload) is **real**. The market (crypto traders) is **large and growing**.

But success requires:
1. **Focus** - Build ONE thing well (Agent A), not four things poorly
2. **Speed** - Launch in 12 weeks, not 12 months
3. **Iteration** - Improve based on user feedback, not assumptions
4. **Persistence** - Most startups fail because founders quit, not because the idea was bad

The difference between a $10M business and a failed side project is often just **execution discipline**.

**You have the roadmap. You have the architecture. You have the plan.**

**Now go build it! 🚀**

---

## 📧 Questions?

If you have questions or need clarification on any part of these documents:

1. Re-read the relevant section (90% of questions are answered)
2. Google the specific technical question
3. Ask in relevant communities (Reddit, Discord, Stack Overflow)
4. Break the problem into smaller pieces

**Remember:** Building is learning. You'll figure things out as you go.

**Good luck! You've got this! 💪**
