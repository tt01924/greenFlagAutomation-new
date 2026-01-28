# Green Flag Automation - Operational Runbook

This runbook provides step-by-step procedures for common operational tasks, debugging, and incident response.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring & Alerts](#monitoring--alerts)
3. [Common Issues](#common-issues)
4. [Incident Response](#incident-response)
5. [Emergency Procedures](#emergency-procedures)
6. [Maintenance Tasks](#maintenance-tasks)
7. [Debugging Guide](#debugging-guide)

---

## Daily Operations

### Morning Health Check (9:00 AM UTC)

Run this checklist daily after the automated summary is posted to Slack:

```bash
# 1. Check pod health
kubectl get pods -n cassini -l app=green-flag-automation
# Expected: All pods Running with 3/3 API, 2/2 Worker

# 2. Check API health endpoint
curl https://green-flag-automation.cassini.skyscanner.net/api/health
# Expected: {"status": "healthy", "database": "connected", "redis": "connected"}

# 3. Check recent logs for errors
kubectl logs deployment/green-flag-automation-api -n cassini --since=24h | grep ERROR
kubectl logs deployment/green-flag-automation-worker -n cassini --since=24h | grep ERROR

# 4. Verify daily summary was sent
# Check #cassini-green-flag Slack channel for daily report

# 5. Check Grafana dashboard
# Open: https://grafana.cassini.skyscanner.net/d/green-flag-automation
# Verify:
#   - Error rate < 2%
#   - Automation enabled (should be 1)
#   - Queue depth < 10
#   - No overdue escalations
```

### Weekly Tasks (Monday Morning)

```bash
# 1. Review weekly metrics
# Check Grafana dashboard for 7-day trends

# 2. Verify audit cleanup job ran
kubectl logs -l job-name=green-flag-automation-audit-cleanup -n cassini --tail=50

# 3. Check for outdated dependencies
cd backend && poetry show --outdated
cd frontend && npm outdated

# 4. Review retraction rate
# Target: < 5% of auto-responded tickets
curl https://green-flag-automation.cassini.skyscanner.net/api/dashboard/metrics | jq '.retraction_rate'
```

---

## Monitoring & Alerts

### Key Metrics to Watch

| Metric | Normal Range | Warning | Critical |
|--------|--------------|---------|----------|
| Error Rate | < 1% | 2-5% | > 5% |
| Automation Rate | > 60% | 50-60% | < 50% |
| Queue Depth | 0-5 | 5-10 | > 10 |
| Escalation Queue | 0-3 | 3-5 | > 5 |
| Overdue Escalations | 0 | 1-2 | > 2 |
| Retraction Rate | < 2% | 2-5% | > 5% |
| API Response Time (P95) | < 500ms | 500ms-1s | > 1s |
| Worker Processing Time (P95) | < 10s | 10-20s | > 20s |

### Alert Definitions

#### High Priority Alerts

**1. HighTicketProcessingErrorRate**
- **Trigger**: Error rate > 5% for 2 minutes
- **Action**: [Circuit Breaker Triggered](#circuit-breaker-triggered)

**2. HighEscalationBacklog**
- **Trigger**: > 10 unresolved escalations
- **Action**: [Escalation Backlog](#escalation-backlog)

**3. AutomationDisabled**
- **Trigger**: Kill switch active for > 30 minutes
- **Action**: [Automation Disabled](#automation-disabled)

**4. DatabaseConnectionFailure**
- **Trigger**: Database health check fails
- **Action**: [Database Connection Issues](#database-connection-issues)

#### Medium Priority Alerts

**5. HighRetractionRate**
- **Trigger**: Retraction rate > 5% for 1 hour
- **Action**: [High Retraction Rate](#high-retraction-rate)

**6. SlowTicketProcessing**
- **Trigger**: P95 processing time > 20s
- **Action**: [Slow Processing](#slow-ticket-processing)

**7. ExternalServiceErrors**
- **Trigger**: Jira/Slack/LLM errors > 10% for 5 minutes
- **Action**: [External Service Degradation](#external-service-degradation)

---

## Common Issues

### Circuit Breaker Triggered

**Symptom**: Automation disabled automatically, alert received from Prometheus

**Cause**: Error rate exceeded 5% threshold

**Resolution**:

1. **Check recent errors**:
   ```bash
   kubectl logs deployment/green-flag-automation-worker -n cassini --since=15m | grep ERROR
   ```

2. **Identify root cause**:
   - LLM API failures → Check Anthropic/OpenAI status page
   - Jira API failures → Check Jira system status
   - Database errors → Check RDS metrics
   - Classification errors → Review recent canned response changes

3. **Fix the issue**:
   - If external service outage → Wait for resolution
   - If canned response issue → Revert CONFIG_VERSION
   - If database issue → Check RDS logs and restart if needed

4. **Test fix**:
   ```bash
   # Send test webhook
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/webhooks/jira \
     -H "Content-Type: application/json" \
     -d @tests/fixtures/jira_webhook_iam_request.json
   ```

5. **Re-enable automation**:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/enable
   ```

6. **Monitor for 30 minutes** to ensure error rate stays low

### Escalation Backlog

**Symptom**: > 10 unresolved escalations in queue

**Cause**: Green Flag holder not responding to Slack messages

**Resolution**:

1. **Check escalation list**:
   ```bash
   curl https://green-flag-automation.cassini.skyscanner.net/api/dashboard/escalations
   ```

2. **Identify overdue escalations**:
   ```bash
   # Escalations > 4 hours old
   curl https://green-flag-automation.cassini.skyscanner.net/api/dashboard/escalations?overdue=true
   ```

3. **Notify Green Flag holder**:
   - Post in #cassini-green-flag Slack channel
   - Tag @green-flag-holder with escalation count

4. **If holder unavailable**:
   - Check backup holder in PagerDuty rotation
   - Manually review and respond to urgent tickets

5. **Consider temporary kill switch** if backlog exceeds 20 tickets

### Automation Disabled

**Symptom**: Kill switch active, no auto-responses being sent

**Cause**: Manual disable or circuit breaker trigger

**Resolution**:

1. **Check kill switch status**:
   ```bash
   curl https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch
   ```

2. **Check who disabled it**:
   ```bash
   kubectl logs deployment/green-flag-automation-api -n cassini | grep "kill-switch/disable"
   # Look for: "Kill switch disabled by user@skyscanner.net"
   ```

3. **Verify reason for disable**:
   - Check #cassini-green-flag for announcements
   - Check PagerDuty for active incidents
   - Review recent deployments

4. **If safe to re-enable**:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/enable
   ```

5. **If not safe**:
   - Keep automation disabled
   - Manually process tickets
   - Fix underlying issue first

### Database Connection Issues

**Symptom**: API returns 500 errors, health check fails

**Cause**: RDS instance unavailable or connection pool exhausted

**Resolution**:

1. **Check RDS status**:
   ```bash
   aws rds describe-db-instances --db-instance-identifier green-flag-automation-production
   ```

2. **Check RDS metrics**:
   ```bash
   # CPU, connections, storage
   aws cloudwatch get-metric-statistics \
     --namespace AWS/RDS \
     --metric-name DatabaseConnections \
     --dimensions Name=DBInstanceIdentifier,Value=green-flag-automation-production \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average
   ```

3. **Check connection pool**:
   ```bash
   kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
   from src.models.base import engine
   print(f'Pool size: {engine.pool.size()}')
   print(f'Checked out: {engine.pool.checkedout()}')
   "
   ```

4. **Restart API pods** if connection pool is exhausted:
   ```bash
   kubectl rollout restart deployment/green-flag-automation-api -n cassini
   ```

5. **Check RDS security group** if connections are refused:
   ```bash
   aws ec2 describe-security-groups --group-ids sg-XXXXX
   # Verify EKS node security group has ingress on port 5432
   ```

6. **Failover to standby** if primary RDS is down (Multi-AZ):
   ```bash
   aws rds reboot-db-instance \
     --db-instance-identifier green-flag-automation-production \
     --force-failover
   ```

### High Retraction Rate

**Symptom**: > 5% of auto-responded tickets are retracted

**Cause**: Poor classification quality or outdated canned responses

**Resolution**:

1. **Review recent retractions**:
   ```bash
   curl https://green-flag-automation.cassini.skyscanner.net/api/dashboard/tickets?status=retracted&limit=20
   ```

2. **Identify patterns**:
   - Which canned responses are being retracted most?
   - Are retractions clustered by time (new response deployment)?
   - Are specific ticket types being misclassified?

3. **Review canned responses**:
   ```bash
   cat backend/src/config/canned_responses.yaml
   ```

4. **Actions**:
   - **Immediate**: Enable shadow mode for new responses
   - **Short-term**: Update problematic canned response keywords
   - **Long-term**: Retrain classification model with retraction data

5. **Enable shadow mode** if retraction rate exceeds 10%:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/shadow-mode/activate
   ```

### Slow Ticket Processing

**Symptom**: P95 processing time > 20 seconds

**Cause**: LLM API latency, database queries, or high load

**Resolution**:

1. **Check external service latency**:
   ```bash
   # View in Grafana: "External Service Latency" panel
   # Or query Prometheus:
   curl -G http://prometheus:9090/api/v1/query \
     --data-urlencode 'query=histogram_quantile(0.95, rate(external_service_request_duration_seconds_bucket[5m]))'
   ```

2. **Identify bottleneck**:
   - **LLM latency** → Check Anthropic/OpenAI status
   - **Database latency** → Check RDS Performance Insights
   - **Redis latency** → Check ElastiCache metrics

3. **Scale workers** if processing backlog is growing:
   ```bash
   kubectl scale deployment green-flag-automation-worker -n cassini --replicas=4
   ```

4. **Enable caching** for repeated classifications:
   ```python
   # Add to settings.py
   ENABLE_CLASSIFICATION_CACHE = True
   CACHE_TTL_SECONDS = 3600
   ```

5. **Monitor queue depth** after scaling:
   ```bash
   kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
   from src.services.queue import TicketQueue
   queue = TicketQueue()
   print(f'Queue depth: {queue.redis_client.llen(\"ticket_queue\")}')"
   ```

### External Service Degradation

**Symptom**: Jira/Slack/LLM API returning errors

**Cause**: External service outage or rate limiting

**Resolution**:

**For Jira/Slack**:
1. **Check service status**:
   - Jira: https://status.atlassian.com/
   - Slack: https://status.slack.com/

2. **Enable shadow mode** during outage:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/shadow-mode/activate
   ```

3. **Queue tickets for retry**:
   - Tickets will automatically retry on failure
   - Check retry queue: `ticket_queue_retry`

4. **Process manually** if outage is prolonged:
   ```bash
   # Export failed tickets
   kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
   from src.models.base import get_db
   from src.models.processed_ticket import ProcessedTicket
   db = next(get_db())
   failed = db.query(ProcessedTicket).filter(ProcessedTicket.status == 'failed').all()
   for ticket in failed:
       print(f'{ticket.ticket_id}: {ticket.jira_summary}')
   "
   ```

**For LLM API**:
1. **Check status**:
   - Anthropic: https://status.anthropic.com/
   - OpenAI: https://status.openai.com/

2. **Switch to fallback LLM**:
   ```bash
   # Update ConfigMap
   kubectl edit configmap green-flag-automation-config -n cassini
   # Set: LLM_PROVIDER=openai (or vice versa)

   # Restart workers to pick up change
   kubectl rollout restart deployment/green-flag-automation-worker -n cassini
   ```

3. **Reduce concurrency** if rate limited:
   ```bash
   # Scale down workers temporarily
   kubectl scale deployment green-flag-automation-worker -n cassini --replicas=1
   ```

---

## Incident Response

### Incident Severity Levels

| Severity | Definition | Response Time | Example |
|----------|------------|---------------|---------|
| **SEV-1** | Critical - Total system outage | 15 minutes | Database down, all tickets failing |
| **SEV-2** | Major - Partial outage | 1 hour | Circuit breaker triggered, 50% failures |
| **SEV-3** | Minor - Degraded performance | 4 hours | Slow processing, 10% errors |
| **SEV-4** | Low - Cosmetic issue | Next business day | Dashboard UI bug |

### Incident Response Workflow

#### 1. Detection & Triage (0-5 minutes)

```bash
# Acknowledge alert in PagerDuty
# Join #cassini-incidents Slack channel

# Quick health check
kubectl get pods -n cassini -l app=green-flag-automation
curl https://green-flag-automation.cassini.skyscanner.net/api/health

# Determine severity
# - SEV-1: Total outage, no tickets processing
# - SEV-2: Partial outage, high error rate
# - SEV-3: Degraded performance
```

#### 2. Containment (5-15 minutes)

```bash
# For SEV-1/SEV-2: Enable kill switch immediately
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/disable

# Notify stakeholders
# Post in #cassini-green-flag:
# "⚠️ Green Flag Automation is currently experiencing issues.
#  Automation has been disabled. Manual ticket processing required.
#  Incident: https://skyscanner.pagerduty.com/incidents/PXXXXXX"
```

#### 3. Investigation (15-60 minutes)

```bash
# Collect logs
kubectl logs deployment/green-flag-automation-api -n cassini --since=1h > api-logs.txt
kubectl logs deployment/green-flag-automation-worker -n cassini --since=1h > worker-logs.txt

# Check metrics
# Open Grafana dashboard and screenshot anomalies

# Review recent changes
git log --since="24 hours ago" --oneline

# Check external dependencies
curl -I https://api.anthropic.com/v1/health
curl -I https://skyscanner.atlassian.net/rest/api/2/myself
curl -I https://slack.com/api/api.test
```

#### 4. Resolution (varies)

Follow appropriate [Common Issues](#common-issues) procedure above.

#### 5. Recovery (post-fix)

```bash
# Test fix with single ticket
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/webhooks/jira \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/jira_webhook_iam_request.json

# Re-enable automation
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/enable

# Monitor closely for 1 hour
watch -n 60 'curl -s https://green-flag-automation.cassini.skyscanner.net/api/metrics | grep tickets_failed_total'
```

#### 6. Post-Incident Review (within 48 hours)

Create post-incident review document:

```markdown
# Incident Review: [Date] - [Title]

## Summary
- **Incident ID**: PXXXXXX
- **Severity**: SEV-X
- **Duration**: HH:MM
- **Impact**: X tickets affected

## Timeline
- HH:MM - Incident detected
- HH:MM - Kill switch enabled
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Automation re-enabled

## Root Cause
[Description]

## Resolution
[What was done to fix it]

## Action Items
- [ ] Update monitoring alerts (Owner: @name)
- [ ] Add retry logic (Owner: @name)
- [ ] Update runbook (Owner: @name)

## Prevention
[How to prevent this in future]
```

---

## Emergency Procedures

### Emergency Kill Switch Activation

**When to use**: Major incident, high error rate, incorrect responses

```bash
# Via API
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/disable

# Via kubectl (if API is down)
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.models.base import get_db
from src.models.system_config import SystemConfig
db = next(get_db())
config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
config.automation_enabled = False
db.commit()
print('✓ Automation disabled via database')
"

# Notify team in Slack
# Post in #cassini-green-flag:
# "🚨 EMERGENCY: Automation disabled. Reason: [REASON].
#  All tickets will be escalated. Manual processing required."
```

### Emergency Database Restore

**When to use**: Data corruption, accidental deletion

```bash
# 1. List available backups
aws rds describe-db-snapshots \
  --db-instance-identifier green-flag-automation-production \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table

# 2. Restore to new instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier green-flag-automation-restore-$(date +%Y%m%d) \
  --db-snapshot-identifier rds:green-flag-automation-production-2026-01-28-03-00

# 3. Wait for restore to complete (15-30 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier green-flag-automation-restore-$(date +%Y%m%d)

# 4. Update DATABASE_URL secret
NEW_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier green-flag-automation-restore-$(date +%Y%m%d) \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

kubectl create secret generic green-flag-automation-secrets \
  --from-literal=database-url="postgresql://gfa_admin:PASSWORD@${NEW_ENDPOINT}:5432/green_flag_automation" \
  --namespace=cassini \
  --dry-run=client -o yaml | kubectl apply -f -

# 5. Restart pods
kubectl rollout restart deployment/green-flag-automation-api -n cassini
kubectl rollout restart deployment/green-flag-automation-worker -n cassini
```

### Emergency Rollback

**When to use**: Bad deployment causing errors

```bash
# 1. Rollback Kubernetes deployment
kubectl rollout undo deployment/green-flag-automation-api -n cassini
kubectl rollout undo deployment/green-flag-automation-worker -n cassini

# 2. Wait for rollback
kubectl rollout status deployment/green-flag-automation-api -n cassini

# 3. Verify health
curl https://green-flag-automation.cassini.skyscanner.net/api/health

# 4. Rollback database migration if needed
kubectl exec -it deployment/green-flag-automation-api -n cassini -- bash
alembic downgrade -1
exit
```

---

## Maintenance Tasks

### Deploying New Canned Responses

```bash
# 1. Update canned_responses.yaml
vim backend/src/config/canned_responses.yaml

# 2. Increment CONFIG_VERSION
vim backend/src/config/settings.py
# Change: CONFIG_VERSION = "1.1.0"

# 3. Commit and push
git add backend/src/config/
git commit -m "feat: Add new canned response for VPN issues (CONFIG v1.1.0)"
git push origin main

# 4. Deploy to production
kubectl set image deployment/green-flag-automation-api \
  api=skyscanner/green-flag-automation:latest -n cassini

# 5. IMMEDIATELY activate shadow mode (48 hours)
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/shadow-mode/activate

# 6. Monitor shadow mode logs
kubectl logs -f deployment/green-flag-automation-worker -n cassini | grep "SHADOW MODE"

# 7. After 48 hours, deactivate shadow mode
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/shadow-mode/deactivate
```

### Rotating Secrets

**Frequency**: Every 90 days

```bash
# 1. Generate new secrets
NEW_JIRA_TOKEN="<from Jira settings>"
NEW_SLACK_TOKEN="<from Slack settings>"
NEW_DB_PASSWORD=$(openssl rand -base64 32)
NEW_REDIS_TOKEN=$(openssl rand -base64 32)

# 2. Update RDS password
aws rds modify-db-instance \
  --db-instance-identifier green-flag-automation-production \
  --master-user-password "${NEW_DB_PASSWORD}" \
  --apply-immediately

# 3. Update Redis auth token
aws elasticache modify-replication-group \
  --replication-group-id gfa-production \
  --auth-token "${NEW_REDIS_TOKEN}" \
  --auth-token-update-strategy ROTATE \
  --apply-immediately

# 4. Update Kubernetes secrets
kubectl create secret generic green-flag-automation-secrets \
  --from-literal=database-url="postgresql://gfa_admin:${NEW_DB_PASSWORD}@..." \
  --from-literal=redis-auth-token="${NEW_REDIS_TOKEN}" \
  --from-literal=jira-api-token="${NEW_JIRA_TOKEN}" \
  --from-literal=slack-bot-token="${NEW_SLACK_TOKEN}" \
  --namespace=cassini \
  --dry-run=client -o yaml | kubectl apply -f -

# 5. Restart pods to pick up new secrets
kubectl rollout restart deployment/green-flag-automation-api -n cassini
kubectl rollout restart deployment/green-flag-automation-worker -n cassini

# 6. Verify connectivity
kubectl exec -it deployment/green-flag-automation-api -n cassini -- \
  curl https://green-flag-automation.cassini.skyscanner.net/api/health
```

### Scaling for High Load

```bash
# Scale API pods
kubectl scale deployment green-flag-automation-api -n cassini --replicas=5

# Scale worker pods
kubectl scale deployment green-flag-automation-worker -n cassini --replicas=4

# Enable HPA (Horizontal Pod Autoscaler)
kubectl autoscale deployment green-flag-automation-api -n cassini \
  --cpu-percent=70 --min=3 --max=10

kubectl autoscale deployment green-flag-automation-worker -n cassini \
  --cpu-percent=70 --min=2 --max=8
```

---

## Debugging Guide

### Debugging Classification Issues

```bash
# 1. Enable debug logging
kubectl set env deployment/green-flag-automation-worker -n cassini LOG_LEVEL=DEBUG

# 2. Watch classification logs
kubectl logs -f deployment/green-flag-automation-worker -n cassini | grep "Classification"

# 3. Test classification manually
kubectl exec -it deployment/green-flag-automation-worker -n cassini -- python
>>> from src.services.classifier import TicketClassifier
>>> classifier = TicketClassifier()
>>> result = classifier.classify("How do I reset my password?", canned_responses)
>>> print(f"Confidence: {result.confidence_score}, Match: {result.matched_response_id}")
```

### Debugging Webhook Issues

```bash
# 1. Check webhook logs
kubectl logs deployment/green-flag-automation-api -n cassini | grep "/webhooks/jira"

# 2. Test webhook locally
curl -X POST http://localhost:8000/api/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=SIGNATURE" \
  -d @tests/fixtures/jira_webhook_iam_request.json

# 3. Check Jira webhook configuration
# Go to: Jira → Settings → System → Webhooks
# Verify URL, events, JQL filter

# 4. Test signature verification
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python
>>> import hmac, hashlib
>>> payload = b'{"test": "data"}'
>>> secret = "YOUR_WEBHOOK_SECRET"
>>> signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
>>> print(f"sha256={signature}")
```

### Debugging Redis Queue Issues

```bash
# 1. Check queue depth
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.services.queue import TicketQueue
queue = TicketQueue()
depth = queue.redis_client.llen('ticket_queue')
print(f'Queue depth: {depth}')
"

# 2. Inspect queued jobs
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.services.queue import TicketQueue
queue = TicketQueue()
jobs = queue.redis_client.lrange('ticket_queue', 0, 10)
for job in jobs:
    print(job.decode())
"

# 3. Clear stuck jobs
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.services.queue import TicketQueue
queue = TicketQueue()
queue.redis_client.delete('ticket_queue')
print('Queue cleared')
"
```

### Useful kubectl Commands

```bash
# Get pod resource usage
kubectl top pods -n cassini -l app=green-flag-automation

# Describe pod for events
kubectl describe pod <POD_NAME> -n cassini

# Get recent pod events
kubectl get events -n cassini --sort-by='.lastTimestamp' | grep green-flag

# Port forward to local machine
kubectl port-forward deployment/green-flag-automation-api 8000:8000 -n cassini

# Execute SQL query
kubectl exec -it deployment/green-flag-automation-api -n cassini -- psql $DATABASE_URL -c "SELECT COUNT(*) FROM processed_tickets WHERE created_at > NOW() - INTERVAL '24 hours';"
```

---

## Contact Information

### On-Call Rotation

- **Primary**: Check PagerDuty schedule
- **Secondary**: Check PagerDuty escalation policy
- **Manager**: cassini-manager@skyscanner.net

### Escalation Path

1. **L1**: On-call engineer (PagerDuty)
2. **L2**: Cassini tech lead
3. **L3**: Platform team
4. **L4**: Engineering manager

### Communication Channels

- **Incidents**: #cassini-incidents
- **Alerts**: #cassini-alerts
- **General**: #cassini-squad
- **Green Flag**: #cassini-green-flag

### External Contacts

- **Jira Support**: https://support.atlassian.com/
- **Slack Support**: https://slack.com/help/requests/new
- **Anthropic Support**: support@anthropic.com
- **AWS Support**: Open ticket in AWS Console

---

## Appendix

### Useful Links

- [Dashboard](https://green-flag-automation.cassini.skyscanner.net)
- [Grafana](https://grafana.cassini.skyscanner.net/d/green-flag-automation)
- [Prometheus](https://prometheus.cassini.skyscanner.net)
- [PagerDuty](https://skyscanner.pagerduty.com/service-directory/PXXXXXX)
- [GitHub Repository](https://github.com/Skyscanner/green-flag-automation)

### Log Locations

- **API Logs**: `kubectl logs deployment/green-flag-automation-api -n cassini`
- **Worker Logs**: `kubectl logs deployment/green-flag-automation-worker -n cassini`
- **RDS Logs**: CloudWatch Logs → `/aws/rds/instance/green-flag-automation-production/`
- **Redis Logs**: CloudWatch Logs → `/aws/elasticache/gfa-production/`

### Metrics Endpoints

- **Prometheus Metrics**: `https://green-flag-automation.cassini.skyscanner.net/api/metrics`
- **Health Check**: `https://green-flag-automation.cassini.skyscanner.net/api/health`
- **Readiness Check**: `https://green-flag-automation.cassini.skyscanner.net/api/health/ready`

---

**Last Updated**: 2026-01-28
**Maintained By**: Cassini DevOps Team
**Review Frequency**: Quarterly
