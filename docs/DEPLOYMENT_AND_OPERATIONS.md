# AETERNA: Deployment & Operations Guide

## Production Deployment, Monitoring, & Runbooks

**Document Version:** 1.0  
**Date:** March 2026  
**Classification:** Internal  
**Status:** Active  
**Last Updated:** March 25, 2026

---

## Table of Contents

1. Deployment Architecture
2. Pre-Deployment Checklist
3. Deployment Procedures
4. Monitoring & Observability
5. Database Management
6. Scaling & Performance
7. Disaster Recovery
8. Incident Runbooks
9. Maintenance Windows
10. Operational Metrics

---

## 1. Deployment Architecture

### 1.1 Environments

**Development:** Local machine

- Docker Compose (local PostgreSQL, Redis, RabbitMQ)
- Hot reload enabled
- No auth required

**Staging:** staging.aeterna.app

- Railway/Render production-like configuration
- Real database (copy of production)
- Full auth/security enabled
- Used for testing before prod

**Production:** aeterna.app

- Railway/Render (HA configuration)
- Auto-scaling enabled
- CDN enabled
- Real users access here

### 1.2 Service Architecture

```
┌─────────────────────────────────────────────┐
│              Nginx/Load Balancer            │
│  (HTTPS termination, rate limiting)         │
└────────────┬────────────────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌──────────┐      ┌──────────┐
│  App 1   │      │  App 2   │
│ (FastAPI)│      │ (FastAPI)│
└────┬─────┘      └────┬─────┘
     │                 │
     └────────┬────────┘
              ▼
     ┌─────────────────┐
     │   PostgreSQL    │
     │  (Primary with  │
     │   Replicas)     │
     └────────┬────────┘
              │
    ┌────────┬─────────────┐
    ▼        ▼             ▼
 ┌─────┐ ┌────────┐   ┌─────────┐
 │Redis│ │RabbitMQ│  │Backups  │
 └─────┘ └────────┘   │(S3/GCS) │
                       └─────────┘

Celery Workers (Auto-scaling)
Email delivery, Telegram messages, background tasks
```

---

## 2. Pre-Deployment Checklist

### 2.1 Code Quality Checks

**Before Every Deployment:**

```bash
# Run full test suite
pytest tests/ -v --cov=app --cov-report=html
# Target: >80% coverage

# Lint code
flake8 app/ --max-line-length=100
black app/ --check

# Type checking
mypy app/

# Security scanning
bandit -r app/

# Dependency check
pip-audit
safety check
```

### 2.2 Environment Validation

**Staging Environment (day before prod deploy):**

```bash
# Check all services are running
curl https://staging.aeterna.app/health
curl https://staging.aeterna.app/health/system

# Verify database connection
pytest tests/test_integration.py -k "database"

# Check API endpoints
pytest tests/test_api_integration.py -v

# Load test (simulate 100 concurrent users)
locust -f tests/load_test.py --headless -u 100 -r 10 -t 5m

# Check logs for errors
docker logs staging-app-1 | grep ERROR
docker logs staging-celery-1 | grep ERROR
```

### 2.3 Database Readiness

**Before Deployment (if schema changes):**

```bash
# Create migration (if new changes)
alembic revision --autogenerate -m "description"

# Test migration on staging database
flask db upgrade  # Test on staging copy

# Verify migration can rollback
flask db downgrade -1
flask db upgrade

# Backup production database
pg_dump -h prod-db-host -U postgres aeterna > backup_before_deploy.sql
gzip backup_before_deploy.sql
aws s3 cp backup_before_deploy.sql.gz s3://aeterna-backups/

# Verify backup integrity
gunzip < backup_before_deploy.sql.gz | head -20  # Quick check
```

---

## 3. Deployment Procedures

### 3.1 Staging Deployment (Test Environment)

**Frequency:** Daily (after code merge)  
**Downtime:** None (always has working version)

**Steps:**

```bash
#!/bin/bash
# deploy_staging.sh

set -e  # Exit on error

echo "=== Staging Deployment ==="
date

# 1) Pull latest code
git pull origin main

# 2) Run tests
echo "Running tests..."
pytest tests/ -v --cov=app
if [ $? -ne 0 ]; then
    echo "Tests failed. Stopping deployment."
    exit 1
fi

# 3) Build Docker image
echo "Building Docker image..."
docker build -t aeterna:staging .

# 4) Push to registry
docker tag aeterna:staging gcr.io/aeterna-project/aeterna:staging
docker push gcr.io/aeterna-project/aeterna:staging

# 5) Deploy to staging (Railway/render API)
echo "Deploying to staging..."
railway variables set GIT_DEPLOYMENT_TOKEN=$GIT_TOKEN
railway deploy --environment staging

# 6) Run smoke tests
sleep 30  # Wait for app to start
curl -f https://staging.aeterna.app/health || exit 1

# 7) Run integration tests
pytest tests/test_integration.py -v

echo "Staging deployment completed successfully!"
```

### 3.2 Production Deployment (Live Environment)

**Frequency:** Weekly (or as needed for hot fixes)  
**Downtime Target:** < 30 seconds (using blue-green deploy)  
**Approval:** Requires 2 senior engineers

**Pre-Deployment Approval Gate:**

```bash
#!/bin/bash
# deploy_prod_approval.sh

echo "=== Production Deployment Approval Gate ==="
echo ""
echo "Changes since last deployment:"
git log --oneline prod..main

echo ""
echo "Staging tests status:"
curl -s https://staging.aeterna.app/health
curl -s https://staging.aeterna.app/health/system

echo ""
read -p "Have you approved this deployment with 2 reviewers? (yes/no): " approval
if [ "$approval" != "yes" ]; then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo "✓ Approval confirmed. Ready to deploy."
```

**Blue-Green Deployment:**

```bash
#!/bin/bash
# deploy_prod_blue_green.sh

set -e

DB_BACKUP_BEFORE="backup_prod_before_$(date +%Y%m%d_%H%M%S).sql"

echo "=== Production Blue-Green Deployment ==="
date

# 1) Backup production database
echo "Backing up production database..."
pg_dump -h prod-db.aeterna.app -U postgres aeterna > $DB_BACKUP_BEFORE
gzip $DB_BACKUP_BEFORE
aws s3 cp ${DB_BACKUP_BEFORE}.gz s3://aeterna-backups/
echo "Backup complete: s3://aeterna-backups/${DB_BACKUP_BEFORE}.gz"

# 2) Deploy to "Green" instance (not receiving traffic)
echo "Deploying to GREEN instance..."
docker build -t aeterna:prod .
docker tag aeterna:prod gcr.io/aeterna-project/aeterna:prod
docker push gcr.io/aeterna-project/aeterna:prod

railway variables set ENVIRONMENT=production
railway deploy --environment green --container-port 8000

# 3) Run smoke tests on green
echo "Running smoke tests on GREEN..."
GREEN_URL="https://green-aeterna.app"
curl -f $GREEN_URL/health || { echo "Health check failed"; exit 1; }
curl -f $GREEN_URL/api/events?limit=1 || { echo "API test failed"; exit 1; }

# Run key integration tests
pytest tests/test_integration.py::test_alert_delivery -v

# 4) Run database migrations (on green)
echo "Running database migrations..."
flask db upgrade

# 5) Smoke tests after migration
pytest tests/test_integration.py::test_database -v

# 6) Run load test on green (spike test)
echo "Running spike test..."
locust -f tests/load_test.py --headless -u 50 -r 5 -t 2m --host=$GREEN_URL

# 7) Switch traffic from Blue to Green
echo "Switching traffic to GREEN..."
# This typically done via load balancer/DNS
# Example: Update Route53 to point to green instance
aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890ABC \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "aeterna.app",
                "Type": "A",
                "TTL": 60,
                "ResourceRecords": [{"Value": "GREEN-INSTANCE-IP"}]
            }
        }]
    }'

sleep 10  # Give DNS time to propagate

# 8) Monitor production for errors (60 seconds)
echo "Monitoring production (60 seconds)..."
for i in {1..12}; do
    ERROR_COUNT=$(curl -s https://aeterna.app/health/system | jq '.errors_last_minute')
    echo "Minute $((i*5)): $ERROR_COUNT errors"

    if [ "$ERROR_COUNT" -gt 100 ]; then
        echo "ERROR COUNT TOO HIGH. Rolling back!"
        # Switch back to blue
        aws route53 ... # Rollback DNS
        exit 1
    fi

    sleep 5
done

# 9) Keep blue as rollback
echo "Blue instance retained for quick rollback"
echo "To rollback: switch traffic back to Blue IP"

# 10) Send notification
slack_notify "✓ Production deployment successful"

echo "Deployment completed at $(date)"
```

### 3.3 Emergency Hot-Fix Deployment

**Use:** Critical bug affecting users  
**Approval:** 1 senior engineer (fast-tracked)  
**Procedure:**

```bash
#!/bin/bash
# deploy_hotfix.sh  (Fast-tracked with minimal tests)

echo "=== HOT-FIX DEPLOYMENT ==="
date

# 1) Verify hotfix
echo "Running critical tests only..."
pytest tests/test_integration.py -k "critical or hotfix" -v
if [ $? -ne 0 ]; then exit 1; fi

# 2) Build & push
docker build -t aeterna:hotfix .
docker push gcr.io/aeterna-project/aeterna:hotfix

# 3) Deploy to production
railway deploy --container aeterna:hotfix

# 4) Quick health check
sleep 10
curl -f https://aeterna.app/health || { echo "Health check failed"; exit 1; }

echo "Hot-fix deployed!"
```

---

## 4. Monitoring & Observability

### 4.1 Metrics to Collect

**Application Metrics:**

```
request_count (total requests per minute)
request_duration_seconds (latency histogram)
request_errors (4xx, 5xx count)
active_users (concurrent)

events_ingested (per minute)
events_processed (by Agent A, per minute)
alerts_generated (per minute)
alerts_delivered (email, Telegram, WebSocket per minute)

database_query_duration_seconds (slow query monitoring)
database_connections (current, max)
database_cache_hit_rate

redis_operations_total
redis_eviction_rate

rabbitmq_queue_depth (messages waiting)
rabbitmq_processing_rate
```

**Infrastructure Metrics:**

```
cpu_usage_percent (target: <70%)
memory_usage_percent (target: <80%)
disk_usage_percent (alert if >85%)
disk_io_bytes (read/write throughput)

network_bytes_in (ingress)
network_bytes_out (egress)

docker_container_restarts
docker_oom_kills (out-of-memory)
```

### 4.2 Monitoring Stack Setup

```bash
# prometheus: metrics collection & storage
# grafana: dashboards & visualization
# alertmanager: alert routing & escalation
# loki: log aggregation

docker run -d \
  -p 9090:9090 \
  -v /etc/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

docker run -d \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana

docker run -d \
  -p 9093:9093 \
  -v /etc/alertmanager.yml:/etc/alertmanager.yml \
  prom/alertmanager
```

### 4.3 Alert Rules

**Critical Alerts (page ops immediately):**

```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05 # >5% errors
  for: 5m
  annotations:
    summary: "High error rate on {{ $labels.instance }}"

- alert: DatabaseDown
  expr: up{job="postgres"} == 0
  for: 1m
  annotations:
    summary: "Database is down!"

- alert: HighMemoryUsage
  expr: container_memory_usage_bytes / 1024^3 > 1.5 # >1.5GB
  for: 5m
  annotations:
    summary: "High memory usage on {{ $labels.container }}"
```

**Warning Alerts (send email):**

```yaml
- alert: SlowQueries
  expr: rate(database_query_duration_seconds_bucket{le="1"}[5m]) < 0.8
  for: 10m
  annotations:
    summary: "80%+ of queries taking >1 second"

- alert: QueueBacklog
  expr: rabbitmq_queue_messages_total > 10000
  for: 5m
  annotations:
    summary: "RabbitMQ queue backlog > 10K messages"
```

### 4.4 Dashboards

**Main Production Dashboard:**

- Real-time request rate (per minute)
- Error rate % (with drill-down)
- P50, P95, P99 latencies
- CPU & memory usage
- Database connections & query performance
- Event processing rate & Agent A throughput
- Alert delivery success rate
- System uptime %

**Example Grafana dashboard:**

```json
{
  "dashboard": {
    "title": "AETERNA Production",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{ "expr": "rate(http_requests_total[1m])" }]
      },
      {
        "title": "Error Rate %",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[1m]) / rate(http_requests_total[1m]) * 100"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [
          { "expr": "histogram_quantile(0.95, http_requests_duration_seconds)" }
        ]
      }
    ]
  }
}
```

---

## 5. Database Management

### 5.1 Backup & Recovery

**Backup Strategy:**

- Daily full backups (2 AM UTC)
- Continuous transaction log archiving (for point-in-time recovery)
- Backups replicated to S3 (cross-region)
- Retention: 30 days

**Backup Job:**

```bash
#!/bin/bash
# backup_prod_db.sh (runs daily via cron)

set -e

BACKUP_DIR="/backups"
S3_BUCKET="s3://aeterna-backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aeterna_prod_$DATE.sql.gz"

echo "Starting daily backup..."

# 1) Create full backup
pg_dump \
  -h $POSTGRES_HOST \
  -U $POSTGRES_USER \
  -d aeterna \
  | gzip > $BACKUP_FILE

# 2) Verify backup integrity
if ! gunzip -t $BACKUP_FILE; then
    echo "Backup verification failed!"
    exit 1
fi

# 3) Upload to S3
aws s3 cp $BACKUP_FILE $S3_BUCKET/

# 4) Keep only latest 30 backups locally
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# 5) Verify S3 upload
if aws s3 ls $S3_BUCKET/$(basename $BACKUP_FILE); then
    echo "Backup successful: $(basename $BACKUP_FILE)"
else
    echo "S3 upload failed!"
    exit 1
fi
```

**Restore Procedure:**

```bash
#!/bin/bash
# restore_db.sh <backup-file>

BACKUP_FILE=$1
RESTORE_DB="aeterna_restored"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore_db.sh /path/to/backup.sql.gz"
    exit 1
fi

echo "Restoring database from: $BACKUP_FILE"

# 1) Create new database for restore test
createdb -h localhost -U postgres $RESTORE_DB

# 2) Restore from backup
gunzip < $BACKUP_FILE | psql -h localhost -U postgres $RESTORE_DB

# 3) Verify restore
psql -h localhost -U postgres $RESTORE_DB -c "
  SELECT count(*) FROM events;
  SELECT count(*) FROM alerts;
  SELECT count(*) FROM users;"

echo "Restore test completed. Database: $RESTORE_DB"
echo "If successful, copy data to production database."
```

**Monthly Restore Test:**

```bash
#!/bin/bash
# monthly_restore_test.sh

BACKUP_FILE=$(aws s3 ls s3://aeterna-backups/ | tail -1 | awk '{print $NF}')

echo "Testing restore of latest backup: $BACKUP_FILE"

aws s3 cp s3://aeterna-backups/$BACKUP_FILE /tmp/

./restore_db.sh /tmp/$BACKUP_FILE

echo "✓ Restore test passed"
```

### 5.2 Database Maintenance

**Daily:**

- Vacuum (garbage collection)
- Analyze (update statistics)

```sql
-- Scheduled via autovacuum (PostgreSQL built-in)
-- Or manually:
VACUUM aeterna;
ANALYZE aeterna;
```

**Weekly:**

- Reindex

```bash
# Offline reindex (high-lock)
# Schedule during maintenance window
REINDEX DATABASE aeterna;
```

**Monthly:**

- Check for missing indexes
- Identify slow queries
- Tune query plans

```bash
# Find slow queries
SELECT query, calls, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Find missing indexes
SELECT * FROM suggested_index_analysis();
```

---

## 6. Scaling & Performance

### 6.1 Horizontal Scaling

**Application Scaling (Auto-Scaling):**

```yaml
# docker-compose production scale
# Scale based on CPU usage

cpu_threshold_high: 70% # When to add more instances
cpu_threshold_low: 30% # When to remove instances
min_instances: 2 # Always running (HA)
max_instances: 10 # Cost control
scale_up_time: 2 minutes
scale_down_time: 10 minutes # Slower to avoid thrashing
```

**Celery Worker Scaling:**

```bash
# Scale workers based on queue depth
QUEUE_DEPTH=$(rabbitmq_queue_depth)

if [ $QUEUE_DEPTH -gt 5000 ]; then
    # Scale up: add 5 more workers
    docker-compose up -d --scale celery_worker=15
elif [ $QUEUE_DEPTH -lt 100 ]; then
    # Scale down: remove workers
    docker-compose up -d --scale celery_worker=5
fi
```

### 6.2 Vertical Scaling

**Database Scaling (if needed):**

- Upgrade PostgreSQL instance size
- Increase RAM (better query caching)
- Add read replicas for read-heavy workloads

**Monitoring:**

- CPU > 80% for 15 min → investigate or scale
- Memory > 90% for 10 min → scale immediately
- Connections > max_connections \* 0.8 → add pool

### 6.3 Performance Tuning

**Query Optimization:**

```bash
# Identify slow queries
tail -f /var/log/postgresql/postgresql.log | grep "duration: [0-9]*\.[0-9]* ms"

# Analyze query plans
EXPLAIN ANALYZE SELECT * FROM events WHERE user_id = 123;

# Add missing indexes
CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_alerts_user_id_created ON alerts(user_id, created_at);
```

**API Response Time Optimization:**

- Use response caching (Redis)
- Pagination for large result sets (never SELECT all)
- Database query optimization (indexes, joins)
- CDN for static assets

---

## 7. Disaster Recovery

### 7.1 RTO & RPO Targets

**Recovery Time Objective (RTO):** 30 minutes

- Time to restore service after disaster
- Includes: notification, restore, validation

**Recovery Point Objective (RPO):** 5 minutes

- Acceptable data loss
- Last backup/replica + 5 minutes of recent transactions

### 7.2 Disaster Scenarios & Recovery

**Scenario 1: Database Corruption**

```bash
# 1) Identify corruption
pg_catalog.pg_database => check pg_stat_database for corruption
or: REINDEX DATABASE

# 2) Restore from backup
./restore_db.sh /backup/aeterna_prod_latest.sql.gz

# 3) Verify data integrity
SELECT count(*) FROM events;
SELECT count(*) FROM alerts;

# 4) Validate critical operations
pytest tests/test_critical_paths.py
```

**Scenario 2: Complete Service Outage**

```bash
# 1) Determine root cause
- Check provider status (Railway/Render down?)
- Check infrastructure (disk full? OOM? network?)
- Check logs for errors

# 2) Recovery
- If cloud provider down: wait for recovery
- If infrastructure: auto-recovery from backups
- If data corruption: restore from backup

# 3) Notify users
- Update status page
- Send email to affected users
- Post on social media

# 4) Post-incident review
- What caused failure
- Why didn't monitoring detect it
- Preventive measures
```

### 7.3 Disaster Recovery Testing

**Monthly DR Drill:**

```bash
# Schedule: First Saturday of month, 10 AM UTC

echo "=== DISASTER RECOVERY DRILL ==="

# 1) Restore production database to staging
LATEST_BACKUP=$(aws s3 ls s3://aeterna-backups/ | tail -1 | awk '{print $NF}')
aws s3 cp s3://aeterna-backups/$LATEST_BACKUP /tmp/
./restore_db.sh /tmp/$LATEST_BACKUP

# 2) Verify data
psql -h staging-db -U postgres aeterna_restored -c "SELECT count(*) FROM events;"
psql -h staging-db - U postgres aeterna_restored -c "SELECT count(*) FROM alerts;"

# 3) Test failover (switch staging to use restored DB)
# Do NOT switch production

# 4) Document issues
# Send drill report to team

echo "DR drill completed"
```

---

## 8. Incident Runbooks

### 8.1 High Error Rate (>5%)

**Symptom:** Error rate spike in dashboards  
**Paging:** YES (immediate)

**Diagnosis:**

```bash
# 1) Check error logs
docker logs aeterna-app-1 | grep ERROR | tail -50

# 2) Check if specific endpoint affected
curl -v https://aeterna.app/health
curl -v https://aeterna.app/api/events

# 3) Check resource usage
docker stats

# 4) Check dependencies
curl https://api.twitter.com/2/tweets/search/recent  # Twitter API
curl https://eth-mainnet.g.alchemy.com/v2/$KEY  # Ethereum node
```

**Recovery:**

```bash
# Option 1: Restart service
docker restart aeterna-app-1
# Wait 2 min, check if error rate drops

# Option 2: Scale up (add more instances)
docker-compose up -d --scale aeterna=3

# Option 3: Rollback (if recent deployment)
./deploy_prod_blue_green.sh  # Switch back to previous version
```

### 8.2 Database Slow (p95 > 5 seconds)

**Symptom:** API response times >5 seconds  
**Paging:** YES

**Diagnosis:**

```bash
# 1) Check database load
psql -c "SELECT
  pid, usename, application_name, query, query_start
FROM pg_stat_activity
WHERE query != '<idle>'
ORDER BY query_start DESC;"

# 2) Check for long-running queries
pg_stat_statements => sort by mean_time DESC

# 3) Check lock contention
SELECT * FROM pg_locks WHERE NOT granted;

# 4) Check connection pool
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

**Recovery:**

```bash
# Option 1: Kill long-running query
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE 'SELECT..long query%';

# Option 2: Scale up database
# Upgrade instance size (add memory, CPU)
# Production will have <1 second downtime during reboot

# Option 3: Disable non-critical features
# Turn off expensive analytics queries
# Use read replicas for reporting

# Option 4: Add indexes
CREATE INDEX idx_events_optimized ON events(timestamp DESC, priority DESC);
ANALYZE events;
```

### 8.3 Out of Disk Space

**Symptom:** Disk at 95%+  
**Paging:** YES (imminent failure)

**Diagnosis:**

```bash
df -h
du -sh /var/lib/docker/*
du -sh /backups/*
du -sh /var/log/*
```

**Recovery:**

```bash
# Option 1: Clean old logs
find /var/log -name "*.log.*" -mtime +30 -delete

# Option 2: Compress backups
find /backups -name "*.sql" -exec gzip {} \;

# Option 3: Delete old Docker images
docker image prune -a

# Option 4: Archive old data
# Move events >6 months old to cold storage
# Keep only recent 100K events in main database

# Option 5: Expand disk
# AWS/GCP: expand volume
# Restart database to resize
```

### 8.4 RabbitMQ Queue Buildup (>10K messages)

**Symptom:** Queue depth growing, alerts delayed  
**Paging:** YES (if >50K messages)

**Diagnosis:**

```bash
# Check queue depth
curl -u guest:guest http://localhost:15672/api/queues | jq '.[] | .name, .messages'

# Check consumer
rabbitmq_consumer_status=$(curl -u guest:guest http://localhost:15672/api/consumers)
```

**Recovery:**

```bash
# Option 1: Scale up Celery workers
docker-compose up -d --scale celery_worker=20  # More workers

# Option 2: Check if consumers are running
docker logs celery_worker-1 | grep ERROR

# Option 3: Restart consumers
docker restart celery_worker

# Option 4: Purge queue if stuck (LAST RESORT)
# This loses messages!
rabbitmqctl purge_queue alert_delivery
```

---

## 9. Maintenance Windows

### 9.1 Planned Maintenance Schedule

**Every Week (Thursday 2-3 AM UTC):**

- Database VACUUM & ANALYZE
- Log rotation
- Dependency updates (if any critical)

**Every Month (2nd Sunday, 1-2 AM UTC):**

- Backup & restore test
- Database REINDEX
- Security scans
- Performance review

**Every Quarter (1st Saturday):**

- Full disaster recovery drill
- Penetration testing
- Infrastructure review

### 9.2 Maintenance Procedure

```bash
#!/bin/bash
# maintenance_window.sh

set -e

echo "=== MAINTENANCE WINDOW START ==="
date

# 1) Notify users (5 minutes before)
send_notification("Scheduled maintenance starting in 5 minutes. Brief downtime expected.")

# 2) Stop Celery workers (graceful)
docker-compose stop celery_worker celery_beat

# 3) Database maintenance
psql -h prod-db -U postgres aeterna -c "VACUUM aefine;"
psql -h prod-db -U postgres aeterna -c "ANALYZE;"

# 4) Reindex (if scheduled month)
if [ "$(date +%u)" = "7" ]; then  # First Sunday
    psql -h prod-db -U postgres aeterna -c "REINDEX DATABASE aeterna;"
fi

# 5) Restart services
docker-compose up -d

# 6) Wait for services to be ready
sleep 30
curl -f https://aeterna.app/health || exit 1

# 7) Verify
pytest tests/test_critical_paths.py -v

# 8) Notify users (done)
send_notification("✓ Maintenance completed. Services restored.")

echo "=== MAINTENANCE WINDOW END ==="
date
```

---

## 10. Operational Metrics & KPIs

### 10.1 System Health Metrics

| Metric                    | Target                            | Alert Threshold |
| ------------------------- | --------------------------------- | --------------- |
| Uptime                    | 99.9% (43 seconds downtime/month) | <99%            |
| Error Rate                | <0.5%                             | >5%             |
| P95 API Latency           | <2 seconds                        | >5 seconds      |
| Database Query Time (p95) | <500 ms                           | >2 seconds      |
| Event Processing Latency  | <10 seconds                       | >30 seconds     |
| Alert Delivery Success    | >99.5%                            | <95%            |
| CPU Usage                 | 40-60%                            | >85%            |
| Memory Usage              | 50-70%                            | >90%            |
| Disk Usage                | <70%                              | >85%            |

### 10.2 Business Metrics

| Metric                    | Target         | Frequency |
| ------------------------- | -------------- | --------- |
| Active Users (DAU)        | 500+ (month 3) | Daily     |
| Alert Quality (% useful)  | >80%           | Weekly    |
| User Retention (week 2)   | >50%           | Weekly    |
| Free→Paid Conversion      | 10%+           | Weekly    |
| Monthly Recurring Revenue | $1500+         | Monthly   |

### 10.3 Reporting

**Daily Report (Ops Team):**

- Uptime percentage
- Error rate % with top errors
- P95 latency
- Any incidents/warnings

**Weekly Report (Leadership):**

- Week-over-week metrics
- User growth
- Revenue
- Issues & resolutions

**Monthly Report (Executive Team):**

- System health summary
- KPI progress vs. targets
- Major incidents (root cause analysis)
- Infrastructure costs
- Planned improvements

---

## Conclusion

Successful operations require:

1. **Automation:** Scripts for common tasks
2. **Monitoring:** Know what's happening
3. **Alerting:** Act before users notice
4. **Runbooks:** Know how to respond
5. **Testing:** Verify before disaster strikes
6. **Communication:** Keep users & team informed
