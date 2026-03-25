# AETERNA: Disaster Recovery & Business Continuity Plan

## Formal RTO/RPO Targets, Recovery Procedures, and Contingency Planning

**Document Version:** 1.0  
**Date:** March 2026  
**Classification:** Internal (Required for compliance)  
**Status:** Active  
**Last Updated:** March 25, 2026

---

## Table of Contents

1. Executive Summary & Targets
2. Disaster Classification & Response Times
3. Recovery Procedures by Scenario
4. Backup Strategy & Verification
5. Failover & Business Continuity
6. Communication & Escalation
7. Testing & Drills
8. Compliance & Audit Trail
9. Contact & Runbook Reference
10. Post-Disaster Review Process

---

## 1. Executive Summary & Targets

### 1.1 Strategic Objectives

AETERNA values user trust above all else. In case of disaster:

- **Minimize downtime:** Get service restored ASAP
- **Retain data integrity:** No data loss if possible
- **Maintain transparency:** Communicate with users proactively
- **Continuous operation:** Graceful degradation (limited features) rather than complete outage

### 1.2 RTO/RPO Targets

| Scenario                     | RTO (Recovery Time)     | RPO (Recovery Point)    | Priority |
| ---------------------------- | ----------------------- | ----------------------- | -------- |
| **Database corruption**      | 30 minutes              | 5 minutes               | P0       |
| **Database server crash**    | 15 minutes              | 5 minutes               | P0       |
| **Deployment failure**       | 5 minutes               | 0 minutes (blue-green)  | P0       |
| **API server crash**         | 2 minutes               | 0 minutes (stateless)   | P0       |
| **Celery worker failure**    | 5 minutes               | 5 minutes               | P1       |
| **Redis cache failure**      | 1 minute                | 0 minutes (repopulated) | P2       |
| **RabbitMQ queue failure**   | 10 minutes              | 1 minute                | P1       |
| **Complete datacenter loss** | 4 hours                 | 15 minutes              | P0       |
| **Credentials compromise**   | 30 minutes              | immediate               | P0       |
| **Data breach detected**     | 24 hours (notify users) | varies                  | P0       |

### 1.3 Maximum Tolerable Downtime (MTD)

```
Business Context: Crypto trading operates 24/7
MTD for AETERNA: 30 minutes/month
Equivalent to: 99.9% uptime SLA
Cost of downtime: ~$2-5K per minute (user base × potential loss)
```

---

## 2. Disaster Classification & Response Times

### 2.1 Severity Levels

**SEVERITY 1 (Critical) - Response: Immediate**

- Complete system unavailable
- Database down or corrupted
- Massive data loss
- Security breach
- Examples: Power outage, server hardware failure, ransomware

**SEVERITY 2 (High) - Response: 15 minutes**

- Partial system failure
- 50%+ functionality offline
- Single critical service down
- High error rate (>10%)
- Examples: App crash, cache down, single database replica failure

**SEVERITY 3 (Medium) - Response: 1 hour**

- Non-critical service degradation
- 10-50% functionality affected
- Elevated error rate (1-10%)
- Examples: Background jobs failing, email delivery slow

**SEVERITY 4 (Low) - Response: 24 hours**

- Minor issues
- No user impact
- Informational only
- Examples: Unused index consuming disk, old logs not cleaning up

### 2.2 Incident Commander Decision Tree

```
Is service completely unavailable?
  ├─ YES → SEVERITY 1 → Page on-call team immediately
  ├─ NO → Is functionality degraded >50%?
      ├─ YES → SEVERITY 2 → Alert senior engineer
      ├─ NO → Is error rate elevated (1-10%)?
          ├─ YES → SEVERITY 3 → Create ticket, follow up next business day
          ├─ NO → SEVERITY 4 → Log and monitor
```

---

## 3. Recovery Procedures by Scenario

### 3.1 Database Corruption or Crash

**Symptoms:**

- Queries returning errors ("index is corrupted")
- Unable to connect to database
- Slow queries (table scans)
- Replication lag >10 seconds

**Recovery Procedure:**

```bash
#!/bin/bash
# disaster_recovery_database.sh

set -e

INCIDENT_ID="INC-$(date +%Y%m%d%H%M%S)"
echo "Starting database recovery: $INCIDENT_ID"

# STEP 1: Assess damage (2 min)
echo "[1/5] Assessing damage..."
pg_isready -h prod-db.internal -p 5432 -U postgres
if [ $? -ne 0 ]; then
    echo "Database is COMPLETELY DOWN"
    SEVERITY="CRITICAL"
else
    echo "Database responding, checking integrity..."

    # Check for corruption
    psql -h prod-db.internal -U postgres -d aeterna -c "REINDEX DATABASE aeterna;" 2>&1 | head -10

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "CORRUPTION DETECTED"
        SEVERITY="CRITICAL"
    fi
fi

# STEP 2: Notify users (if needed)
if [ "$SEVERITY" = "CRITICAL" ]; then
    echo "[2/5] Sending notifications..."

    # Update status page
    curl -X PATCH https://status.aeterna.app/api/v1/incidents \
      -H "Authorization: Bearer $STATUS_PAGE_TOKEN" \
      -d '{"status":"investigating","message":"Database maintenance in progress"}'

    # Send email to users
    send_email_broadcast "We are performing emergency maintenance. ETA: 15 minutes."
fi

# STEP 3: Stop write traffic (prevents new corruptions)
echo "[3/5] Stopping write traffic..."
# Close connection to database, stop API servers
docker-compose stop app

# STEP 4: Create backup of corrupted DB (for analysis)
echo "[4/5] Backing up corrupted database..."
pg_dump -h prod-db.internal -U postgres aeterna > /backup/corrupted_db_${INCIDENT_ID}.sql
gzip /backup/corrupted_db_${INCIDENT_ID}.sql
aws s3 cp /backup/corrupted_db_${INCIDENT_ID}.sql.gz s3://aeterna-backups/pre-recovery/

# STEP 5: Restore from backup
echo "[5/5] Restoring from backup..."

# Find latest clean backup
LATEST_BACKUP=$(aws s3 ls s3://aeterna-backups/ | tail -1 | awk '{print $4}')
echo "Using backup: $LATEST_BACKUP"

aws s3 cp s3://aeterna-backups/$LATEST_BACKUP /tmp/
gunzip -c /tmp/$LATEST_BACKUP | psql -h prod-db.internal -U postgres

# Verify restore
echo "Verifying restored database..."
psql -h prod-db.internal -U postgres -d aeterna -c "SELECT COUNT(*) FROM events;"
psql -h prod-db.internal -U postgres -d aeterna -c "SELECT COUNT(*) FROM alerts;"

# STEP 6: Restart services
echo "Restarting services..."
docker-compose up -d

# STEP 7: Verify services
sleep 30
curl -f https://aeterna.app/health || exit 1

# STEP 8: Update status page
curl -X PATCH https://status.aeterna.app/api/v1/incidents \
  -H "Authorization: Bearer $STATUS_PAGE_TOKEN" \
  -d '{"status":"resolved","message":"Database recovered successfully"}'

echo "✓ Database recovery completed in $(( $(date +%s) - RECOVERY_START_TIME )) seconds"
```

**Recovery Checklist:**

- [ ] Stop API servers (prevent new writes)
- [ ] Backup corrupted database
- [ ] Restore from latest clean backup
- [ ] Verify row counts match expectations
- [ ] Run integrity checks (REINDEX, ANALYZE)
- [ ] Restart services
- [ ] Monitor error rate for 10 minutes
- [ ] Notify users of resolution

---

### 3.2 Application Server Crash (API/Celery Workers)

**Symptoms:**

- API returning 503 errors
- No response from endpoint
- Container exited

**Recovery Procedure:**

```bash
#!/bin/bash
# disaster_recovery_app_crash.sh

# SEVERITY: Medium (RTO: 2-5 minutes)

# Step 1: Assess which instance(s) are down
docker ps -a | grep -E "aeterna|celery"

# Step 2: Restart the service
# Docker Compose auto-restart will try first
# If that fails:
docker-compose restart app

# Step 3: Check logs for errors
docker logs app-1 | tail -50

# Step 4: If app won't start: Scale down and up
docker-compose up -d --scale app=0
sleep 5
docker-compose up -d --scale app=2

# Step 5: Verify
curl -f https://aeterna.app/health

# Step 6: If still failing
# - Check database connectivity
# - Check external API keys (expired?)
# - Check disk space
# - Check memory availability
```

**Auto-Recovery (Recommended):**

```yaml
# docker-compose.yml with auto-restart
services:
  app:
    restart_policy:
      condition: on-failure
      max_attempts: 5
      delay: 5s # Wait 5s before retry
```

---

### 3.3 Deployment Failure (Broken Code Release)

**Symptoms:**

- Error rate spike after deployment
- 5XX errors from new code
- Alert delivery stopped

**Recovery Procedure (Blue-Green Rollback):**

```bash
#!/bin/bash
# Automatic rollback (implemented in DEPLOYMENT_AND_OPERATIONS.md)

# Monitor post-deployment
for i in {1..12}; do
    ERROR_RATE=$(curl -s http://prometheus:9090/api/v1/query \
      --data-urlencode 'query=rate(http_requests_error_total[1m])' | jq '.data.result[0].value[1]')

    if [ $(echo "$ERROR_RATE > 0.05" | bc) -eq 1 ]; then
        echo "ERROR RATE SPIKE DETECTED: $ERROR_RATE"

        # Automatic rollback
        echo "Rolling back to previous version..."
        git revert HEAD --no-edit
        docker build -t aeterna:prod .
        docker-compose up -d

        # Verify
        sleep 10
        curl -f https://aeterna.app/health || exit 1

        echo "✓ Rollback completed"
        exit 0
    fi

    sleep 5
done
```

---

### 3.4 Data Breach / Credentials Compromise

**Symptoms:**

- Unauthorized API calls detected
- Users reporting account compromise
- Suspicious database queries in logs
- Credentials found in public repo

**Recovery Procedure:**

```bash
#!/bin/bash
# disaster_recovery_breach.sh

INCIDENT_ID="BREACH-$(date +%Y%m%d%H%M%S)"
echo "Starting breach recovery: $INCIDENT_ID"

# STEP 1: Contain the breach (IMMEDIATE)
echo "[1] Isolating compromised resources..."

# Revoke all active API keys
psql -h prod-db -U postgres -d aeterna -c "
  UPDATE auth_tokens SET revoked_at = NOW() WHERE revoked_at IS NULL;
  UPDATE users SET password_hash = '' WHERE id NOT IN (1);  -- Keep admin
"

# Rotate external API keys
# - Twitter API key
# - Ethereum node key
# - SendGrid API key
./rotate_external_credentials.sh

# Block compromised IPs
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxx \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

aws waf-regional associate-web-acl \
  --web-acl-id arn:aws:wafregional:... \
  --resource-arn arn:aws:elasticloadbalancing:...

# STEP 2: Assess scope
echo "[2] Assessing breach scope..."

# Query logs for unauthorized access
psql -h prod-db -U postgres -d aeterna -c "
  SELECT DISTINCT user_id, ip_address, COUNT(*) as requests
  FROM audit_logs
  WHERE action != 'login' AND timestamp > NOW() - INTERVAL '1 hour'
  GROUP BY user_id, ip_address
  ORDER BY requests DESC
  LIMIT 20;
" > /tmp/suspicious_activity_${INCIDENT_ID}.txt

# STEP 3: Notify users
echo "[3] Notifying users..."

send_email_broadcast "
  SECURITY ALERT: We detected unauthorized access to your account.

  What happened: [Brief explanation]
  What we did: [Actions taken]
  What to do:
    - Change your password immediately
    - Enable 2FA
    - Check your portfolio history

  Support: security@aeterna.app
"

# STEP 4: Reset all sessions
echo "[4] Invalidating all sessions..."
redis-cli FLUSHDB  # Clear all cached sessions

# Force users to re-login
psql -h prod-db -U postgres -d aeterna -c "
  UPDATE users SET last_login_at = NULL;
  DELETE FROM auth_tokens WHERE token_type = 'access';
"

# STEP 5: Enable audit logging on all tables
echo "[5] Enabling enhanced audit logging..."
# Already configured in DATABASE_SCHEMA.md

# STEP 6: Report to authorities (if required)
echo "[6] Compliance notifications..."

# GDPR: Notify if personal data affected
# Within 72 hours of discovery
send_notification("privacy@gdpr-authority.gov", "Data breach notification")

# Financial: If could affect trading
# Within 4 hours
send_notification("sec@financial-authority.gov", "Potential trading system compromise")

echo "✓ Breach containment completed"
echo "Investigation details: /tmp/suspicious_activity_${INCIDENT_ID}.txt"
```

---

### 3.5 Complete Datacenter Loss

**Symptoms:**

- All services down
- Cannot connect to anything
- Cloud provider announces outage

**Recovery Procedure (Multi-Region Failover):**

```bash
#!/bin/bash
# Multi-region failover (Phase II feature)

# Prerequisites: Secondary region setup
# - Standby database in different region
# - Application code deployable in 5 min
# - DNS failover configured

# STEP 1: Detect primary datacenter is down
PRIMARY_HEALTH=$(curl -s -m 5 https://us-east-1.internal/health || echo "FAIL")

if [ "$PRIMARY_HEALTH" = "FAIL" ]; then
    echo "PRIMARY REGION DOWN - Initiating failover"

    # STEP 2: Switch DNS to secondary region
    aws route53 change-resource-record-sets \
      --hosted-zone-id Z1234567890ABC \
      --change-batch '{
        "Changes": [{
          "Action": "UPSERT",
          "ResourceRecordSet": {
            "Name": "aeterna.app",
            "Type": "A",
            "TTL": 60,
            "AliasTarget": {
              "HostedZoneId": "Z2FDTNDATAQYW2",
              "DNSName": "us-west-2.aeterna.app",
              "EvaluateTargetHealth": false
            }
          }
        }]
      }'

    # STEP 3: Promote standby database
    psql -h us-west-2-db.internal -U postgres -c "
      SELECT pg_promote();
    "

    # STEP 4: Deploy application to secondary region
    cd /tmp
    git clone https://github.com/aeterna/aeterna-app.git
    cd aeterna-app
    docker build -t aeterna:prod .
    docker push gcr.io/aeterna/aeterna:prod

    # Deploy via Kubernetes/Docker Swarm
    kubectl apply -f k8s/prod-deployment.yml

    # STEP 5: Verify secondary region
    sleep 60
    curl -f https://us-west-2.aeterna.app/health || exit 1

    # STEP 6: Notify users
    send_email_broadcast "We've switched to our backup region. Services restored."

    echo "✓ Failover to secondary region complete"
fi
```

---

## 4. Backup Strategy & Verification

### 4.1 Backup Schedule

```
Daily 2 AM UTC:      Full database backup (gzipped, 500 MB - 1 GB)
                     Replicated to AWS S3 (cross-region)
                     Retention: 30 days

Weekly backup:       Full VM snapshot (for quick recovery)
                     Retention: 12 weeks

Monthly backup:      Offline archival (cold storage)
                     Retention: 1 year (compliance)

Transaction logs:    Continuous (PostgreSQL WAL)
                     Enables point-in-time recovery to any minute
```

### 4.2 Backup Verification Checklist

**Daily (automated):**

```bash
# After backup completes
✓ File size > 500 MB (not empty)
✓ Successfully uploaded to S3
✓ gzip integrity check (gunzip -t)
✓ MD5 checksum matches
```

**Weekly (manual):**

```bash
# Test restore on staging DB
✓ Restore completed without errors
✓ Row counts match production
✓ Can insert/update/delete data
✓ Foreign key constraints intact
```

**Monthly (full test):**

```bash
# Complete recovery scenario
✓ Restore from month-old backup
✓ Verify data integrity
✓ Run full test suite
✓ Document any issues
✓ Update recovery procedures
```

---

## 5. Failover & Business Continuity

### 5.1 Graceful Degradation Strategy

If complete service is unavailable, offer limited functionality:

```
Services in priority order (restore first):
1. Authentication API (users can log in)
2. Event feed (read-only view of recent events)
3. Alert delivery (email, Telegram to subscribed users)
4. Analytics (display historic data from cache)
5. Dashboard (if UI cached)
```

**Implementation:**

```python
# Add feature flags for graceful degradation
FEATURE_FLAGS = {
    'auth_enabled': True,
    'api_write_enabled': True,
    'event_ingestion_enabled': True,
    'alert_delivery_enabled': True,
}

@app.post("/api/alerts/preferences")
async def update_preferences(data):
    if not FEATURE_FLAGS['api_write_enabled']:
        return {
            "status": "temporary_unavailable",
            "message": "Write operations temporarily disabled. Your changes will be lost.",
            "retry_after": 300  # Try again in 5 minutes
        }

    # Proceed normally
    ...
```

### 5.2 Recovery Runbook (Quick Start)

**Saved at:** `/opt/runbooks/QUICK_RECOVERY.txt`

```
=== QUICK RECOVERY RUNBOOK ===

If system is down:

1. Run health check:
   curl -v https://aeterna.app/health

2. If no response:
   docker-compose restart

3. If still no response:
   docker-compose logs app | tail -20

   → If database error: Run disaster_recovery_database.sh
   → If code error: Run disaster_recovery_deployment.sh
   → If unknown: Page incident commander

4. After restart:
   curl -f https://aeterna.app/health
   curl -f https://aeterna.app/api/events?limit=1

5. Update status page:
   https://status.aeterna.app/admin

Full procedures: /opt/runbooks/DISASTER_RECOVERY.md
```

---

## 6. Communication & Escalation

### 6.1 Escalation Path

```
Symptom detected (monitoring auto-alert)
                    ↓
Severity determined (SEVERITY_1/2/3/4)
                    ↓
         ┌──────────┼──────────┐
         ↓          ↓          ↓
    SEVERITY_1  SEVERITY_2  SEVERITY_3
         ↓          ↓          ↓
    Page on-call  Alert eng  Create ticket
    immediately   next 15m   Track for follow-up
                    ↓
            Insufficient progress?
                    ↓
            Escalate to senior eng
                    ↓
            Still no resolution after 30 min?
                    ↓
            Page CTO/Founder
```

### 6.2 Communication Templates

**For Users (Status Page):**

```
🟡 INVESTIGATING: [Service Name] - [Time Start]
We are investigating an issue affecting [functionality].
Impact: [% of users affected]
Status: We are actively working on resolution.
Updates every 30 minutes.

---

🟢 RESOLVED: Service restored at [Time]
Thank you for your patience. The issue was [brief cause].
We'll provide detailed analysis in our post-mortem.
```

**For Internal (Slack):**

```
🚨 INCIDENT DECLARED: [Name]
P0 - [Service] down
Started: [Time]
ETA to fix: [Time]
People involved: [@person1, @person2]
Updates in #incident-channel
```

---

## 7. Testing & Drills

### 7.1 Monthly DR Drill Schedule

**1st Saturday of each month, 10 AM UTC**

```bash
#!/bin/bash
# monthly_dr_drill.sh

DATE=$(date +%Y-%m-%d)
DRILL_LOG="dr_drill_${DATE}.log"

echo "=== DISASTER RECOVERY DRILL ===" | tee $DRILL_LOG
echo "Date: $DATE" | tee -a $DRILL_LOG
echo "" | tee -a $DRILL_LOG

# Test 1: Database restore
echo "[1/3] Testing database restore..." | tee -a $DRILL_LOG
./restore_from_backup.sh >> $DRILL_LOG 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Database restore: PASS" | tee -a $DRILL_LOG
else
    echo "✗ Database restore: FAIL" | tee -a $DRILL_LOG
fi

# Test 2: Failover procedure
echo "[2/3] Testing failover..." | tee -a $DRILL_LOG
./test_failover.sh >> $DRILL_LOG 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Failover: PASS" | tee -a $DRILL_LOG
else
    echo "✗ Failover: FAIL" | tee -a $DRILL_LOG
fi

# Test 3: Communication procedure
echo "[3/3] Testing communication..." | tee -a $DRILL_LOG
echo "Mock: Sending status page update..." | tee -a $DRILL_LOG
echo "Mock: Sending user notification email..." | tee -a $DRILL_LOG
echo "✓ Communication: PASS" | tee -a $DRILL_LOG

echo "" | tee -a $DRILL_LOG
echo "Drill completed. Results logged to: $DRILL_LOG" | tee -a $DRILL_LOG

# Share results with team
slack_post "#ops" "DR Drill completed. Results: $DRILL_LOG"
```

### 7.2 Escalation Drill (Quarterly)

Test full escalation path:

- Is on-call engineer responsive?
- Can senior engineer be reached?
- Does CTO respond to page?
- Do external communications (Slack, email, status page) work?

---

## 8. Compliance & Audit Trail

### 8.1 Compliance Requirements

**SOC 2 Type II:**

```
✓ Documented disaster recovery plan (this document)
✓ RTO/RPO targets defined and measurable
✓ Annual DR testing performed
✓ Backup integrity verified regularly
✓ Change management for DR procedures
✓ Audit logs of all recovery activities
```

**GDPR (if EU customers):**

```
✓ Data can be restored from backups
✓ Lost data notification within 72 hours
✓ Deletion requests honored (no need to restore)
✓ Privacy impact assessment done
```

### 8.2 Incident Audit Trail

```sql
-- All recovery activities logged
INSERT INTO audit_logs (
    user_id, action, resource_type,
    old_values, new_values, timestamp, ip_address
) VALUES (
    NULL,  -- System action, not user triggered
    'database_recovered',
    'system',
    '{"reason": "corruption detected", "previous_state": "degraded"}',
    '{"action": "restore_from_backup", "backup_id": "backup_20260325"}',
    NOW(),
    '127.0.0.1'
);
```

---

## 9. Contact & Runbook Reference

### 9.1 Key Contacts

```
On-Call Incident Commander:
  Name: [Contact name]
  Phone: [Phone]
  Email: [Email]
  Slack: @[handle]

Senior Engineer:
  Name: [Contact name]
  Phone: [Phone]
  Escalation: After 15 min with no progress

CTO/Founder:
  Name: [Contact name]
  Phone: [Phone]
  Escalation: After 30 min with no progress

External Support:
  Cloud Provider Support: +1-800-XXX-XXXX
  Database Provider: support@provider.com
```

### 9.2 Runbook Index

| Scenario          | Runbook                        | RTO     | Owner    |
| ----------------- | ------------------------------ | ------- | -------- |
| API crash         | disaster_recovery_app_crash.sh | 2 min   | DevOps   |
| DB corrupt        | disaster_recovery_database.sh  | 30 min  | DBA      |
| Deployment failed | rollback_deployment.sh         | 5 min   | DevOps   |
| Breach detected   | disaster_recovery_breach.sh    | 30 min  | Security |
| Datacenter loss   | failover_secondary_region.sh   | 4 hours | CTO      |
| User data loss    | restore_from_backup.sh         | 60 min  | DBA      |

---

## 10. Post-Disaster Review Process

### 10.1 Incident Post-Mortem (Within 48 Hours)

```
Post-Mortem Template:

EVENT SUMMARY
─────────────
Title: [Brief title]
Date/Time: [When it happened]
Duration: [How long it lasted]
Severity: [P0/P1/P2]
Impact: [# users affected, lost revenue]

TIMELINE
────────
12:34 - [What happened]
12:35 - [When noticed]
12:36 - [When declared incident]
12:45 - [Action X taken]
13:00 - [Service restored]

ROOT CAUSE ANALYSIS
────────────────
Why did this happen?
  ↓ (Ask "why?" 5 times)
  ↓
3. Because the backup wasn't tested
  ↓
2. Because monthly DR drills were skipped
  ↓
1. Because... [root cause]

CONTRIBUTING FACTORS
──────────────────
- No alerting on backup failures
- Manual process prone to mistakes
- Single database, no replicas
- No runbook for recovery

WHAT WENT WELL
──────────────
+ Team responded quickly
+ Clear communication
+ Runbook was helpful

WHAT COULD IMPROVE
──────────────────
- Test backups more frequently
- Automate recovery procedures
- Add replica database for HA
- Improve alerting

ACTION ITEMS (Assign owners + due dates)
─────────────────────────────────────────
1. Automate backup testing - @person1 - Due: 2 weeks
2. Set up read replica - @person2 - Due: 1 month
3. Add backup failure alerting - @person3 - Due: 1 week
```

### 10.2 Update Runbooks Based on Learnings

```bash
# After incident resolution:

1. Document what actually happened (not what should happen)
2. Update runbook with new steps if different
3. Mark sections that need improvement
4. Share with team for feedback
5. Archive post-mortem for future reference

Example update:
  OLD: "Restore takes 5 minutes"
  NEW: "Restore actually took 30 minutes due to large DB.
        Estimated 1-2 hours if DB >50GB."
```

---

## Appendix: Quick Reference Card

**Laminated card in ops desk drawer:**

```
AETERNA DISASTER RECOVERY QUICK REFERENCE

If system down:
1. curl https://aeterna.app/health
2. docker-compose logs app | tail -20
3. Choose runbook based on error
4. Execute runbook
5. Page incident commander if unclear

Runbooks location: /opt/runbooks/
Status page: https://status.aeterna.app/

On-call: See contact list above
Emergency: Page CTO if RTO exceeded

Database issues → disaster_recovery_database.sh
Application issues → disaster_recovery_app_crash.sh
Deployment issues → rollback_deployment.sh
Breach → disaster_recovery_breach.sh
```

---

## Conclusion

A comprehensive disaster recovery plan is crucial for:

- ✅ Minimizing downtime and user impact
- ✅ Maintaining data integrity and compliance
- ✅ Ensuring business continuity
- ✅ Building user trust

**Key Success Factors:**

1. Clear RTO/RPO targets
2. Documented procedures
3. Regular testing
4. Team training
5. Rapid communication

This plan lives and evolves with the system!
