# Deployment Guide - AETERNA

## Overview

This guide covers deploying AETERNA using Docker, Docker Compose, GitHub Actions (CI/CD), and Render.com.

## Local Development with Docker Compose

### Prerequisites
- Docker & Docker Compose installed
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AETERNA-Autonomous-Alpha-Engine
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - FastAPI application (http://localhost:8000)
   - PostgreSQL database (port 5432)
   - Redis cache (port 6379)
   - RabbitMQ broker (http://localhost:15672)
   - Celery worker
   - Celery beat (scheduled tasks)

4. **Run migrations**
   ```bash
   docker-compose exec app alembic upgrade head
   ```

5. **View logs**
   ```bash
   docker-compose logs -f app
   ```

### Common Docker Compose Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (Warning: deletes data)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Run specific service
docker-compose up -d postgres

# Access database
docker-compose exec postgres psql -U postgres -d aeterna_db

# Run tests
docker-compose exec app pytest tests/ -v
```

## Docker Image Building

### Build Production Image Locally

```bash
# Build
docker build -t aeterna:latest .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e REDIS_URL="redis://localhost:6379" \
  aeterna:latest
```

### Multi-stage Build Benefits
- **Builder stage**: Compiles dependencies (large intermediate image)
- **Runtime stage**: Only includes runtime dependencies (smaller final image)
- **Security**: Non-root user runs the application
- **Health checks**: Included for production readiness

## GitHub Actions CI/CD Pipeline

### Workflow Triggers
- Pushes to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### Pipeline Steps

1. **Lint & Test**
   - Python 3.11 environment setup
   - Dependency installation
   - Flake8 linting
   - Black code formatting check
   - MyPy type checking
   - Pytest with coverage
   - Code coverage upload to Codecov

2. **Build & Push**
   - Docker image build (multi-stage)
   - Push to GitHub Container Registry
   - Automatic tagging (branch, semver, SHA)

3. **Security Scan**
   - Trivy filesystem scan
   - Safety dependency check
   - SARIF report upload to GitHub Security tab

### Accessing CI/CD Results

- **Tests**: View in "Checks" tab of PR
- **Coverage**: Check Codecov badge/reports
- **Docker Images**: `ghcr.io/your-org/your-repo:tag`

## Deployment on Render

### Prerequisites
- Render.com account
- GitHub repository connected to Render
- Environment variables configured

### Deploy Using render.yml

1. **Connect Repository**
   - Sign in to Render.com
   - Click "New +" → "Blueprint"
   - Select your GitHub repository
   - Render reads `render.yml` automatically

2. **Configuration in render.yml**
   - **Web Service**: Main FastAPI app (pro plan)
   - **PostgreSQL**: Database (pro plan)
   - **Redis**: Cache service (pro plan)
   - **RabbitMQ**: Message broker (pro plan)
   - **Worker**: Celery worker for async tasks

3. **Deploy**
   - Select branch (main recommended)
   - Click "Deploy"
   - Render creates all services automatically
   - Migration runs automatically

### Render Services Breakdown

| Service | Type | Purpose |
|---------|------|---------|
| aeterna-api | Web | Main FastAPI application |
| aeterna_postgres | PostgreSQL | Relational database |
| aeterna-redis | Redis | Caching & session storage |
| aeterna-rabbitmq | RabbitMQ | Message broker for Celery |
| aeterna-celery-worker | Worker | Process async tasks |

### Environment Variables on Render

Most are auto-configured from `render.yml`:
- `DATABASE_URL`: Auto-set from PostgreSQL service
- `REDIS_URL`: Auto-set from Redis service
- `RABBITMQ_URL`: Auto-set from RabbitMQ service

**Manual Environment Variables** (set in Render dashboard):
- `SECRET_KEY`: Your JWT secret
- `TELEGRAM_BOT_TOKEN`: If using Telegram
- `SMTP_PASSWORD`: Email service password
- Any other API keys

### Monitoring on Render

- **Logs**: View in service dashboard
- **Health**: Green checkmark = healthy
- **Metrics**: CPU, memory, network usage
- **Alerts**: Set up email notifications

## DNS & Domain Setup

1. **Add Custom Domain** (in Render dashboard under service settings)
2. **Point DNS records** to Render's assigned values
3. **SSL Certificate**: Auto-provisioned by Render

## Database Migrations

### Running Migrations

```bash
# Local with Docker
docker-compose exec app alembic upgrade head

# Production on Render (via dashboard or SSH)
# Use Curl or direct command if SSH access available
```

### Creating New Migrations

```bash
docker-compose exec app alembic revision --autogenerate -m "Description"
docker-compose exec app alembic upgrade head
```

## Troubleshooting

### Docker Compose Issues

**Service won't start**
```bash
# Check logs
docker-compose logs service_name

# Rebuild
docker-compose build --no-cache service_name
docker-compose up -d service_name
```

**Port already in use**
```bash
# Change port in docker-compose.yml
# e.g., "9000:8000" instead of "8000:8000"
```

### Render Deployment Issues

**Build fails**
- Check logs in Render dashboard
- Ensure `render.yml` syntax is correct
- Verify environment variables

**Services not connecting**
- Database: Wait for PostgreSQL health check
- Redis/RabbitMQ: Check service status first
- Verify connection strings in environment

**Out of memory**
- Upgrade plan (pro → pro+)
- Optimize queries
- Configure RabbitMQ memory limits

## Performance Optimization

### Production Checklist

```yaml
✓ Environment: production
✓ Debug: false
✓ Use pro/pro+ plans on Render
✓ Enable Redis caching
✓ Configure CDN for static files
✓ Set up monitoring/alerts
✓ Regular database backups
✓ Use strong SECRET_KEY
✓ Configure CORS properly
✓ Rate limiting enabled
✓ Load testing in staging
```

### Scaling

- **Horizontal**: Add more Celery workers on Render
- **Vertical**: Upgrade service plans
- **Database**: Enable PostgreSQL read replicas
- **Cache**: Increase Redis memory

## Security Best Practices

1. **Never commit .env file**
2. **Rotate secrets regularly**
3. **Use strong passwords**
4. **Enable PostgreSQL encryption**
5. **Configure firewall rules**
6. **Review CI/CD logs for secrets**
7. **Keep dependencies updated**
8. **Monitor security scan results**

## Support & Resources

- [Docker Documentation](https://docs.docker.com/)
- [Render Documentation](https://render.com/docs)
- [GitHub Actions](https://docs.github.com/en/actions)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
