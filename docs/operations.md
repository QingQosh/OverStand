# OverStand Operations Runbook

This runbook enables operators to maintain OverStand infrastructure reliably on mainnet. It covers daily/weekly/monthly health checks, anomaly detection rules, and incident response procedures.

## Table of Contents

1. [Health Check Procedures](#health-check-procedures)
2. [Monitoring & Metrics](#monitoring--metrics)
3. [Anomaly Detection](#anomaly-detection)
4. [Incident Response](#incident-response)
5. [Post-Incident Review](#post-incident-review)
6. [Monitoring Setup](#monitoring-setup)

---

## Health Check Procedures

### Daily Health Check (5-10 minutes)

Run this check every morning to ensure the registry is operational.

**Objective**: Verify the contract responds to read operations and the instance storage is accessible.

**Procedure**:

```bash
#!/bin/bash
# daily-healthcheck.sh
set -e

CONTRACT_ID="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
RPC_URL="https://mainnet.stellar.validationcloud.io/v1"
QUERIER="GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# Test 1: GetAdmin (reads instance storage)
echo "=== Checking contract responsiveness ==="
ADMIN=$(stellar contract invoke \
  --id "$CONTRACT_ID" \
  --network mainnet \
  -- get_admin 2>&1)

if [ -z "$ADMIN" ]; then
  echo "FAILED: Contract did not return admin. Instance storage may be archived."
  exit 1
fi

echo "OK: Contract is responsive. Admin: $ADMIN"

# Test 2: GetAlertCount (reads persistent storage)
echo "=== Checking persistent storage ==="
COUNT=$(stellar contract invoke \
  --id "$CONTRACT_ID" \
  --network mainnet \
  -- get_alert_count 2>&1)

echo "OK: Persistent storage accessible. Alert count: $COUNT"

# Test 3: Sample pagination read (represents typical query)
echo "=== Checking pagination ==="
SAMPLE=$(stellar contract invoke \
  --id "$CONTRACT_ID" \
  --network mainnet \
  -- get_contract_alerts_paginated \
  --querier "$QUERIER" \
  --target_contract "$CONTRACT_ID" \
  --offset 0 \
  --limit 1 2>&1)

echo "OK: Pagination works. Sample result: $SAMPLE"

echo ""
echo "✅ Daily health check passed at $(date)"
```

**Success Criteria**:
- ✅ All three calls return within 5 seconds
- ✅ No "archive not found" or "ledger closed" errors
- ✅ Admin address is non-empty

**Failure Response**: Alert ops team immediately. See [Incident Response](#incident-response).

---

### Weekly Health Check (15-20 minutes)

Run this check every Monday to assess contract storage utilization and performance.

**Objective**: Ensure storage is within budget, no performance regressions, and watcher registry is synchronized.

**Procedure**:

```bash
#!/bin/bash
# weekly-healthcheck.sh

CONTRACT_ID="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WATCHER_ID="CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
RPC_URL="https://mainnet.stellar.validationcloud.io/v1"

# Check 1: Storage utilization
echo "=== Contract Storage Utilization ==="
STATS=$(stellar contract info --id "$CONTRACT_ID" --network mainnet)
echo "$STATS"

# Extract key metrics (varies by stellar-cli version; adjust as needed)
INSTANCE_SIZE=$(echo "$STATS" | grep -o "instance.*" | head -1)
DATA_SIZE=$(echo "$STATS" | grep -o "persistent.*" | head -1)

echo "Instance storage: $INSTANCE_SIZE"
echo "Persistent storage: $DATA_SIZE"

# Check 2: Alert registration rate (use a 7-day window)
echo ""
echo "=== Alert Registration Rate (7-day window) ==="
BEFORE=$(date -d "7 days ago" +%s)
CURRENT=$(date +%s)
INTERVAL=$((CURRENT - BEFORE))

# This would typically be fetched from a database or monitoring system that
# tracks events. For now, we'll use the get_alert_count endpoint.
COUNT=$(stellar contract invoke \
  --id "$CONTRACT_ID" \
  --network mainnet \
  -- get_alert_count 2>&1)

echo "Total alerts (all-time): $COUNT"
echo "Estimated weekly registration rate: ~N/A (requires event history)"

# Check 3: Watcher registry sync
echo ""
echo "=== Watcher Registry Sync ==="
WATCHER_COUNT=$(stellar contract invoke \
  --id "$WATCHER_ID" \
  --network mainnet \
  -- get_watcher_count 2>&1)

echo "Registered watchers: $WATCHER_COUNT"

if (( WATCHER_COUNT < 1 )); then
  echo "⚠️  WARNING: No watchers registered. Alert firing may be disabled."
fi

# Check 4: Limits
echo ""
echo "=== Registry Limits ==="
PER_OWNER=$(stellar contract invoke \
  --id "$CONTRACT_ID" \
  --network mainnet \
  -- get_per_owner_alert_limit 2>&1)

PER_CONTRACT=$(stellar contract invoke \
  --id "$CONTRACT_ID" \
  --network mainnet \
  -- get_per_contract_alert_limit 2>&1)

GLOBAL=$(stellar contract invoke \
  --id "$CONTRACT_ID" \
  --network mainnet \
  -- get_global_alert_limit 2>&1)

echo "Per-owner limit: $PER_OWNER"
echo "Per-contract limit: $PER_CONTRACT"
echo "Global limit: $GLOBAL"

echo ""
echo "✅ Weekly health check completed at $(date)"
```

**Success Criteria**:
- ✅ Instance storage < 50 KB (normal operation)
- ✅ Persistent storage stable or growing slowly (not sudden spikes)
- ✅ Watcher count ≥ 1
- ✅ Limits are reasonable (not 0 or 1, suggesting misconfiguration)

**Failure Response**: Investigate storage growth, check for DoS, review watcher status.

---

### Monthly Health Check (30-45 minutes)

Run this check on the first Monday of each month for a comprehensive audit.

**Procedure**:

```bash
#!/bin/bash
# monthly-healthcheck.sh

echo "=== Monthly OverStand Health Audit ==="
echo "Date: $(date)"
echo ""

# 1. Run daily + weekly checks
bash daily-healthcheck.sh
bash weekly-healthcheck.sh

# 2. Watcher churn analysis
echo ""
echo "=== Watcher Registration Churn (30-day window) ==="
echo "Note: Requires event history from blockchain or database"
echo "Expected: < 20% change in watcher count"
echo "Actual: Requires tooling integration (see Monitoring Setup)"

# 3. Alert owner distribution
echo ""
echo "=== Alert Owner Distribution ==="
echo "Top alert owners (requires pagination analysis)"
echo "This would iterate through get_alerts_by_owner_paginated for all owners"
echo "Expected: Evenly distributed, no single owner > 50% of alerts"

# 4. Query performance baseline
echo ""
echo "=== Query Performance Baseline ==="
for i in {1..3}; do
  START=$(date +%s%N)
  stellar contract invoke \
    --id "$CONTRACT_ID" \
    --network mainnet \
    -- get_contract_alerts_paginated \
    --querier "$QUERIER" \
    --target_contract "$CONTRACT_ID" \
    --offset 0 \
    --limit 100 > /dev/null 2>&1
  END=$(date +%s%N)
  ELAPSED_MS=$(( (END - START) / 1000000 ))
  echo "Query $i latency: ${ELAPSED_MS}ms"
done

echo ""
echo "✅ Monthly health audit completed at $(date)"
```

---

## Monitoring & Metrics

### Key Metrics to Track

| Metric | Collection Method | Alert Threshold | Notes |
|---|---|---|---|
| **Contract Responsiveness** | RPC `get_ledger_entry` | >5s latency | Daily check |
| **Alert Registration Rate** | Event listener or query log | >100/hour | Anomaly signal |
| **Active Alert Count** | `get_active_alert_count` per owner | Trending | Weekly check |
| **Watcher Count** | `get_watcher_count` | <1 watchers | Critical |
| **Webhook Delivery Rate** | Watcher logs | <90% success | Per-watcher basis |
| **Query Latency (p99)** | RPC query timing | >2 seconds | Indicates storage issues |
| **Storage Utilization** | Contract info / ledger size | >50 KB instance | Monthly check |
| **Instance TTL** | Ledger entry TTL | <7 days | Indicates archive risk |

### Prometheus Queries

If using Prometheus for monitoring:

```yaml
# Alert registration rate (per hour)
rate(overstand_alerts_registered_total[1h])

# Webhook delivery failures
rate(overstand_webhook_failures_total[5m]) / rate(overstand_webhook_attempts_total[5m])

# Query latency (p99)
histogram_quantile(0.99, rate(overstand_query_duration_seconds_bucket[5m]))

# Active alerts per owner
overstand_active_alerts_per_owner

# Watcher count
overstand_watcher_count
```

---

## Anomaly Detection

### Rule 1: Alert Spike

**Trigger**: >100 alert registrations in 1 hour

**Detection**:
```bash
# Pseudo-code; implement with event listener or query log analysis
if (alerts_registered_last_hour > 100) {
  SEVERITY=HIGH
  ACTION=INVESTIGATE
}
```

**Possible Causes**:
- ✅ Legitimate surge: New customer or integration
- ⚠️ Misconfiguration: Webhook receiver registering alerts in a loop
- ❌ **Attack**: DoS attempt, fill registry to max limit

**Mitigation Steps**:
1. Check watcher logs for unusual registration patterns
2. Identify the registering owner(s)
3. Check if registrations are from known integrators
4. If unknown: Contact owner, ask for explanation
5. If malicious: Admin can call `set_per_owner_alert_limit(owner, 0)` to freeze registrations

**Recovery**:
- If misconfiguration: Owner updates integration and resumes
- If attack: Admin resets limit after threat passes, optionally removes malicious alerts

---

### Rule 2: Watcher Churn

**Trigger**: >20% change in watcher count in 24 hours

**Detection**:
```bash
# Compare watcher count to baseline
BASELINE_WATCHERS=3  # Previous day average
CURRENT_WATCHERS=$(stellar contract invoke ... get_watcher_count)
CHANGE=$(( (CURRENT_WATCHERS - BASELINE_WATCHERS) / BASELINE_WATCHERS * 100 ))

if [ $(( abs(CHANGE) )) -gt 20 ]; then
  SEVERITY=MEDIUM
  ACTION=INVESTIGATE
fi
```

**Possible Causes**:
- ✅ Expected: Planned watcher deployment
- ⚠️ Unexpected: Watcher node failures or rollbacks
- ❌ **Risk**: Alert firing may be temporarily disabled if all watchers go down

**Mitigation Steps**:
1. Check watcher deployment logs / infrastructure
2. Verify watcher nodes are still running and reachable
3. Check for recent contract upgrades or configuration changes
4. If watcher is down: Page on-call watcher operator

**Recovery**:
- Restart watcher nodes
- Deploy replacement watcher (if permanent failure)
- Monitor watcher count return to baseline

---

### Rule 3: Query Latency Spike

**Trigger**: Query p99 latency >2 seconds for 10+ consecutive queries

**Detection**:
```bash
# Measure query latency over time
for i in {1..10}; do
  START=$(date +%s%N)
  stellar contract invoke ... get_contract_alerts_paginated ... > /dev/null
  END=$(date +%s%N)
  LATENCY_MS=$(( (END - START) / 1000000 ))
  if (( LATENCY_MS > 2000 )); then
    SLOW_QUERIES=$((SLOW_QUERIES + 1))
  fi
done

if (( SLOW_QUERIES >= 10 )); then
  SEVERITY=HIGH
  ACTION=INVESTIGATE_STORAGE
fi
```

**Possible Causes**:
- ✅ Network congestion: High Stellar network load
- ⚠️ Storage stress: Query scanning many entries, cache miss
- ❌ **Risk**: Alerts may not fire in time; users see timeouts

**Mitigation Steps**:
1. Check Stellar network status / block time
2. Check RPC server load and availability
3. Analyze contract storage size (instance + persistent)
4. Review recent alert patterns (unusual query distribution?)
5. If storage is excessive: Consider admin cleanup (remove inactive alerts)

**Recovery**:
- Scale RPC infrastructure
- Migrate to faster RPC provider
- Offload old alerts to archive (via admin removal)

---

### Rule 4: Webhook Failures

**Trigger**: >10% webhook failure rate in a 5-minute window across all watchers

**Detection**:
```bash
# Watcher logs aggregate webhook delivery metrics
FAILED=$(watcher_logs | grep "webhook_failed" | wc -l)
TOTAL=$(watcher_logs | grep "webhook_" | wc -l)
FAILURE_RATE=$(( FAILED * 100 / TOTAL ))

if (( FAILURE_RATE > 10 )); then
  SEVERITY=HIGH
  ACTION=PAGE_INTEGRATORS
fi
```

**Possible Causes**:
- ✅ Transient: Temporary network hiccup
- ⚠️ Receiver down: User's webhook endpoint is timing out or 5xx
- ⚠️ Rate limiting: Webhook receiver rate-limited watcher node
- ❌ **Risk**: Alerts don't reach users; they miss events

**Mitigation Steps**:
1. Check watcher logs for specific webhook receiver addresses
2. Contact affected integrators: "Your webhook receiver is failing, we see X% failures"
3. Ask integrators to check their endpoints
4. If receiver is flaky: Suggest load balancing or caching layer
5. If watcher is down: Restart or redeploy

**Recovery**:
- Integrator fixes their webhook receiver
- Watcher retries queued deliveries
- Resume normal alert firing

---

## Incident Response

### Incident Classification

| Severity | Example | Response Time | Escalation |
|---|---|---|---|
| **Critical (SEV-1)** | Contract unresponsive, all alerts failing | 15 min | Page on-call, notify community |
| **High (SEV-2)** | 50%+ webhook failures, >1 hour churn | 1 hour | Page on-call |
| **Medium (SEV-3)** | Single watcher down, elevated query latency | 4 hours | Create ticket |
| **Low (SEV-4)** | Informational anomalies, minor performance dip | Next business day | Log and review |

### Incident Response Template

When an incident is detected:

#### 1. Acknowledge & Assess (0-5 min)

```markdown
## INCIDENT ALERT: [Title]

**Time**: [ISO 8601 timestamp]  
**Severity**: [SEV-1/2/3/4]  
**Detected By**: [Check type or alert name]  
**Impact**: [Who/what is affected]

### Initial Assessment

- [ ] Confirm the issue (re-run check)
- [ ] Identify affected systems (e.g., AlertRegistry, Watcher nodes)
- [ ] Check for recent deployments or changes
- [ ] Page on-call if SEV-1 or 2

**Root Cause (Initial)**: [e.g., "Instance storage archived"]
**Action**: [Next step - see below]
```

#### 2. Communicate (Ongoing)

**Internal** (Discord #incidents channel):
```
🚨 SEV-2: Webhook delivery failures (60% failure rate)
Affected: All watchers
Status: Investigating
ETA: 15 min
Link: [Incident post]
```

**External** (Twitter, Discord #announcements):
```
⚠️ We are currently investigating elevated webhook delivery latencies.
Alerts are being registered normally, but delivery may be delayed.
We will update every 15 minutes. Status: https://status.qingqosh.org
```

#### 3. Troubleshoot & Mitigate (5-30 min)

**If Contract Unresponsive**:
- [ ] Check Stellar network status
- [ ] Verify RPC server is responsive
- [ ] Check if instance storage needs bump (call `bump_instance_ttl`)
- [ ] If archived: Invoke contract to restore (requires admin key)

**If Webhook Failures High**:
- [ ] Check watcher node logs
- [ ] Identify failing receiver addresses
- [ ] Contact integrators
- [ ] If watcher down: Restart or redeploy

**If Query Latency High**:
- [ ] Check contract storage size
- [ ] Run sample queries against different ledgers
- [ ] If storage excessive: Admin cleanup

**If Alert Spike Suspicious**:
- [ ] Identify registering owner(s)
- [ ] Check registration pattern (bot-like vs human)
- [ ] Contact owner or freeze via limit

#### 4. Resolve (30-60 min)

- [ ] Root cause confirmed
- [ ] Mitigation in place
- [ ] Metrics normalizing
- [ ] Update incident post with resolution

#### 5. Post-Incident Review (24-48 hours)

See [Post-Incident Review](#post-incident-review) section.

### Escalation Contacts

| Role | Escalation | Contact |
|---|---|---|
| **On-Call Operator** | SEV-1/2 alerts | Pagerduty (link) |
| **Watcher Ops** | Watcher node issues | watcher-ops@qingqosh.org |
| **Contract Owner** | Admin actions needed | admin@qingqosh.org |
| **Community** | Status/transparency updates | @QingQosh (Twitter) |

### Incident Communication Examples

#### Example 1: Contract Unresponsive

```
🚨 SEV-1: AlertRegistry contract unresponsive (15:42 UTC)

Status: INVESTIGATING
- Contract is not responding to RPC queries
- Instance storage may be archived

Actions in progress:
- Checking Stellar network status ✓ (Network: OK)
- Restoring instance storage... (in progress)

ETA: 20 minutes
Updates: Every 5 minutes in this thread
```

(15 min later)
```
✅ RESOLVED

Root cause: Instance storage TTL expired and was archived.
Fix: Called `bump_instance_ttl` to restore access.
Impact: ~12 min of unavailability, ~2K webhook deliveries queued for retry.

Next steps:
- [ ] Increase instance TTL bump frequency in monitoring
- [ ] Post-incident review in 24h
```

#### Example 2: Webhook Delivery Failures

```
⚠️ SEV-2: Elevated webhook delivery failures (60% rate, 14:30 UTC)

Status: INVESTIGATING
- Watcher nodes reporting high failure rates to specific receiver IPs
- Identified 3 integrators affected
- Root cause unknown (network, rate limiting, or receiver issue)

Actions in progress:
- Contacting affected integrators for receiver status
- Checking watcher logs for patterns

ETA: 30 minutes
```

(30 min later)
```
✅ RESOLVED

Root cause: One integrator's webhook receiver was rate-limiting watcher requests.
Impact: ~1 hour of delivery delays for that integrator's alerts.

Resolution:
- Integrator increased rate limit on their endpoint
- Watcher retried queued deliveries successfully
- Failure rate now <1%

Lessons learned:
- Add webhook receiver rate limiting to security best practices doc
- Consider implementing exponential backoff in watcher retry logic
```

---

## Post-Incident Review

After any SEV-1/2 incident, conduct a post-incident review within 24-48 hours.

### PIR Template

```markdown
## Post-Incident Review: [Incident Title]

**Incident Date**: [Date]  
**Duration**: [Start - End time, total duration]  
**Severity**: [SEV-1/2]  
**Participants**: [Names]  
**Lead**: [Name]  
**Scribe**: [Name]

### Timeline

- **14:30** - Alert spike detected (>100/hour)
- **14:35** - Owner identified as integration test service
- **14:40** - Owner contacted via email
- **14:50** - Owner fixed configuration
- **15:00** - Alert rate normalized
- **15:15** - All-clear posted to community

### Root Cause Analysis

**What happened**:
Integration test service was registering alerts in a loop due to a bug in their deployment script.

**Why did it happen**:
- Test script didn't have a termination condition
- No rate limiting on alert registration (by design)
- No monitoring alert for high registration rate (gap identified)

**Why weren't we aware earlier**:
- Spike detection was not yet implemented
- No automatic notification to owner

### Action Items

| Priority | Item | Owner | Due Date |
|---|---|---|---|
| P0 | Implement alert spike detection (>100/hour) | @monitoring-lead | 1 week |
| P1 | Add webhook for notifying owners of suspicious registrations | @backend-lead | 2 weeks |
| P2 | Document best practices for integration testing | @docs-lead | 1 month |

### Lessons Learned

1. **What went well**:
   - Quick response once owner was contacted
   - No contract impact or data loss
   - Community remained calm

2. **What could be better**:
   - We could have detected this automatically
   - We should have alert guidelines for integrators
   - Test environment should use separate contract instance

### Follow-up

- Spike detection will be implemented in next sprint
- Docs updated with integration best practices
- Separate testnet contracts for integrator testing

---

**PIR Completed**: [Date]  
**Approved By**: [Name]
```

---

## Monitoring Setup

### Prometheus Configuration

If running Prometheus for OverStand monitoring:

```yaml
# prometheus.yml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: 'overstand-contract'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8080']
```

### Grafana Dashboard JSON

Sample Grafana dashboard for OverStand:

```json
{
  "dashboard": {
    "title": "OverStand Mainnet Operations",
    "panels": [
      {
        "title": "Alert Registration Rate (per hour)",
        "targets": [
          {
            "expr": "rate(overstand_alerts_registered_total[1h])"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": { "type": "gt", "params": [100] },
              "message": "Alert registration rate >100/hour"
            }
          ]
        }
      },
      {
        "title": "Webhook Delivery Success Rate",
        "targets": [
          {
            "expr": "rate(overstand_webhook_delivered_total[5m]) / rate(overstand_webhook_attempts_total[5m])"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": { "type": "lt", "params": [0.9] },
              "message": "Webhook delivery success <90%"
            }
          ]
        }
      },
      {
        "title": "Query Latency (p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(overstand_query_duration_seconds_bucket[5m]))"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": { "type": "gt", "params": [2] },
              "message": "Query latency p99 >2s"
            }
          ]
        }
      },
      {
        "title": "Watcher Count",
        "targets": [
          {
            "expr": "overstand_watcher_count"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": { "type": "lt", "params": [1] },
              "message": "Watcher count <1 (alerts may not fire)"
            }
          ]
        }
      }
    ]
  }
}
```

### Event Listener Setup

For tracking alert events, run a listener that consumes Stellar events:

```bash
#!/bin/bash
# event-listener.sh - Example stub

CONTRACT_ID="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# Requires: stellar-cli event listener implementation
# This is a placeholder for custom implementations using:
# - JavaScript SDK sorobanrpc.getEvents()
# - Go SDK sorobanrpc events subscription
# - Python SDK with websocket listener

echo "Listening for OverStand events..."

# Pseudo-code:
# while true:
#   events = fetch_events(CONTRACT_ID, last_ledger)
#   for event in events:
#     if event.type == "alert_registered":
#       metrics.increment("alerts_registered")
#     elif event.type == "webhook_fired":
#       metrics.increment("webhooks_fired")
#   sleep(30)
```

---

## Appendices

### A. Useful Commands

```bash
# Get contract info
stellar contract info --id $CONTRACT_ID --network mainnet

# Get admin
stellar contract invoke --id $CONTRACT_ID --network mainnet -- get_admin

# Get limits
stellar contract invoke --id $CONTRACT_ID --network mainnet -- get_per_owner_alert_limit

# Check RPC latency
time curl -X POST "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"getLatestLedger","params":[],"id":1}' | jq '.result.sequence'

# List recent transactions (requires local soroban-cli or custom parsing)
stellar transaction list --id $CONTRACT_ID --network mainnet
```

### B. Alerting Rules (Prometheus)

```yaml
# alert-rules.yaml
groups:
  - name: overstand
    rules:
      - alert: AlertRegistrationSpike
        expr: rate(overstand_alerts_registered_total[1h]) > 100
        for: 5m
        annotations:
          summary: "Alert registration rate exceeded 100/hour"
          action: "Check for DoS or misconfiguration"

      - alert: WebhookFailureRate
        expr: (1 - (rate(overstand_webhook_delivered_total[5m]) / rate(overstand_webhook_attempts_total[5m]))) > 0.1
        for: 10m
        annotations:
          summary: "Webhook delivery failures exceeded 10%"
          action: "Check watcher logs and integrator receivers"

      - alert: QueryLatencyP99
        expr: histogram_quantile(0.99, rate(overstand_query_duration_seconds_bucket[5m])) > 2
        for: 10m
        annotations:
          summary: "Query latency p99 exceeded 2 seconds"
          action: "Check RPC load and storage utilization"

      - alert: WatcherCount
        expr: overstand_watcher_count < 1
        for: 1m
        annotations:
          summary: "No watchers registered"
          action: "CRITICAL - Alerts will not fire. Restore watcher immediately."
```

### C. Status Page Template

Maintain a status page (e.g., status.qingqosh.org) with:

- Current system status (Operational / Degraded / Down)
- Incident history
- Planned maintenance schedule
- Component status (AlertRegistry, Watcher nodes, RPC)

---

**Last Updated**: October 24, 2026  
**Version**: 1.0  
**Maintained By**: OverStand Operations Team  
**Next Review**: October 24, 2027
