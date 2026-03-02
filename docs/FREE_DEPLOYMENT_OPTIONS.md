# Free Deployment Options - Complete Comparison

## 💰 Cost Comparison

| Platform         | Free Tier    | Monthly Cost | Best For                             |
| ---------------- | ------------ | ------------ | ------------------------------------ |
| **Railway**      | $5 credit    | $10-20/mo    | Easiest option, generous free tier   |
| **Fly.io**       | $3 credit    | $20-40/mo    | Best performance, global datacenters |
| **VultrVPS**     | None         | $2.50-5/mo   | Most budget-friendly                 |
| **DigitalOcean** | Free trial   | $7-12/mo     | Balanced cost/performance            |
| **Local Docker** | Free forever | $0           | Development/testing                  |

---

## 🥇 RECOMMENDED: Railway.app - Easiest Setup

### Why Railway?

- ✅ Simplest deployment process
- ✅ Free starting credit ($5-10)
- ✅ Docker Compose support
- ✅ One-click service setup
- ✅ Automatic SSL/HTTPS
- ✅ GitHub integration built-in

### Step-by-Step Railway Deployment

#### Step 1: Sign Up

```
1. Go to: https://railway.app
2. Click "Start a New Project"
3. Sign in with GitHub
4. Grant Railway access to your repo
```

#### Step 2: Create Project

```
1. Click "Create New"
2. Name: "AETERNA"
3. Click "Create Project"
```

#### Step 3: Add Services

**Add PostgreSQL:**

```
1. Click "Add Service" → "Database" → PostgreSQL
2. Wait 30 seconds
3. Note the connection string (shown in Variables)
```

**Add Redis:**

```
1. Click "Add Service" → "Database" → Redis
2. Wait 30 seconds
3. Note the connection string
```

**Add RabbitMQ:**

```
1. Click "Add Service" → "Add from Marketplace"
2. Search "RabbitMQ"
3. Select & click Deploy
4. Wait 1 minute
```

**Add Your App:**

```
1. Click "Add Service" → "GitHub Repo"
2. Select AETERNA repo
3. Railway auto-detects Dockerfile
4. Click Deploy
```

#### Step 4: Configure Environment Variables

```
For Each Service (Auto-configured by Railway):

DATABASE_URL=          ← Auto-set by PostgreSQL service
REDIS_URL=             ← Auto-set by Redis service
RABBITMQ_URL=          ← Auto-set by RabbitMQ service

Manual Variables (Set in Railway Dashboard):
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-secret-key-here
```

#### Step 5: Deploy

```
1. Click "Deploy"
2. Railway builds from Dockerfile
3. Services connect automatically
4. App starts in 2-5 minutes
5. Public URL provided
```

#### Step 6: Run Migrations

```
1. Click on app service → "Shell" tab
2. Run: alembic upgrade head
3. Done!
```

### Accessing Your App on Railway

```
API:     https://your-app-name.up.railway.app
Docs:    https://your-app-name.up.railway.app/docs
Monitor: Dashboard at railway.app
```

### Railway Cost Breakdown

```
PostgreSQL:  ~$1.50/GB used
Redis:       ~$0.01/day (minimal)
RabbitMQ:    ~$2/month
App:         ~$5-10/month

Total: $10-20/month (manageable!)
```

### Stop Charges When Not Using

```
1. Go to Dashboard
2. Pause services (don't delete)
3. Resume anytime
4. Only pay when running
```

---

## 🥈 ALTERNATIVE: Fly.io - Best Performance

### Why Fly.io?

- ✅ Superior performance
- ✅ Global datacenters
- ✅ Free $5-10 trial
- ✅ Pay-as-you-go
- ✅ Worldwide deployment

### Quick Fly.io Setup

#### Installation

```bash
# macOS
brew install flyctl

# Windows (PowerShell as Admin)
iwr https://fly.io/install.ps1 -useb | iex

# Linux
curl https://fly.io/install.sh | sh
```

#### Deploy

```bash
# 1. Login
flyctl auth login

# 2. Create app
flyctl launch

# 3. Follow prompts (choose region near you)

# 4. Add PostgreSQL
flyctl postgres create --name aeterna-postgres

# 5. Deploy
flyctl deploy

# 6. Add Redis (optional, in dashboard)

# 7. Run migrations
flyctl ssh console
# Inside: alembic upgrade head
exit
```

#### Access

```
https://APPNAME.fly.dev
```

---

## 🚀 Option 3: Docker Hub + Your Own Server (Cheapest if Long-term)

If you want to self-host:

### Cost: $2.50-12/month

**Option A: Vultr ($2.50/month)**

- Smallest VPS
- Great for learning
- Limited resources

**Option B: DigitalOcean ($5-12/month)**

- More reliable
- Better support
- Docker pre-installed recommended

**Option C: Linode ($5/month)**

- Good uptime
- Decent support

### Self-Hosting Steps

#### 1. Buy VPS

```
Choose provider above
Select: Ubuntu 22.04 LTS
Size: Smallest available (fine for testing)
Region: Near you
```

#### 2. Connect to Server

```bash
# SSH into server
ssh root@YOUR_SERVER_IP

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

#### 3. Clone Your Repo

```bash
git clone https://github.com/YOUR/AETERNA.git
cd AETERNA
cp .env.example .env
# Edit .env with your settings
```

#### 4. Start with Docker Compose

```bash
docker-compose -f docker-compose.yml up -d
docker-compose exec app alembic upgrade head
```

#### 5. Setup Domain (Optional)

```
1. Buy domain (namecheap, godaddy)
2. Point A record to your VPS IP
3. Add reverse proxy (nginx)
```

#### 6. Get SSL Certificate (Free)

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Get certificate
certbot certonly --standalone -d yourdomain.com
```

---

## 🏠 Option 4: Keep Running Locally (Free Forever)

### Best for:

- Development
- Testing
- Learning
- Demo purposes
- Small team (your computer stays on)

### Setup (What You Already Have)

```bash
# Already completed in previous steps:
bash scripts/dev_start.sh    # or .ps1 on Windows

# Services running locally on:
# API: http://localhost:8000
# RabbitMQ: http://localhost:15672
# PostgreSQL: localhost:5432
# Redis: localhost:6379
```

### Keep It Running

**Option 1: Windows Service** (Computer always on)

```
1. Windows Search → Services
2. Create service to run docker-compose
3. Auto-restart if computer reboots
```

**Option 2: Cloud Play** (Free cloud IDE)

```
1. Use GitHub Codespaces (free hours)
2. Keep container running
3. Kill when done
```

**Option 3: Keep Computer On**

```
1. Disable sleep mode
2. Leave docker-compose running
3. Access from laptop: http://localhost:8000
```

---

## 📊 Decision Matrix

### If You Need:

**Production-ready immediately?**
→ Railway.app ✅

**Best performance & global?**
→ Fly.io ✅

**Absolute cheapest?**
→ Vultr VPS $2.50/mo ✅

**Learning/not mission-critical?**
→ Local Docker (free) ✅

**Team collaboration?**
→ Railway (easy GitHub sync) ✅

**Full control?**
→ Self-hosted VPS ✅

---

## 📝 FAQ

### Q: Can I use free tier forever?

**A:** Railway gives free credit monthly. When it runs out, you pay, but you can pause services to stop charges.

### Q: How do I backup data?

**Railway:**

```
1. Dashboard → PostgreSQL → Backups
2. Automatic daily backups
```

Self-hosted:

```bash
docker-compose exec postgres pg_dump -U postgres > backup.sql
```

### Q: Can I scale easily?

**Railway:** Yes, increase service size in dashboard
**Fly.io:** Yes, `flyctl scale vm=performance-1x`
**VPS:** Requires manual upgrade

### Q: What if I outgrow free tier?

**Railway:** Upgrade to pro plan
**Fly.io:** Pay-as-you-go model
**VPS:** Upgrade VPS size

### Q: How do I monitor my app?

**Railway:** Built-in dashboard + logs
**Fly.io:** `flyctl status` command + dashboard
**VPS:** Manual monitoring (Prometheus optional)

### Q: Can I use custom domain?

**Railway:** Yes, settings in dashboard
**Fly.io:** Yes, `flyctl certs create yourdomain.com`
**VPS:** Yes, point DNS to server IP

---

## 🎯 Recommended Path: Railway.app

### Timeline:

1. **Now**: Local development works ✅
2. **Today**: Sign up at Railway.app (5 min)
3. **Today**: Deploy in 30 minutes
4. **Cost**: $10-20/month when free credit runs out
5. **Later**: Scale up if needed

### Cheap & Fast:

```
1. Railway free credit: $5-10
2. Your local machine is still option
3. Total: $0 this month
4. Next month: ~$10 basic plan
```

---

## Quick Start Commands

### Local Development

```bash
bash scripts/dev_start.sh    # macOS/Linux
# or
powershell -ExecutionPolicy Bypass -File scripts/dev_start.ps1  # Windows

# Then:
make dev
make logs
make test
```

### Push to Railway (After Setup)

```bash
git push origin main
# Railway automatically redeploys!
```

### Local Backup Before Deploy

```bash
make db-dump
# Creates: backups/aeterna_YYYYMMDD_HHMMSS.sql
```

---

## ⚠️ Important Notes

1. **Never commit `.env` file**

   ```
   .env is ignored by git ✓
   Set variables in platform dashboard instead
   ```

2. **Keep secrets safe**

   ```
   SECRET_KEY - Generate a random string
   API keys - Use platform's secret storage
   Passwords - Strong & unique
   ```

3. **Database migrations**

   ```
   Always run: alembic upgrade head
   After first deploy and after schema changes
   ```

4. **Monitor costs**
   ```
   Railway: Dashboard shows real-time usage
   Set alerts in Railway settings
   Pause services when not using
   ```

---

## 🎓 Next Steps

1. ✅ **Today**: You have working local setup
2. **Choose**: Pick Railway.app (recommended)
3. **Deploy**: Follow Railway setup (30 min)
4. **Test**: Verify app works at railway URL
5. **Monitor**: Check dashboard for issues

---

**Need Help?**

- Railway Docs: https://docs.railway.app
- Fly.io Docs: https://fly.io/docs
- FastAPI: https://fastapi.tiangolo.com
- Docker: https://docs.docker.com
