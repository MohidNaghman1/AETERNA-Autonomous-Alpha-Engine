# AETERNA - Quick Reference Guide

## 🎬 START HERE - 5 Minute Overview

### You Have 3 Options:

#### Option 1️⃣: Local Development (FREE)

```bash
# Already setup! Just run:
make dev

# Access:
http://localhost:8000/docs
```

#### Option 2️⃣: Deploy to Railway (Recommended)

```
Sign up → Add Services → Push code → Done!
Free $5-10 credit, then ~$10/month
```

#### Option 3️⃣: Deploy to VPS (Cheapest)

```
Buy VPS ($2.50-5/mo) → Clone repo → docker-compose up
Most control, but manual setup
```

---

## 📋 Command Cheat Sheet

### Daily Development

```bash
make dev              # Start everything
make logs             # View logs
make test             # Run tests
make quality          # Check code quality
make down             # Stop everything
```

### Database

```bash
make migrate          # Run migrations
make db-shell         # PostgreSQL shell
make db-dump          # Backup database
make migrate-create MSG="add users table"  # New migration
```

### Troubleshooting

```bash
make health           # Check if services running
make restart          # Restart all services
docker-compose ps     # See running containers
docker-compose logs   # View all logs
```

---

## 🚀 Deployment Path - Step by Step

### Phase 1: LOCAL TESTING (You Are Here ✅)

```bash
# 1. Start local environment
bash scripts/dev_start.sh        # Linux/macOS
# or
powershell -ExecutionPolicy Bypass -File scripts/dev_start.ps1  # Windows

# 2. Test it works
make health                     # All green? ✓

# 3. Run tests
make test-coverage              # All pass? ✓

# 4. Backup your database
make db-dump                    # Saved to backups/
```

### Phase 2: PUSH TO GITHUB

```bash
# 1. Ensure code is clean
git add .
git commit -m "Ready for deployment"
git push origin main

# 2. GitHub Actions runs automatically:
#    ✓ Lints code
#    ✓ Runs tests
#    ✓ Builds Docker image
#    ✓ Pushes to registry
#    Check: GitHub → Actions tab

# 3. Image now available at:
#    ghcr.io/YOUR-USERNAME/aeterna:main
```

### Phase 3: CHOOSE DEPLOYMENT PLATFORM

#### 🎯 Railway.app (Easiest - Recommended)

**Timeline: 30 minutes**

```
1. Go to: https://railway.app
2. Click "Start New Project"
3. Choose "GitHub Repo" → Select AETERNA
4. Add Services:
   - PostgreSQL (add from Railway)
   - Redis (add from Railway)
   - RabbitMQ (add from Railway)
5. Click Deploy
6. Railway reads your Dockerfile
7. Services connect automatically
8. Done! Public URL provided
```

**Cost:**

- First month: FREE ($5-10 credit)
- After: ~$10-15/month

**Access:**

```
https://your-app-name.up.railway.app
https://your-app-name.up.railway.app/docs
```

---

#### 🚀 Fly.io (Best Performance)

**Timeline: 45 minutes**

```
1. Install: brew install flyctl
2. Login: flyctl auth login
3. Create: flyctl launch
4. Choose region (near you)
5. Deploy: flyctl deploy
6. Run migrations:
   flyctl ssh console
   alembic upgrade head
   exit
7. Done!
```

**Cost:**

- First month: FREE ($5 credit)
- After: ~$20-30/month

**Access:**

```
https://your-app-name.fly.dev
```

---

#### 💻 Self-Hosted VPS (Full Control)

**Timeline: 1-2 hours**

```
1. Buy VPS:
   https://www.vultr.com ($2.50/mo)
   or DigitalOcean ($5/mo)

2. Choose: Ubuntu 22.04 LTS, smallest size

3. SSH into server:
   ssh root@YOUR_SERVER_IP

4. Install Docker:
   curl -fsSL https://get.docker.com | sh

5. Clone & start:
   git clone https://github.com/YOU/AETERNA.git
   cd AETERNA
   cp .env.example .env
   # Edit .env
   docker-compose up -d
   docker-compose exec app alembic upgrade head

6. done!
```

**Cost:**

- Vultr: $2.50-5/month (cheapest!)
- DigitalOcean: $5-12/month (most reliable)
- Total: Lowest long-term cost

**Access via:**

- Direct IP: http://YOUR_SERVER_IP:8000
- Custom domain: Point DNS to IP + use nginx

---

### Phase 4: VERIFY DEPLOYMENT

```bash
# 1. Check app is running:
curl https://your-app-name.up.railway.app/health

# 2. View logs:
# Railway: Dashboard → Logs tab
# Fly.io: flyctl logs
# VPS: docker-compose logs app

# 3. Run tests against deployed app (optional):
pytest tests/ -v

# 4. You're live! 🎉
```

---

## 🔑 Environment Variables

### Required (Must Set in Platform Dashboard)

```
SECRET_KEY=                # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
ENVIRONMENT=production     # Set to this
DEBUG=false                # Set to this
```

### Auto-Configured by Platform

```
DATABASE_URL               # Platform connects PostgreSQL
REDIS_URL                  # Platform connects Redis
RABBITMQ_URL              # Platform connects RabbitMQ
```

### Optional (If Using)

```
TELEGRAM_BOT_TOKEN=       # For Telegram integration
SMTP_PASSWORD=            # For email sending
SENTRY_DSN=               # For error tracking
```

---

## 🛠️ Common Tasks

### Scale to More Traffic

**Railway:**

```
1. Dashboard → app service
2. Click "Settings"
3. Increase "Memory" & "CPU"
4. Save
```

**Fly.io:**

```bash
flyctl scale vm=performance-2x
flyctl scale count=3  # 3 instances
```

**VPS:**

- Upgrade to larger VPS
- Add Load Balancer (advanced)

### Monitor Your App

**Railway:**

- Built-in dashboard
- Logs tab
- Real-time metrics

**Fly.io:**

```
flyctl dashboard
flyctl status
flyctl logs --follow
```

**VPS:**

```bash
docker stats
docker-compose logs -f app
```

### Update Code

**All Platforms:**

```bash
# 1. Make changes locally
# 2. Test: make quality && make test
# 3. Commit: git add . && git commit -m "..."
# 4. Push: git push origin main
# 5. Platform auto-redeploys!
#    Watch logs while deploying
```

### Backup Database

**Railway:**

```
Dashboard → PostgreSQL → Backups → Auto-backup turned on
```

**VPS:**

```bash
docker-compose exec postgres pg_dump -U postgres aeterna_db > backup_$(date +%Y%m%d).sql
```

### Access Database Directly

**Railway:**

```
Dashboard → PostgreSQL → Connection info
Use in your favorite DB client
```

**Fly.io:**

```bash
flyctl proxy 5432 -a aeterna-postgres
# Then connect to localhost:5432
```

**VPS:**

```bash
docker-compose exec postgres psql -U postgres -d aeterna_db
```

---

## ⚠️ Important - DON'T Forget

✅ **Before Deploying:**

- [ ] Code passes: `make quality`
- [ ] Tests pass: `make test`
- [ ] Migrations ready: Database schema finalized
- [ ] `.env` NOT committed to git
- [ ] `SECRET_KEY` is random & strong

✅ **After Deploying:**

- [ ] Run migrations: `alembic upgrade head`
- [ ] Test main endpoints
- [ ] Check logs for errors
- [ ] Configure automatic backups
- [ ] Set up error notifications

---

## 📊 FINAL DECISION

| Criteria     | Local      | Railway    | Fly.io     | VPS    |
| ------------ | ---------- | ---------- | ---------- | ------ |
| Price        | Free       | $10-20     | $20-40     | $2-12  |
| Setup time   | 10 min     | 30 min     | 45 min     | 2 hrs  |
| Ease         | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐   | ⭐⭐⭐ |
| Performance  | Good       | Excellent  | Excellent  | Good   |
| Scalability  | None       | Easy       | Easy       | Manual |
| **Best for** | Dev/Test   | Production | Production | Budget |

**👉 RECOMMENDED FOR YOU: Railway.app**

- Most user-friendly
- Nearly free with credit
- Production-ready
- Easy to scale later
- GitHub auto-sync

---

## 🎓 Next Steps Today

1. ✅ **Local dev working** (Already done!)

2. 🎯 **Pick platform**
   - Easiest → Railway.app
   - Best perf → Fly.io
   - Cheapest → VPS

3. 📝 **Follow platform guide** (See appropriate section above)

4. ✈️ **Deploy** (30 min - 2 hours depending on choice)

5. 🧪 **Test live app**
   - Visit `/docs` endpoint
   - Test main features
   - Check logs for errors

6. 🎉 **You're deployed!**

---

## 🆘 Help & Resources

### Common Issues

**"Docker not running"**
→ Start Docker Desktop (Windows/Mac) or `sudo systemctl start docker` (Linux)

**"Ports already in use"**
→ `make down` first, then restart

**"Tests fail after deploy"**
→ Check logs, usually missing env var
→ Platform dashboard → Settings → Variables

**"Database migrations didn't run"**
→ Manual run: `flyctl ssh console` then `alembic upgrade head`

**"App not accessible"**
→ Wait 2-3 minutes for deploy
→ Check logs for build errors
→ Verify environment variables set

### Documentation

- [GETTING_STARTED.md](./GETTING_STARTED.md) - Detailed guide
- [FREE_DEPLOYMENT_OPTIONS.md](./FREE_DEPLOYMENT_OPTIONS.md) - Platform comparison
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Advanced topics
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) - Pre-deploy verification

### Useful Links

- Railway: https://railway.app (sign up with GitHub)
- Fly.io: https://fly.io
- FastAPI Docs: https://fastapi.tiangolo.com
- Docker Docs: https://docs.docker.com

---

**🚀 You're ready to deploy! Pick Railway.app and follow the steps above. Estimated time: 30 minutes to live app.**
