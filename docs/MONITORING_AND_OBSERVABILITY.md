# AETERNA: Monitoring & Observability Guide

## Comprehensive Metrics, Alerting, Logging, and Visualization

**Document Version:** 1.0  
**Date:** March 2026  
**Stack:** Prometheus + Grafana + Loki + AlertManager  
**Status:** Production Ready  
**Last Updated:** March 25, 2026

---

## Table of Contents

1. Observability Philosophy
2. Metrics Collection Architecture
3. Key Metrics & Instrumentation
4. Alert Rules & Escalation
5. Dashboards & Visualization
6. Log Aggregation & Analysis
7. Distributed Tracing (Optional Phase II)
8. Runbooks & Alerts Integration
9. SLO/SLI Definitions
10. Monitoring Troubleshooting

---

## 1. Observability Philosophy

### 1.1 The Three Pillars

**Metrics:** Time-series data of system behavior

- Questions answered: "How many requests/second? What's CPU usage?"
- Tools: Prometheus, StatsD, Graphite

**Logs:** Detailed event records from applications

- Questions answered: "Why did this request fail? What was the error?"
- Tools: ELK Stack, Datadog, Loki

**Traces:** Request-level execution flow across services

- Questions answered: "Why is this query slow? Where's the bottleneck?"
- Tools: Jaeger, Zipkin, DataDog APM

**AETERNA Stack (MVP):**

- Metrics: Prometheus (free, time-series DB)
- Logs: Loki (lightweight, designed for Kubernetes)
- Traces: Structured logging (Phase II: add Jaeger)

---

## 2. Metrics Collection Architecture

### 2.1 Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                  METRIC SOURCES                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Application       Infrastructure      Custom           │
│  (FastAPI app)     (Docker stats)       (Business logic) │
│       │                  │                    │          │
│       └──────────────────┼────────────────────┘          │
│                          │                               │
│                          ▼                               │
│            ┌─────────────────────────┐                  │
│            │  Prometheus Exporters   │                  │
│            │  (Scrape endpoints)     │                  │
│            ├─────────────────────────┤                  │
│            │ /metrics (app)          │                  │
│            │ :9100/metrics (node)    │                  │
│            │ :9113/metrics (nginx)   │                  │
│            └────────────┬────────────┘                  │
│                         │                               │
│                         ▼                               │
│         ┌───────────────────────────┐                   │
│         │  Prometheus (Time-series) │                   │
│         │  (Stores metrics)         │                   │
│         │  15s scrape interval      │                   │
│         │  Storage: 15 days         │                   │
│         └────────────┬──────────────┘                   │
│                      │                                  │
│          ┌───────────┼───────────┐                     │
│          ▼           ▼           ▼                     │
│      ┌────────┐ ┌──────────┐ ┌────────┐              │
│      │Grafana │ │AlertMgr  │ │Loki    │              │
│      │Dashbrd │ │Alerts    │ │Logs    │              │
│      └────────┘ └──────────┘ └────────┘              │
│                                                        │
└──────────────────────────────────────────────────────┘
```

### 2.2 Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: "aeterna-prod"
    environment: "production"
    region: "us-east-1"

# Scrape targets (where to collect metrics from)
scrape_configs:
  - job_name: "aeterna-app"
    static_configs:
      - targets: ["localhost:8000"]
        labels:
          service: "api"

  - job_name: "aeterna-workers"
    static_configs:
      - targets: ["localhost:8001", "localhost:8002", "localhost:8003"]
        labels:
          service: "celery-worker"

  - job_name: "postgres"
    static_configs:
      - targets: ["localhost:9187"] # postgres_exporter
        labels:
          service: "database"

  - job_name: "redis"
    static_configs:
      - targets: ["localhost:9121"] # redis_exporter
        labels:
          service: "cache"

  - job_name: "rabbitmq"
    static_configs:
      - targets: ["localhost:15692"] # rabbitmq_exporter
        labels:
          service: "queue"

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          service: "prometheus"

# AlertManager integration
alerting:
  alertmanagers:
    - static_configs:
        - targets: ["localhost:9093"]

# Alert rules
rule_files:
  - "alerts/critical.yml"
  - "alerts/warnings.yml"
  - "alerts/info.yml"

# Remote storage (optional: backup metrics)
remote_write:
  - url: "https://remote-storage-endpoint.com/write"
    queue_config:
      max_shards: 100
```

---

## 3. Key Metrics & Instrumentation

### 3.1 Application Metrics (FastAPI)

**HTTP Request Metrics:**

```python
from prometheus_client import Counter, Histogram, Gauge
import time
from fastapi import Request

# Counter: Total requests
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

# Histogram: Request latency (buckets in seconds)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY
)

# Gauge: Active requests
http_requests_active = Gauge(
    'http_requests_active',
    'Active HTTP requests',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# Middleware to record metrics
@app.middleware("http")
async def record_request_metrics(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    # Increment active requests
    http_requests_active.labels(method=method, endpoint=endpoint).inc()

    start_time = time.time()
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as e:
        status = 500
        http_requests_active.labels(method=method, endpoint=endpoint).dec()
        raise

    # Record metrics
    duration = time.time() - start_time
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    # Decrement active requests
    http_requests_active.labels(method=method, endpoint=endpoint).dec()

    return response
```

**Business Logic Metrics:**

```python
# Counter: Events ingested
events_ingested_total = Counter(
    'events_ingested_total',
    'Total events ingested',
    ['source_type'],
    registry=REGISTRY
)

# Gauge: Queue depth
rabbitmq_queue_depth = Gauge(
    'rabbitmq_queue_depth',
    'RabbitMQ queue depth',
    ['queue_name'],
    registry=REGISTRY
)

# Counter: Alerts generated
alerts_generated_total = Counter(
    'alerts_generated_total',
    'Total alerts generated',
    ['priority'],
    registry=REGISTRY
)

# Counter: Alerts delivered
alerts_delivered_total = Counter(
    'alerts_delivered_total',
    'Total alerts delivered successfully',
    ['channel'],  # email, telegram, websocket
    registry=REGISTRY
)

# Histogram: Alert delivery latency
alert_delivery_latency_seconds = Histogram(
    'alert_delivery_latency_seconds',
    'Alert delivery latency',
    ['channel'],
    buckets=(0.5, 1, 2, 5, 10, 30, 60),
    registry=REGISTRY
)

# Usage in code
@app.post("/ingestion/receive")
async def receive_event(event_data):
    event = Event.create(event_data)

    # Record metric
    events_ingested_total.labels(source_type=event.source_type).inc()

    return {"status": "OK"}
```

**Error & Exception Metrics:**

```python
# Counter: Total errors
http_requests_error_total = Counter(
    'http_requests_error_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'error_type'],
    registry=REGISTRY
)

# Example: Catch and record database errors
try:
    result = db.query(User).filter_by(id=user_id).first()
except Exception as e:
    http_requests_error_total.labels(
        method='GET',
        endpoint='/api/user',
        error_type=type(e).__name__
    ).inc()
    raise
```

### 3.2 Database Metrics (PostgreSQL)

**Installed via postgresql_exporter:**

```
:9187/metrics provides:
- pg_stat_database_tup_fetched (rows read)
- pg_stat_database_tup_inserted (rows inserted)
- pg_stat_database_tup_updated (rows updated)
- pg_stat_database_tup_deleted (rows deleted)
- pg_connections (active connections)
- pg_cache_hit_ratio (% of queries served from cache)
- pg_lock_conflicts (contention)
- pg_slow_queries (>100ms queries)
```

### 3.3 Infrastructure Metrics

**Node Exporter (CPU, Memory, Disk):**

```
:9100/metrics provides:
- node_cpu_seconds_total (CPU time)
- node_memory_MemAvailable_bytes (free memory)
- node_disk_free_bytes (disk space)
- node_disk_io_reads_completed_total (I/O operations)
- node_network_receive_bytes_total (network throughput)
```

**Container Metrics (cAdvisor):**

```
Container CPU, Memory, Network, Disk I/O
- container_cpu_usage_seconds_total
- container_memory_working_set_bytes
- container_network_receive_bytes_total
```

---

## 4. Alert Rules & Escalation

### 4.1 Critical Alert Rules

**File: alerts/critical.yml**

```yaml
groups:
  - name: critical_alerts
    interval: 30s
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: rate(http_requests_error_total[5m]) > 0.05 # >5% errors
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High error rate ({{ $value | humanizePercentage }})"
          description: "Error rate on {{ $labels.instance }} exceeded 5% for 5 minutes"
          dashboard: "http://grafana/d/errors"
          runbook: "https://internal.wiki/runbook/high-error-rate"

      # Database Down
      - alert: DatabaseDown
        expr: pg_connections == bool 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down!"
          description: "PostgreSQL not responding for 1 minute"

      # Out of Memory
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage > 90% for 5 minutes"

      # Out of Disk
      - alert: DiskSpaceWarning
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space on {{ $labels.device }}"
          description: "{{ $value | humanizePercentage }} disk space remaining"

      # High Queue Backlog
      - alert: QueueBacklogHigh
        expr: rabbitmq_queue_messages_total > 50000
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "RabbitMQ queue backlog > 50K messages"
          description: "Queue: {{ $labels.queue_name }}, Count: {{ $value }}"
```

### 4.2 Warning Alert Rules

**File: alerts/warnings.yml**

```yaml
groups:
  - name: warning_alerts
    interval: 1m
    rules:
      # Slow API Response
      - alert: SlowAPIResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "API response time high (p95={{ $value }}s)"
          description: "95th percentile response time exceeds 2 seconds"

      # Slow Database Queries
      - alert: SlowDatabaseQueries
        expr: pg_stat_statements_mean_time > 1000 # >1000ms
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries detected"
          description: "Average query time: {{ $value }}ms"

      # High CPU Usage
      - alert: HighCPUUsage
        expr: rate(node_cpu_seconds_total[5m]) > 0.8 # >80%
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage > 80% for 15 minutes"

      # Cache Hit Rate Low
      - alert: LowCacheHitRate
        expr: pg_cache_hit_ratio < 0.8 # <80%
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low database cache hit rate"
          description: "Cache hit ratio: {{ $value | humanizePercentage }}"

      # Alert Delivery Backlog
      - alert: AlertDeliveryBacklog
        expr: increase(alerts_pending[5m]) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alert delivery backlog building"
          description: "{{ $value }} alerts pending delivery"
```

### 4.3 Informational Alerts

**File: alerts/info.yml**

```yaml
groups:
  - name: info_alerts
    interval: 5m
    rules:
      # Deployment Completed
      - alert: DeploymentCompleted
        expr: changes(app_version[1m]) > 0
        labels:
          severity: info
        annotations:
          summary: "Application deployed"
          description: "Version changed to {{ $value }}"

      # Daily Backup Completed
      - alert: DailyBackupCompleted
        expr: increase(database_backups_total[1d]) > 0
        labels:
          severity: info
        annotations:
          summary: "Daily backup completed successfully"
```

### 4.4 AlertManager Routing & Escalation

**File: alertmanager.yml**

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  pagerduty_url: "https://events.pagerduty.com/v2/enqueue"

# Routing tree: how alerts route to receivers
route:
  receiver: "default"
  group_by: ["alertname", "cluster", "service"]
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 12h

  routes:
    # Critical alerts → page everyone immediately
    - match:
        severity: critical
      receiver: "pagerduty"
      group_wait: 0s # No waiting, page immediately
      repeat_interval: 5m # Re-page every 5 min if unresolved
      continue: true

    # Warnings → Slack (no page)
    - match:
        severity: warning
      receiver: "slack-warnings"
      group_wait: 5m # Wait 5 min to batch warnings
      repeat_interval: 1h # Re-notify hourly

    # Info → Log only
    - match:
        severity: info
      receiver: "null" # Don't notify, just log

# Receivers: where alerts go
receivers:
  - name: "default"
    slack_configs:
      - channel: "#alerts"
        title: "Alert"

  - name: "pagerduty"
    slack_configs:
      - channel: "#critical-alerts"
        title: "🚨 CRITICAL 🚨"
    pagerduty_configs:
      - service_key: "YOUR_PAGERDUTY_KEY"

  - name: "slack-warnings"
    slack_configs:
      - channel: "#warnings"
        title: "⚠️ Warning"

  - name: "null"

# Silence rules
inhibit_rules:
  # Don't page for warnings if critical alert exists
  - source_match:
      severity: "critical"
    target_match:
      severity: "warning"
    equal: ["alertname", "instance"]
```

---

## 5. Dashboards & Visualization

### 5.1 Main Production Dashboard

**Grafana Dashboard: `Production Overview`**

```
Row 1: System Health
├─ Uptime %  (big number: target >99.9%)
├─ Request Rate (graph: last 24h)
├─ Error Rate % (graph: should be <1%)
└─ P95 Latency (graph: should be <2s)

Row 2: Application Performance
├─ Active Requests (gauge)
├─ API Latency Distribution (percentiles: p50, p95, p99)
├─ Errors by Type (pie chart)
└─ Events Processed (counter: events/sec)

Row 3: Infrastructure
├─ CPU Usage (% over time)
├─ Memory Usage (% over time)
├─ Disk I/O (bytes/sec)
└─ Network Throughput (bytes/sec)

Row 4: Database Performance
├─ Query Latency p95 (should be <500ms)
├─ Connections (current/max)
├─ Cache Hit Rate % (should be >80%)
└─ Slow Queries (count)

Row 5: Business Metrics
├─ Events Ingested (per minute)
├─ Alerts Generated (per minute)
├─ Alerts Delivered (per minute)
└─ Delivery Success Rate % (target >99%)
```

**Panel Queries (PromQL):**

```
# Uptime percentage (last 30 days)
rate(up{service="api"}[30d]) * 100

# Request rate
sum(rate(http_requests_total[5m]))

# Error rate %
sum(rate(http_requests_error_total[5m])) / sum(rate(http_requests_total[5m])) * 100

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# CPU usage
rate(node_cpu_seconds_total[5m]) * 100

# Cache hit ratio
pg_cache_hit_ratio * 100
```

### 5.2 Service-Specific Dashboards

**API Service Dashboard:**

- Response time by endpoint
- Error rate by endpoint
- Top slow endpoints
- Request volume by method (GET/POST/etc)

**Database Dashboard:**

- Query latency histogram
- Connection pool utilization
- Cache hit rate
- Disk I/O
- Slow queries (top 10)
- Table sizes

**Alert Delivery Dashboard:**

- Alerts pending vs delivered
- Delivery latency by channel (email, Telegram)
- Success/failure rates per channel
- Retry attempts

---

## 6. Log Aggregation & Analysis

### 6.1 Structured Logging Format

**Application Logs (JSON):**

```python
import logging
import json
from pythonjsonlogger import jsonlogger

# Setup structured logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Usage
logger.info("User logged in", extra={
    "user_id": 123,
    "ip_address": "192.168.1.1",
    "session_id": "abc123",
    "duration_ms": 45
})

# Output (sent to Loki)
{
  "timestamp": "2026-03-25T10:30:00Z",
  "level": "INFO",
  "message": "User logged in",
  "user_id": 123,
  "ip_address": "192.168.1.1",
  "session_id": "abc123",
  "duration_ms": 45,
  "service": "aeterna-api",
  "environment": "production"
}
```

### 6.2 Loki Configuration (Log Aggregation)

```yaml
# loki-config.yml
auth_enabled: false

ingester:
  chunk_idle_period: 3m
  chunk_retain_period: 1m
  max_chunk_age: 1h
  max_streams_matcher_size: 10000

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

server:
  http_listen_port: 3100

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

# Label parsing (extract fields from logs)
pipeline_stages:
  - json:
      expressions:
        level: level
        message: message
        user_id: user_id
        error_type: error_type

  - labels:
      level:
      message:
      user_id:
      error_type:
```

### 6.3 Log Queries & Analysis

**Loki PromQL Examples:**

```
# Count of ERROR logs in last hour
count_over_time({level="ERROR"}[1h])

# Error rate (errors / total logs)
count_over_time({level="ERROR"}[5m]) / count_over_time({job="api"}[5m])

# Find errors by type
{level="ERROR"} | regexp "error_type=(?P<error_type>\w+)"

# Database slow query logs
{service="postgres"} | json | duration_ms > 1000

# Failed login attempts
{message="User login failed"} | json | user_id != ""
```

---

## 7. Distributed Tracing (Phase II)

### 7.1 Why Tracing?

**Metrics tell you something is wrong, traces tell you why.**

Example:

- Metric: API latency p95 = 5 seconds (HIGH!)
- Question: Which service is slow?
- Trace: Request flow visualization showing which service took 4.9 seconds

### 7.2 Jaeger Setup (Phase II)

```yaml
# docker-compose addition (Phase II)
jaeger:
  image: jaegertracing/all-in-one:latest
  ports:
    - "6831:6831/udp" # Jaeger agent
    - "16686:16686" # Jaeger UI
```

**Instrumentation (FastAPI):**

```python
from jaeger_client import Config
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracer
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

tracer = trace.get_tracer(__name__)

# Instrument endpoint
@app.post("/api/events")
async def create_event(event_data):
    with tracer.start_as_current_span("create_event") as span:
        span.set_attribute("event.source", event_data.source)

        # Your code here
        with tracer.start_as_current_span("validate_event"):
            validate(event_data)

        with tracer.start_as_current_span("save_to_db"):
            event = db.create(event_data)

        return {"id": event.id}
```

---

## 8. SLO/SLI Definitions

### 8.1 Service-Level Objectives (SLOs)

| SLO             | Target | Current | Status   |
| --------------- | ------ | ------- | -------- |
| Uptime          | 99.9%  | 99.95%  | ✅ GREEN |
| Error Rate      | <1%    | 0.2%    | ✅ GREEN |
| API Latency p95 | <2s    | 1.2s    | ✅ GREEN |
| Alert Delivery  | >99%   | 99.8%   | ✅ GREEN |

### 8.2 Error Budget

**Monthly error budget calculation:**

```
SLO Target: 99.9% uptime
Days per month: 30
Acceptable downtime: 30 days * (1 - 0.999) = 0.03 days = 43 seconds/month

If actual: 99.85% (50 seconds down)
Budget used: 50 / 43 = 116% (EXCEEDED)

Action: Increase monitoring, reduce change velocity, add redundancy
```

---

## 9. Monitoring Troubleshooting

### 9.1 Common Issues & Solutions

**Issue 1: Metrics Not Appearing**

```bash
# 1) Check if Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# 2) Check exporter is up
curl http://localhost:8000/metrics

# 3) Check Prometheus config
promtool check config /etc/prometheus/prometheus.yml

# 4) Restart Prometheus
docker restart prometheus
```

**Issue 2: Alerts Not Firing**

```bash
# 1) Check alert rules syntax
promtool check rules /etc/prometheus/alerts/*.yml

# 2) Check if alert expression evaluates
# Visit: http://prometheus:9090/graph
# Enter expression: rate(http_requests_error_total[5m])

# 3) Test AlertManager routing
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "critical"},
    "annotations": {"summary": "Test"}
  }]'
```

**Issue 3: High Memory Usage of Prometheus**

```bash
# Reduce retention period
# In prometheus.yml:
# --storage.tsdb.retention.time=7d  # Default: 15d

# Reduce scrape interval (trade-off: less granularity)
# In prometheus.yml:
# global.scrape_interval: 30s  # Default: 15s
```

---

## 10. Operational Checklist

### 10.1 Daily Monitoring Tasks

- [ ] Check dashboard for anomalies
- [ ] Review critical alerts (any overnight?)
- [ ] Check error rate < 1%
- [ ] Verify backup job completed
- [ ] Review slow queries log

### 10.2 Weekly Monitoring Tasks

- [ ] Review SLO/SLI metrics vs targets
- [ ] Check alert coverage (are all issues being caught?)
- [ ] Review top 10 slowest endpoints
- [ ] Capacity planning (growth trending?)
- [ ] Update runbooks if needed

### 10.3 Monthly Monitoring Tasks

- [ ] Full month SLO report
- [ ] Review and tune alert thresholds
- [ ] Database vacuum & analyze
- [ ] Metrics storage cleanup (old data)
- [ ] Disaster recovery drill

---

## Conclusion

Effective monitoring requires:

1. **Comprehensive instrumentation** (metrics collection)
2. **Smart alerting** (alert on SLO breaches, not noise)
3. **Actionable dashboards** (quick visibility)
4. **Detailed logs** (for investigations)
5. **Runbooks** (faster resolution)

This setup enables rapid incident response and continuous improvement!
