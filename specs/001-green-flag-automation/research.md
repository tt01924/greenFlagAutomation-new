# Research: Green Flag Ticket Automation

**Feature**: Green Flag Ticket Automation
**Date**: 2026-01-27
**Status**: Complete

## Overview

This document captures technology research and decisions for implementing the Green Flag automation system. All decisions prioritize fail-safe operation, auditability, and constitutional compliance.

---

## Decision 1: Ticket Classification Approach

### Context
Need to match incoming Jira tickets against 11 canned response categories with semantic understanding (e.g., distinguishing "Cortex bug" from "Cortex feature request").

### Options Evaluated

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Keyword/Regex matching** | Simple, fast, deterministic | Brittle, misses semantic nuances, high maintenance | ❌ Rejected |
| **TF-IDF + Cosine Similarity** | Classical NLP, no API costs | Poor semantic understanding, requires keyword engineering | ❌ Rejected |
| **BERT Embeddings + KNN** | Good semantic matching | Requires training data, complexity, operational overhead | ❌ Rejected |
| **LLM Few-Shot Classification** | Excellent semantic understanding, handles nuance, includes reasoning | API costs, latency, requires prompt engineering | ✅ **Selected** |

### Decision: LLM-Based Few-Shot Classification

Use Anthropic Claude (Sonnet) or OpenAI GPT-4 with few-shot prompting to classify tickets.

**Rationale**:
- Canned responses have subtle semantic differences (e.g., "IAM request" vs "CQL request")
- LLMs excel at understanding intent and context
- Can provide confidence scores and reasoning (required by constitution)
- No training data required - few-shot examples in prompt
- Easier to add new canned responses (just update prompt, no retraining)

**Implementation Details**:
- Prompt structure: System instructions + 11 canned response descriptions + ticket content
- Output format: Structured JSON with `{matched_response_id: string, confidence: float (0-1), reasoning: string}`
- Timeout: 30 seconds hard limit
- Fallback: On timeout or error, escalate to human

**Prompt Engineering**:
```
You are a ticket classifier for Cassini's Green Flag support system.

Given a ticket, select the most appropriate canned response from the list below.
If no response clearly matches or multiple responses are equally valid, return low confidence.

Canned Responses:
1. IAM Request - Keywords: IAM, permissions, policy, account access
2. CQL Request - Keywords: CQL, Cortex query, steampipe, scorecard
...

Ticket:
Title: {title}
Description: {description}

Return JSON:
{
  "matched_response_id": "string or null",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation of your decision"
}
```

**Cost Estimate**:
- ~1000 tokens per classification (ticket + prompt + response)
- 100 tickets/week = 100k tokens/week
- Anthropic Claude Sonnet: ~$3/million input tokens, $15/million output
- **~$2-5/week or $100-250/year** (acceptable)

---

## Decision 2: Audit Log Storage

### Context
Must store immutable audit logs with 90-day retention, full ticket snapshots, confidence scores, and decision reasoning. Constitution requires tamper-evident logs.

### Options Evaluated

| Storage | Pros | Cons | Verdict |
|---------|------|------|---------|
| **PostgreSQL (JSONB)** | ACID, append-only triggers, JSONB flexibility, Skyscanner RDS | Requires DB management | ✅ **Selected** |
| **DynamoDB** | Serverless, low ops | Eventual consistency (not ACID), harder audit guarantees | ❌ Rejected |
| **MongoDB** | Document flexibility | Weaker consistency, not standard at Skyscanner | ❌ Rejected |
| **TimescaleDB** | Optimized for time-series | Overkill for 13k records/year, added complexity | ❌ Rejected |
| **S3 (append-only)** | Simple, cheap | No querying, no transactional guarantees | ❌ Rejected |

### Decision: PostgreSQL 14+ with Append-Only Pattern

**Rationale**:
- Strong ACID guarantees for audit integrity
- JSONB columns for flexible ticket snapshots without rigid schema
- Database-level triggers can enforce append-only (prevent updates/deletes)
- Excellent query performance for dashboard (<3s load time)
- Skyscanner already has managed RDS infrastructure
- 13k records/year is trivial for PostgreSQL (millions of records easily supported)

**Schema Design**:
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id VARCHAR(50) NOT NULL,
    ticket_snapshot JSONB NOT NULL,           -- Full Jira ticket JSON
    confidence_scores JSONB NOT NULL,          -- {response_id: {confidence, reasoning}}
    matched_response_id VARCHAR(100),          -- NULL if escalated
    action VARCHAR(20) NOT NULL,               -- 'auto_respond' | 'escalate'
    escalation_reason VARCHAR(200),            -- NULL if auto_respond
    comment_id VARCHAR(50),                    -- Jira comment ID if posted
    system_version VARCHAR(20) NOT NULL,       -- e.g., "v1.2.3"
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    -- Prevent updates and deletes via trigger
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_created_at (created_at),
    INDEX idx_action (action)
);

-- Trigger to prevent updates/deletes
CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs table is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutability
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
```

**90-Day Retention**:
- Daily cron job archives logs older than 90 days to S3 (encrypted)
- Archived logs remain queryable via S3 Select if needed
- After 90 days in S3, can be transitioned to Glacier or deleted per compliance policy

---

## Decision 3: Ticket Processing Queue

### Context
Need reliable queue for async ticket processing with fail-safe guarantees (zero ticket loss). Must handle Jira webhook spikes and service restarts.

### Options Evaluated

| Queue | Pros | Cons | Verdict |
|-------|------|------|---------|
| **Redis (RQ/Celery)** | Simple, fast, persistent, lower ops overhead | Not as battle-tested as RabbitMQ for critical workflows | ✅ **Selected** |
| **RabbitMQ** | Industry standard, robust, guaranteed delivery | Higher ops complexity, overkill for 100 tickets/day | ❌ Rejected |
| **AWS SQS** | Serverless, low ops | Higher latency, AWS lock-in, eventual consistency | ❌ Rejected |
| **Kafka** | High throughput, battle-tested | Massive overkill for this scale, ops complexity | ❌ Rejected |

### Decision: Redis with RQ (or Celery)

**Rationale**:
- Simple setup, widely used in Python ecosystem
- Redis persistence (AOF + RDB) ensures zero ticket loss on restart
- Low latency (<10ms queue operations)
- Good enough for 100 tickets/day (Redis handles millions of ops/sec)
- Skyscanner likely already runs Redis for caching
- If Redis fails, webhook returns 5xx → Jira retries automatically

**Implementation Details**:
- Queue name: `green_flag_tickets`
- Worker process: Separate container/pod from webhook API
- Job data: `{ticket_id, ticket_snapshot, timestamp}`
- Retry policy: 3 attempts with exponential backoff (1min, 5min, 15min)
- Dead letter queue: `green_flag_failed_tickets` for manual review

**Fail-Safe Mechanism**:
1. Webhook receives Jira ticket → enqueue to Redis → return 202 Accepted
2. If Redis unavailable → webhook returns 5xx → Jira retries
3. Worker pops from queue → process → audit log → post response
4. If worker crashes mid-processing → job returns to queue (Redis visibility timeout)
5. After 3 retries → move to DLQ → alert Green Flag holder via Slack

---

## Decision 4: Dashboard Framework

### Context
Need lightweight dashboard for Green Flag holder to view processed tickets, retract responses, activate kill switch, and view weekly reports.

### Options Evaluated

| Framework | Pros | Cons | Verdict |
|-----------|------|------|---------|
| **React + Vite** | Standard at Skyscanner, large ecosystem, fast dev, TypeScript support | Overkill for simple dashboard | ✅ **Selected** |
| **Svelte** | Smaller bundle, simpler | Less familiar to team, smaller ecosystem | ❌ Rejected |
| **Server-rendered (Jinja)** | Simple, no build step | Poor UX for real-time updates, less interactive | ❌ Rejected |
| **Vue** | Gentler learning curve than React | Less standard at Skyscanner | ❌ Rejected |

### Decision: React + Vite + TypeScript

**Rationale**:
- React is standard at Skyscanner (team familiarity)
- Vite provides fast dev experience and optimized builds
- TypeScript ensures type safety with backend API
- Large ecosystem for charting (Recharts) and UI (shadcn/ui)
- Over-engineering is acceptable here - dev speed > bundle size for internal tool

**Pages**:
1. **Dashboard** (`/`) - List of recent tickets with filters (auto-responded, escalated, last 24h)
2. **Ticket Detail** (`/tickets/:id`) - Full ticket view with retract button and audit log timeline
3. **Weekly Report** (`/reports`) - Charts for auto/escalate ratio, confidence distribution, retraction rate
4. **Kill Switch** (`/settings`) - Toggle automation on/off, view shadow mode status

**API Integration**:
- Axios or Fetch for REST API calls to backend
- SWR or React Query for data fetching and caching
- WebSocket (optional) for real-time updates (lower priority)

---

## Decision 5: LLM Provider

### Context
Need LLM API for ticket classification with high reliability, low latency, and strong reasoning capabilities.

### Options Evaluated

| Provider | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Anthropic Claude (Sonnet)** | Strong reasoning, lower hallucination, structured outputs | Slightly higher cost than GPT-3.5 | ✅ **Selected** |
| **OpenAI GPT-4** | Excellent performance, widely used | Higher cost than Sonnet, higher latency | ✅ Fallback |
| **OpenAI GPT-3.5 Turbo** | Cheaper, faster | Lower reasoning quality, more hallucinations | ❌ Rejected |
| **Self-hosted Llama 3** | No API costs | Ops overhead (GPU infra), higher latency, lower quality | ❌ Rejected |
| **Cohere** | Good for classification | Less proven for reasoning tasks | ❌ Rejected |

### Decision: Anthropic Claude (Sonnet) with GPT-4 Fallback

**Rationale**:
- Claude Sonnet has excellent reasoning capabilities (critical for confidence + reasoning output)
- Lower hallucination rate than GPT models (important for accuracy)
- Structured JSON output support (native in API)
- Skyscanner may already have Anthropic Enterprise contract (confirm with procurement)
- Fallback to GPT-4 if Claude unavailable (provider diversity for resilience)

**Implementation Details**:
- Use Anthropic SDK for Python (`anthropic` package)
- Model: `claude-sonnet-4-5-20250929` (latest as of 2026-01-27)
- Timeout: 30 seconds
- Retry: 2 attempts with 5s backoff
- Fallback: If Claude fails 3 times in 1 hour → switch to GPT-4 temporarily

**Cost Comparison** (per million tokens):
- Claude Sonnet: $3 input / $15 output
- GPT-4 Turbo: $10 input / $30 output
- Expected usage: ~100k tokens/week = $2-5/week for Sonnet, $5-10/week for GPT-4

**Prompt Optimization**:
- Use Claude's XML tag format for structured prompts
- Cache system instructions (reduces input tokens by 50%)
- Batch multiple tickets if latency allows (not critical for 100/week)

---

## Decision 6: Jira Integration Method

### Context
Need to receive new Green Flag tickets and post responses. Two options: polling vs webhooks.

### Options Evaluated

| Method | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Webhooks** | Real-time, push-based, lower load | Requires public endpoint, webhook config in Jira | ✅ **Selected** |
| **Polling** | Simple, no public endpoint needed | Higher latency, unnecessary load on Jira API | ❌ Rejected |

### Decision: Jira Webhooks

**Rationale**:
- Real-time notification when tickets are created/updated
- Lower latency (seconds vs minutes with polling)
- No need to poll Jira API every minute (respectful of rate limits)
- Skyscanner infra supports ingress via K8s LoadBalancer

**Webhook Configuration**:
- Jira Admin → System → Webhooks
- URL: `https://green-flag-automation.skyscanner.net/webhooks/jira`
- Events: `issue_created`, `issue_updated`, `comment_created`
- JQL Filter: `project = CASSINI AND labels = "Green-Flag"`
- Authentication: Webhook secret in `X-Hub-Signature` header

**Security**:
- Verify webhook signature using HMAC-SHA256
- Rate limiting: 100 req/min (reject 429 if exceeded)
- IP whitelist: Only allow Jira Cloud IPs

---

## Decision 7: Slack Integration Method

### Context
Need to send escalation notifications to current Green Flag holder. Slack API offers multiple methods.

### Options Evaluated

| Method | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Slack Webhook (Incoming)** | Simple, one-way posting | No interactive buttons, no user lookup | ❌ Rejected |
| **Slack Bot with Web API** | Full API access, interactive buttons, user lookup | Requires bot token, slightly more complex | ✅ **Selected** |
| **Slack Slash Command** | Interactive | Not suitable for automated notifications | ❌ Rejected |

### Decision: Slack Bot with Web API

**Rationale**:
- Can send direct messages to Green Flag holder (via user ID or email lookup)
- Supports interactive buttons ("Mark as Reviewed")
- Can update messages after sending (e.g., mark as reviewed)
- Slack Web API is standard and well-documented

**Bot Setup**:
1. Create Slack app in Skyscanner workspace
2. Enable bot scopes: `chat:write`, `users:read`, `users:read.email`
3. Install app to workspace → get bot token
4. Store bot token in K8s secret

**Escalation Message Format**:
```
🚨 Green Flag Ticket Needs Review

Ticket: CASSINI-1234
Link: https://jira.skyscanner.net/browse/CASSINI-1234
Reason: Low confidence (highest: 65%)

Top Matches:
1. IAM Request (65%) - Mentioned "permissions" but unclear context
2. CQL Request (58%) - Mentioned "query" but not Cortex-specific

[View in Dashboard] [Mark as Reviewed]
```

**On-Call Lookup**:
- Option 1: Hardcoded config with rotation schedule
- Option 2: Integration with PagerDuty/OpsGenie API to fetch current on-call
- **Selected**: Start with config file, migrate to PagerDuty API in v2

---

## Decision 8: Shadow Mode Implementation

### Context
Constitution requires 48-hour shadow mode after canned response config changes. Need state management for shadow mode.

### Options Evaluated

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Feature flag service (LaunchDarkly)** | Centralized, UI for toggling | External dependency, overkill | ❌ Rejected |
| **Config file with timestamp** | Simple, version-controlled | Manual timestamp management | ✅ **Selected** |
| **Database flag** | Dynamic toggling | Not version-controlled, can drift from code | ❌ Rejected |

### Decision: Config File with Timestamp

**Rationale**:
- Canned responses are version-controlled in Git
- Add `activated_at` timestamp to config file
- On service startup, load config and check: `if now() - activated_at < 48h → shadow_mode = true`
- After 48h, automatically transitions to active mode
- Requires manual timestamp update in PR (acceptable - forces human review)

**Config Format** (YAML):
```yaml
version: "1.1.0"
activated_at: "2026-01-27T14:00:00Z"  # Manually set in PR
shadow_mode_hours: 48

canned_responses:
  - id: "iam-request"
    name: "Cassini - IAM request"
    response: |
      Hey {{issueReporter}}, if you could provide the account, project role...
    keywords:
      - IAM
      - permissions
      - policy
      - account access
```

**Behavior**:
- Shadow mode: Process tickets, run classification, log to audit table with `action='shadow'`, do NOT post to Jira
- After 48h: Process tickets normally, post responses
- Dashboard shows banner: "Shadow mode active: {time_remaining}" with list of shadow-mode decisions

---

## Decision 9: Authentication for Dashboard

### Context
Dashboard needs to be accessible only to Cassini squad members. Kill switch requires authorization.

### Options Evaluated

| Method | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Skyscanner SSO (SAML/OIDC)** | Standard, integrated with org identity | Complex setup | ✅ **Selected** |
| **Basic Auth** | Simple | Not integrated with org identity, poor UX | ❌ Rejected |
| **API Key** | Simple | No user attribution, not suitable for interactive UI | ❌ Rejected |

### Decision: Skyscanner SSO (OIDC)

**Rationale**:
- Skyscanner uses Okta or similar for SSO
- OIDC standard with well-supported libraries (`authlib` for Python)
- User identity tied to org credentials
- Authorization via group membership (e.g., "cassini-squad" group)

**Implementation**:
- Frontend: Auth0/Okta SDK for React (handles redirect flow)
- Backend: Verify JWT tokens from OIDC provider
- Authorization: Check `groups` claim in JWT for "cassini-squad"
- Session: JWT stored in httpOnly cookie (XSS protection)

---

## Decision 10: Error Rate Monitoring

### Context
Constitution requires auto-disable automation if error rate exceeds 5% in 1 hour. Need monitoring and circuit breaker.

### Options Evaluated

| Approach | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Custom circuit breaker in code** | Simple, no dependencies | Reinventing the wheel | ❌ Rejected |
| **Metrics + alerting (Prometheus + Alertmanager)** | Standard observability stack | External dependencies | ✅ **Selected** |
| **Database-tracked error rate** | Self-contained | Less observable, no alerting | ❌ Rejected |

### Decision: Prometheus Metrics + Circuit Breaker

**Rationale**:
- Skyscanner likely uses Prometheus for monitoring
- Export metrics: `tickets_processed_total`, `tickets_failed_total`
- Alert rule: `rate(tickets_failed_total[1h]) / rate(tickets_processed_total[1h]) > 0.05`
- On alert → Alertmanager sends webhook to service → service sets `AUTOMATION_ENABLED=false`

**Metrics**:
```python
from prometheus_client import Counter, Gauge

tickets_processed = Counter('tickets_processed_total', 'Total tickets processed')
tickets_failed = Counter('tickets_failed_total', 'Total tickets failed')
automation_enabled = Gauge('automation_enabled', 'Whether automation is enabled')
```

**Circuit Breaker**:
- Service exposes `/circuit-breaker/disable` endpoint
- Alertmanager webhook calls endpoint on 5% error rate
- Endpoint sets `automation_enabled.set(0)` and updates config
- Manual re-enable via dashboard after investigation

---

## Summary of Key Technologies

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | Python 3.11+ | Mature async ecosystem, LLM library support |
| **API Framework** | FastAPI | Async, OpenAPI docs, Pydantic validation |
| **Classification** | Anthropic Claude (Sonnet) | Strong reasoning, structured outputs |
| **Storage** | PostgreSQL 14+ | ACID, JSONB flexibility, append-only triggers |
| **Queue** | Redis (RQ) | Simple, persistent, low ops overhead |
| **Dashboard** | React + Vite + TypeScript | Standard at Skyscanner, fast dev |
| **Testing** | pytest + pytest-asyncio + respx | Python standard, async support, HTTP mocking |
| **Deployment** | Kubernetes on AWS | Skyscanner standard, containerized |
| **Monitoring** | Prometheus + Grafana | Standard observability stack |

---

## Open Questions

1. **Skyscanner Anthropic Contract**: Does Skyscanner have existing Anthropic Enterprise agreement? If not, need to procure or use GPT-4.
2. **Jira Webhook Access**: Who has admin access to configure webhooks in Jira?
3. **Slack App Approval**: What's the approval process for new Slack apps in Skyscanner workspace?
4. **SSO Provider**: Is it Okta, Auth0, or custom OIDC? Need provider endpoint URLs.
5. **Existing Infrastructure**: Does Cassini already run PostgreSQL/Redis? Can we use existing clusters?

**Action**: Engineering lead to answer these during Phase 1 design.
