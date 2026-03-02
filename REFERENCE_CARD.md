# ⚡ AETERNA - Quick Reference Card

## 🎯 What You Have

✅ Local development setup working  
✅ Docker Compose running all services  
✅ Database migrations working  
✅ Tests & linting configured  
✅ GitHub Actions CI/CD pipeline  
✅ Docker image ready for deployment

---

## 🚀 FASTEST PATH TO LIVE

```
Step 1: https://railway.app (sign up, 5 min)
Step 2: Add PostgreSQL, Redis, RabbitMQ (10 min)
Step 3: Deploy from GitHub (auto, 10 min)
Step 4: Run migrations in shell (2 min)
Result: 🎉 LIVE in 30 min
Cost: FREE this month ($10-20 next month)
```

---

## 💻 Essential Commands

```bash
# START YOUR APP
make dev                    # Start everything locally

# TESTING
make test                   # Run all tests
make quality                # Code quality checks
make test-coverage          # Tests with coverage report

# DATABASE
make migrate                # Run migrations
make db-shell               # Access PostgreSQL
make db-dump                # Backup database
make migrate-create MSG="x" # Create new migration

# VIEWING
make logs                   # View all logs
make health                 # Check if running
make stats                  # CPU/Memory/Network

# MAINTENANCE
make down                   # Stop all services
make restart                # Restart everything
make reset                  # Fresh start (⚠️ deletes data!)
make clean-volumes          # Delete all Docker volumes
make help                   # Show all commands
```

---

## 📁 Key Files Explained

| File                          | Purpose                    |
| ----------------------------- | -------------------------- |
| `Dockerfile`                  | Production Docker image    |
| `docker-compose.yml`          | Local development services |
| `.env.example`                | Configuration template     |
| `.github/workflows/ci-cd.yml` | GitHub Actions CI/CD       |
| `render.yml`                  | Render.com deployment      |
| `Makefile`                    | Shortcut commands          |

---

## 🌐 Access Services

```
API:            http://localhost:8000
API Docs:       http://localhost:8000/docs
RabbitMQ:       http://localhost:15672 (guest/guest)
PostgreSQL:     localhost:5432
Redis:          localhost:6379
```

---

## 📚 Documentation Files

| File                              | When to Read              |
| --------------------------------- | ------------------------- |
| `QUICK_START.md`                  | 5 min overview (TOP FILE) |
| `ACTION_PLAN.md`                  | What to do next NOW       |
| `docs/GETTING_STARTED.md`         | Detailed setup guide      |
| `docs/FREE_DEPLOYMENT_OPTIONS.md` | Platform comparison       |
| `docs/VISUAL_GUIDE.md`            | Diagrams & flowcharts     |
| `docs/DEPLOYMENT_GUIDE.md`        | Advanced deployment       |
| `docs/DEPLOYMENT_CHECKLIST.md`    | Pre-deploy checklist      |
| `docs/DEPLOYMENT_FILES_GUIDE.md`  | File explanations         |

---

## 🚀 Deployment Platforms Comparison

| Platform       | Price       | Setup Time | Best For             |
| -------------- | ----------- | ---------- | -------------------- |
| **Railway** ⭐ | $10-20/mo   | 30 min     | Easiest, recommended |
| **Fly.io**     | $20-40/mo   | 45 min     | Best performance     |
| **Vultr VPS**  | $2.50-12/mo | 2 hours    | Cheapest long-term   |
| **Local**      | FREE        | 10 min     | Development          |

**RECOMMENDATION**: Start with Railway.app → Go to: https://railway.app

---

## ⚙️ Environment Variables

### Required for Production

```
SECRET_KEY=your-random-secret-key
ENVIRONMENT=production
DEBUG=false
```

### Auto-Configured by Platforms

```
DATABASE_URL      (PostgreSQL)
REDIS_URL         (Redis)
RABBITMQ_URL      (RabbitMQ)
```

### Generate Secret Key

```python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🔄 GitHub Integration

```bash
# Local → GitHub → CI/CD → Docker Registry → Deploy

# Push code
git add .
git commit -m "message"
git push origin main

# Automatic:
# 1. GitHub Actions runs
# 2. Tests run
# 3. Image built
# 4. Image pushed to ghcr.io
# 5. Check: GitHub → Actions tab
```

---

## 🎯 Daily Workflow

### Morning

```bash
make dev     # Start development
make logs    # Check for issues
```

### During Day

```bash
# Code → Auto-reload works
make test                # Before committing
make quality             # Check code quality
```

### Evening

```bash
git push origin main     # GitHub Actions auto-builds
make down                # Stop services
```

---

## 🆘 Troubleshooting

| Issue               | Solution                  |
| ------------------- | ------------------------- |
| Port already in use | `make down` first         |
| Docker not running  | Start Docker Desktop      |
| Tests fail          | `make logs` to see errors |
| Can't connect to DB | `make restart`            |
| App won't start     | Check `.env` file         |
| Forgot command      | `make help`               |

---

## 📞 Support Resources

- 📖 See [GETTING_STARTED.md](./docs/GETTING_STARTED.md) - Detailed guide
- 🎫 GitHub Issues in your repo
- 🔍 Search: "deployment error" in docs/
- 🌐 Platform docs (Railway/Fly/etc)

---

## ✅ Pre-Deployment Checklist

```bash
make quality          # ✓ All checks pass?
make test             # ✓ All tests pass?
docker build .        # ✓ Builds successfully?
make db-dump          # ✓ Database backed up?
```

---

## 🎓 Next Steps (Pick One)

### Option 1: Deploy Now (Recommended)

→ Go to [ACTION_PLAN.md](./ACTION_PLAN.md)
→ Follow "Railway.app Path" section
→ 30 minutes to live app

### Option 2: Learn More First

→ Read [GETTING_STARTED.md](./docs/GETTING_STARTED.md)
→ Understand all options
→ Then deploy when ready

### Option 3: Stay Local

→ Use `make dev` daily
→ Deploy later when needed
→ No cost, but limited to when computer is on

---

## 💰 Cost Breakdown

| Service   | Railway    | Fly.io     | Vultr       |
| --------- | ---------- | ---------- | ----------- |
| App       | $5-10      | $5-15      | $2.50       |
| Database  | $1-5       | $5-10      | included    |
| Cache     | $0-1       | $1-5       | included    |
| Queue     | $2-5       | $0-5       | included    |
| **Total** | **$10-20** | **$20-40** | **$2.50-5** |

**First Month**: FREE on Railway/Fly (credits)  
**Ongoing**: Railway recommended for ease

---

## 🔗 Important Links

| Link                       | Purpose                   |
| -------------------------- | ------------------------- |
| https://railway.app        | Deploy here (recommended) |
| https://fly.io             | Alternative platform      |
| https://www.vultr.com      | Cheap VPS option          |
| http://localhost:8000/docs | Your API docs (local)     |
| GitHub repo → Actions      | View CI/CD status         |

---

## 📊 Architecture Quick View

```
Your Code
   ↓
Docker Compose (Local) / Platform (Cloud)
   ├─ FastAPI App
   ├─ PostgreSQL
   ├─ Redis
   ├─ RabbitMQ
   ├─ Celery Worker
   └─ Celery Beat
```

---

## 🎬 RIGHT NOW

### Pick one:

**Go live today?** → [ACTION_PLAN.md](./ACTION_PLAN.md)  
**Learn first?** → [GETTING_STARTED.md](./docs/GETTING_STARTED.md)  
**Local only?** → `make dev`  
**Need help?** → Check relevant doc above

---

## 📝 Notes Template

```
Date: ___________
Platform chosen: ___________
Deployment URL: ___________
Issues encountered: ___________
Resolution: ___________
```

---

**Save this file for quick reference!** ⭐
