# AETERNA - Complete Deployment Setup Guide

## 🎯 Table of Contents

1. [Quick Start - Local Development](#quick-start---local-development)
2. [Using Makefile Commands](#using-makefile-commands)
3. [Free Deployment Alternatives](#free-deployment-alternatives)
4. [Step-by-Step Local Deployment](#step-by-step-local-deployment)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start - Local Development

### Prerequisites

- Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- Git installed
- 8GB+ RAM recommended
- Port 8000, 5432, 6379, 5672 available

### Option 1: Automatic Setup (Recommended)

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev_start.ps1
```

**Linux/macOS (Bash):**

```bash
bash scripts/dev_start.sh
```

✅ This automatically:

- Creates `.env` from template
- Builds Docker images
- Starts all services
- Runs database migrations
- Shows useful links

### Option 2: Manual Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd AETERNA-Autonomous-Alpha-Engine

# 2. Copy environment template
cp .env.example .env

# 3. Start all services
docker-compose up -d

# 4. Wait 10 seconds for services to initialize
sleep 10

# 5. Run database migrations
docker-compose exec app alembic upgrade head

# 6. Verify everything is running
docker-compose logs
```

Done! Access the app:

- 🌐 **API**: http://localhost:8000
- 📚 **Docs**: http://localhost:8000/docs
- 🔄 **ReDoc**: http://localhost:8000/redoc
- 🐰 **RabbitMQ**: http://localhost:15672 (guest/guest)

---

## Using Makefile Commands

After starting with the scripts, use these commands:

### Development Commands

```bash
# View all available commands
make help

# Start development environment
make dev

# View live logs
make logs

# Stop all services
make down

# Full restart
make restart
```

### Testing

```bash
# Run all tests
make test

# Run tests with coverage report
make test-coverage

# Quick test (no coverage)
make test-fast

# Run specific test
docker-compose exec app pytest tests/test_auth.py -v
```

### Code Quality

```bash
# Format code with Black
make format

# Check formatting
make format-check

# Run all linters
make lint

# Type checking with mypy
make typecheck

# Run ALL quality checks
make quality
```

### Database Management

```bash
# Run pending migrations
make migrate

# Rollback last migration
make migrate-down

# Create new migration
make migrate-create MSG="add user table"

# Access PostgreSQL shell
make db-shell

# Backup database
make db-dump

# View current migration version
make migrate-current
```

### Maintenance

```bash
# Check service health
make health

# View container resource usage
make stats

# Clean up everything (WARNING: deletes data!)
make clean-volumes

# Reset to fresh start
make reset

# Access app shell
make shell
```

---

## Free Deployment Alternatives

### 🥇 Best Option: Railway.app (Free Tier Available)

**Why Railway?**

- ✅ Free tier: $5 credit/month
- ✅ Supports Docker Compose
- ✅ Easy GitHub integration
- ✅ PostgreSQL, Redis, RabbitMQ available
- ✅ Better than Heroku (Heroku removed free tier)

**Steps:**

1. **Sign up**: https://railway.app (Link GitHub)

2. **Create new project**: Click "New Project"

3. **Connect GitHub**: "Deploy from GitHub repo"

4. **Add services** (one by one):
   - Click "Add Service" → "Database" → PostgreSQL
   - Click "Add Service" → "Database" → Redis
   - Click "Add Service" → "Marketplace" → RabbitMQ

5. **Deploy app**:
   - Click "Add Service" → "Docker Image"
   - Set image: `ghcr.io/your-org/aeterna:main`
   - Or deploy from repo (Railway auto-detects Dockerfile)

6. **Configure environment**:
   - Set variables in Railway dashboard
   - They auto-link services

---

### 🥈 Alternative: Fly.io (Free Trial + Pay-as-you-go)

**Why Fly.io?**

- ✅ Free trial with $5 credit
- ✅ Pay-as-you-go (usually $20-40/month for all services)
- ✅ Excellent performance
- ✅ Worldwide data centers

**Steps:**

1. **Install Fly CLI**:

   ```bash
   # macOS
   brew install flyctl

   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex

   # Linux
   curl https://fly.io/install.sh | sh
   ```

2. **Login**:

   ```bash
   flyctl auth login
   ```

3. **Create app**:

   ```bash
   flyctl launch
   # Choose app name, region, don't migrate yet
   ```

4. **Add PostgreSQL**:

   ```bash
   flyctl postgres create
   # Follow prompts, choose free tier
   ```

5. **Deploy**:

   ```bash
   flyctl deploy
   ```

6. **Run migrations**:
   ```bash
   flyctl ssh console
   # Inside console:
   alembic upgrade head
   exit
   ```

---

### 🥉 Alternative: Heroku (Free for hobby use now requires paid dyno)

If you want simplicity, Heroku eco plans are $5-7/month (cheapest option).

---

### 💻 Option 4: Self-Hosted (Your Own Server)

**Why?**

- ✅ Complete control
- ✅ Cheapest long-term ($5-15/month VPS)
- ✅ No vendor lock-in

**Popular VPS providers:**

- DigitalOcean (App Platform): $7-12/month
- Linode: $5/month
- Vultr: $2.50-5/month (smaller, good for testing)
- AWS (free tier): 12 months free

**Basic deployment on DigitalOcean App Platform:**

1. Start with Docker locally ✅ (you're here!)
2. Push image to Docker Hub or GitHub Container Registry
3. Connect to DigitalOcean App Platform
4. Add services (PostgreSQL, Redis, RabbitMQ from marketplace)
5. Deploy!

---

## Step-by-Step Local Deployment

### Phase 1: Local Development Setup

```bash
# 1. Navigate to project
cd AETERNA-Autonomous-Alpha-Engine

# 2. Run setup script
# Windows:
powershell -ExecutionPolicy Bypass -File scripts/dev_start.ps1

# Linux/macOS:
bash scripts/dev_start.sh

# Wait for output like:
# ✓ Development environment is ready!
# API Documentation: http://localhost:8000/docs
```

### Phase 2: Test the Application

```bash
# Verify all services running
make health

# Output should show:
# App: 200 OK
# Postgres: accepting connections
# Redis: PONG
# RabbitMQ: responding
```

### Phase 3: Run Tests

```bash
# Run full test suite
make test-coverage

# This runs:
# - pytest with coverage
# - flambe code format check
# - mypy type check
# - All tests pass? Green ✓
```

### Phase 4: Build Docker Image (For Deployment)

```bash
# Build production image locally
docker build -t aeterna:v1.0.0 .

# Test image locally
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@localhost:5432/db" \
  -e REDIS_URL="redis://localhost:6379" \
  -e ENVIRONMENT="production" \
  aeterna:v1.0.0

# Should start on http://localhost:8000
```

### Phase 5: Deploy to Free Service (Railway Example)

```bash
# 1. Push image to registry
docker login ghcr.io  # Login with GitHub token

docker tag aeterna:v1.0.0 ghcr.io/YOUR-USERNAME/aeterna:v1.0.0

docker push ghcr.io/YOUR-USERNAME/aeterna:v1.0.0

# 2. Go to Railway.app
# 3. Create new project
# 4. Add PostgreSQL service
# 5. Add Redis service
# 6. Add RabbitMQ
# 7. Add Docker image service (use your pushed image)
# 8. Set environment variables
# 9. Deploy!
```

---

## Configuration Files Explained

### `.env` - Local Configuration

```bash
# Copy this for local development
cp .env.example .env

# Edit .env with your values:
ENVIRONMENT=development      # Or: production
DEBUG=true                    # Or: false
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/aeterna_db
REDIS_URL=redis://redis:6379
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

### `docker-compose.yml` - Local Stack

```yaml
# Contains:
services:
  app: FastAPI application
  postgres: Database
  redis: Cache
  rabbitmq: Message broker
  celery_worker: Background tasks
  celery_beat: Scheduled tasks
```

### `Dockerfile` - Production Image

```dockerfile
# Multi-stage build:
# Stage 1: Build dependencies (temporary)
# Stage 2: Runtime (small, optimized final image)
```

---

## Deployment Checklist

Before deploying anywhere:

```bash
# ✓ Code quality
make quality

# ✓ Tests pass
make test

# ✓ Build works
docker build -t aeterna:test .

# ✓ Local image runs
docker run -p 8000:8000 aeterna:test

# ✓ Database migrations ready
make migrate

# ✓ All environment variables set
cat .env | grep -E "^[A-Z]" | wc -l  # Should show many vars
```

---

## Troubleshooting

### "Ports already in use"

```bash
# Find what's using port 8000
netstat -anno | findstr :8000  # Windows
lsof -i :8000  # macOS/Linux

# Either:
# 1. Kill the process
# 2. Change port in docker-compose.yml (e.g., "9000:8000")
```

### "Docker daemon not running"

```bash
# Windows: Start Docker Desktop
# macOS: brew services start docker
# Linux: sudo systemctl start docker
```

### "Can't connect to database"

```bash
# Check if postgres is running
docker-compose ps

# Check postgres logs
docker-compose logs postgres

# Restart postgres
docker-compose restart postgres
docker-compose exec app alembic upgrade head
```

### "Tests fail locally but pass in CI"

```bash
# Run tests exactly like CI does:
docker-compose exec app pytest tests/ -v

# Or with coverage:
docker-compose exec app pytest tests/ -v --cov=app
```

### "Image too large for free tier"

```bash
# Check image size
docker images aeterna

# Reduce size:
# 1. Use .dockerignore (already done)
# 2. Multi-stage build (already done)
# 3. Use slim Python base (already done)
# Size should be < 500MB
```

---

## Next Steps

### If Deploying Locally (Development)

1. ✅ You're done! Use `make` commands
2. Run tests: `make test`
3. Code changes auto-reload
4. Check logs: `make logs`

### If Deploying to Cloud (Production)

**Choose your platform:**

- 🚀 **Railway.app** (easiest, free trial)
- 🚀 **Fly.io** (best performance)
- 🚀 **DigitalOcean** (cheapest long-term)

**Then follow platform-specific guide** (see Free Deployment Alternatives)

---

## CI/CD Pipeline

Your GitHub Actions pipeline automatically:

1. **On every push to main/develop**:
   - ✓ Runs tests
   - ✓ Lints code
   - ✓ Checks security
   - ✓ Builds Docker image
   - ✓ Pushes to GitHub Container Registry

2. **View results**:
   - Go to GitHub repo → Actions tab
   - See test results, coverage, build status

3. **Use built image for deployment**:
   - Image stored at: `ghcr.io/YOUR-ORG/aeterna:main`
   - Pull and run anywhere

---

## Performance Tips

### Optimize for free tier costs:

```bash
# 1. Use smallest service tiers
# 2. Turn off auto-scaling
# 3. Use PostgreSQL free tier (shared)
# 4. Combine Redis + RabbitMQ into one service if possible
# 5. Don't spawn extra Celery workers

# Local optimization:
make quality  # Before pushing, avoid CI failures
```

---

## Getting Help

📚 **Documentation:**

- API Docs: `http://localhost:8000/docs`
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Docker Docs](https://docs.docker.com/)

🐛 **Common Issues:**

1. Check logs: `make logs`
2. Check services: `make health`
3. Check Docker: `docker ps`

✉️ **Report Issues:**

- GitHub Issues (if in repo)
- Check logs for error messages
- Ensure all services running: `docker-compose up -d` and `make health`

---

## Quick Command Reference

```bash
# Start development
make dev

# Run tests
make test

# Check code quality
make quality

# View logs
make logs

# Stop everything
make down

# Reset (fresh start)
make reset

# Database backup
make db-dump

# Database shell
make db-shell

# Service health
make health

# All commands
make help
```

---

**You're all set!** 🎉

Choose your deployment path and follow the steps. For questions, check the logs or review the DEPLOYMENT_GUIDE.md file.
