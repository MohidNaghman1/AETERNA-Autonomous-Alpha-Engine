# AETERNA Deployment Files Guide

## Overview

This guide explains each deployment-related file added to the project.

## Files Summary

### Root Level Files

#### `Dockerfile`

**Purpose**: Production-ready Docker image definition using multi-stage build
**Key Features**:

- **Builder stage**: Compiles Python dependencies (temporary)
- **Runtime stage**: Slim Python image with only necessary runtime files
- **Non-root user**: Runs as unprivileged `appuser` for security
- **Health checks**: Built-in liveness probe
- **Multi-stage**: Reduces final image size by ~70%

**Usage**:

```bash
docker build -t aeterna:latest .
docker run -p 8000:8000 aeterna:latest
```

#### `docker-compose.yml`

**Purpose**: Local and staging environment orchestration
**Services**:

- `app`: FastAPI application with hot-reload
- `postgres`: PostgreSQL 15 database
- `redis`: Redis cache (7-alpine)
- `rabbitmq`: RabbitMQ message broker (3.12)
- `celery_worker`: Async task processing
- `celery_beat`: Scheduled task scheduler

**Features**:

- Health checks for each service
- Volume persistence for databases
- Environment variable management
- Service dependency ordering

**Usage**:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### `docker-compose.override.yml`

**Purpose**: Development-specific overrides
**What it does**:

- Enables auto-reload for code changes
- Loads `.env` file
- Sets `DEBUG=true` and `ENVIRONMENT=development`
- Overrides build context for quick iteration

**Note**: Auto-applied by Docker Compose; separate from `docker-compose.yml`

#### `.dockerignore`

**Purpose**: Prevents unnecessary files from being copied into Docker images
**Excludes**:

- Git files
- Virtual environments
- Python cache/compiled files
- IDE configurations
- Test files and coverage
- Documentation
- Logs and temporary files

**Effect**: Reduces Docker build context size and final image size

#### `render.yml`

**Purpose**: Render.com deployment configuration (Infrastructure as Code)
**Defines**:

- **Web Service**: Main FastAPI application
- **PostgreSQL**: Database with auto-backup
- **Redis**: Cache service
- **RabbitMQ**: Message broker
- **Celery Worker**: Background task processor

**Key Benefits**:

- One-click deployment
- Auto-provisioned SSL/TLS
- Environment variables auto-configured
- Auto-scaling capabilities
- Monitoring built-in

**Deployment**: Push to GitHub → Render reads `render.yml` → Auto-deploys

#### `.env.example`

**Purpose**: Template for environment configuration
**Contents**:

- Database settings
- Redis/RabbitMQ credentials
- JWT and security keys
- Email configuration
- Telegram bot tokens
- API settings

**Usage**:

```bash
cp .env.example .env
# Edit .env with your values
```

#### `Makefile`

**Purpose**: Simplify common Docker and development commands
**Categories**:

- Docker management: `make up`, `make down`, `make logs`
- Testing: `make test`, `make test-coverage`
- Code quality: `make lint`, `make format`, `make typecheck`
- Database: `make migrate`, `make db-shell`, `make db-dump`
- Development: `make dev`, `make reset`

**Example**:

```bash
make help          # Show all commands
make dev           # Start dev environment
make quality       # Run all checks
```

### GitHub Workflows (`.github/workflows/`)

#### `ci-cd.yml`

**Purpose**: Continuous Integration/Continuous Deployment pipeline
**Triggers**: On push/PR to main/develop branches

**Jobs**:

1. **lint-and-test**
   - Sets up Python 3.11
   - Starts PostgreSQL, Redis, RabbitMQ
   - Runs: flake8, black, mypy, pytest with coverage
   - Uploads coverage to Codecov

2. **build**
   - Only runs on successful lint-and-test
   - Builds Docker image
   - Pushes to GitHub Container Registry (ghcr.io)
   - Tags with branch/version/SHA
   - Uses buildx cache for faster builds

3. **security-scan**
   - Trivy filesystem vulnerability scan
   - Safety dependency check
   - SARIF report to GitHub Security
   - Identifies known vulnerabilities

**Status Badges**: Add to README:

```markdown
![CI/CD Pipeline](https://github.com/your-org/AETERNA/workflows/CI%2FCD%20Pipeline/badge.svg)
```

### Scripts Folder (`scripts/`)

#### `dev_start.sh`

**Purpose**: Automated development environment setup (Linux/macOS)
**Does**:

- Checks Docker/Docker Compose installation
- Creates `.env` from template
- Builds images
- Starts services
- Runs migrations
- Shows useful info

**Usage**:

```bash
bash scripts/dev_start.sh
```

#### `dev_start.ps1`

**Purpose**: Automated development environment setup (Windows)
**Same as `dev_start.sh` but for PowerShell**

**Usage**:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev_start.ps1
```

### Documentation Files (`docs/`)

#### `DEPLOYMENT_GUIDE.md`

**Purpose**: Comprehensive deployment instructions
**Covers**:

- Local development with Docker Compose
- Docker image building
- GitHub Actions CI/CD pipeline
- Render.com deployment
- Database migrations
- Troubleshooting
- Performance optimization
- Security best practices

#### `DEPLOYMENT_CHECKLIST.md`

**Purpose**: Pre-deployment verification checklist
**Sections**:

- Code quality checks
- Configuration requirements
- Docker & Compose verification
- Testing requirements
- Security validation
- Post-deployment verification
- Rollback procedures

## Deployment Flow

```
┌─────────────────────────────────────────────────────────┐
│              Developer Workflow                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ↓
         (git push to main/develop)
                          │
                          ↓
        ┌─────────────────────────────────────┐
        │    GitHub Actions CI/CD Pipeline    │
        │  (.github/workflows/ci-cd.yml)      │
        └─────────────────────────────────────┘
                          │
        ┌─────────┬───────┴────────┬──────────┐
        ↓         ↓                ↓          ↓
    [Lint]   [Tests]        [Security]  [Build Docker]
        │         │                │          │
        └─────────┴────────────────┴──────────┘
                          │
                    ✓ All pass?
                          │
        ┌─────────────────┴──────────────────────┐
        │                                        │
        ↓ CI passes                              X Fails → Notification
    Docker image built                      (Developers fix issues)
    Tagged & pushed to ghcr.io                  │
        │                                        │
        ↓                                        │
    ┌──────────────────────────────────────┐    │
    │  GitHub Container Registry (ghcr.io) │◄───┘
    └──────────────────────────────────────┘
        │
        ↓ (Manual or Auto: Main branch)
    ┌──────────────────────────────────────┐
    │  Render.com reads render.yml          │
    │  • Deploys Web Service                │
    │  • Sets up PostgreSQL                 │
    │  • Configures Redis                   │
    │  • Sets up RabbitMQ                   │
    │  • Starts Celery Worker               │
    └──────────────────────────────────────┘
        │
        ↓
    Application Live
    Monitoring & Alerts Active
```

## Quick Start Paths

### For Local Development

```
1. Clone repo
2. Run: bash scripts/dev_start.sh (or .ps1 on Windows)
3. Use: make dev
4. Code & Test with hot-reload
```

### For Production on Render

```
1. Connect GitHub repo to Render
2. Render reads render.yml
3. Push to main branch
4. Automatic deployment
5. Services up & running
```

### For Manual Docker Deployment

```
1. docker build -t aeterna:latest .
2. docker run -e DATABASE_URL=... aeterna:latest
3. Configure environment variables
```

## Environment Variables

### Required for Production

```
SECRET_KEY              # JWT signing key
DATABASE_URL           # PostgreSQL connection
REDIS_URL              # Redis connection
RABBITMQ_URL           # RabbitMQ connection
ENVIRONMENT=production # Set to production
DEBUG=false            # Disable debug mode
```

### Optional

```
TELEGRAM_BOT_TOKEN     # For Telegram integration
SMTP_PASSWORD          # For email
SENTRY_DSN             # For error tracking
```

## Monitoring & Maintenance

### Viewing Logs

```bash
# Docker Compose
docker-compose logs -f app

# Render Dashboard
Dashboard → Service → Logs tab
```

### Database Backup

```bash
# Local
make db-dump

# Render
Auto-backup enabled (configurable)
```

### Performance Metrics

- Render Dashboard: CPU, Memory, Network
- Application metrics: See `/metrics` endpoint

## File Dependencies

```
Dockerfile ────┐
               ├─→ docker-compose.yml
.dockerignore ─┤   │
               └─→ .github/workflows/ci-cd.yml
                   │
requirements.txt ──┤
                   ├─→ render.yml
.env.example ──────┤
                   └─→ Documentation files
    Makefile ──────────→ scripts/dev_start.*
```

## Troubleshooting File Location

| Issue                    | Check File                                |
| ------------------------ | ----------------------------------------- |
| Build fails              | Check `Dockerfile` syntax                 |
| Services won't connect   | Check `docker-compose.yml` ports/networks |
| Environment vars not set | Check `.env` and `render.yml`             |
| Tests fail in CI         | Check `.github/workflows/ci-cd.yml`       |
| Deployment fails         | Check `render.yml` configuration          |
| Script errors            | Check `scripts/dev_start.*` permissions   |

## Next Steps

1. **Update README** with deployment badges and quickstart
2. **Configure GitHub Secrets** for Docker registry access
3. **Test locally** with `make dev`
4. **Deploy to Render** for production
5. **Set up monitoring** (optional: Sentry, DataDog)
6. **Configure alerts** for production issues
