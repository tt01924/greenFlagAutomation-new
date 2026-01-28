# Implementation Plan: Green Flag Ticket Automation

**Branch**: `001-green-flag-automation` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-green-flag-automation/spec.md`

## Summary

Build a secure, observable, testable service that automates Cassini's Green Flag ticket triage by classifying Jira tickets against a catalog of pre-approved canned responses. When confidence is high (>80%), the system posts the matched canned response automatically. When confidence is low or ambiguous, it escalates to the Green Flag holder via Slack with reasoning. The system includes a dashboard for oversight, audit logging for compliance, and fail-safe mechanisms (kill switch, shadow mode, error rate monitoring) per the constitution.

**Technical Approach**: Event-driven microservice architecture with Jira webhook ingestion, LLM-based classification, stateful processing with audit trail, and web dashboard for oversight. All operations are logged to immutable audit storage with 90-day retention.

## Technical Context

**Language/Version**: Python 3.11+ (mature async ecosystem, strong LLM/NLP library support, Skyscanner standard)
**Primary Dependencies**:
- FastAPI (async REST API and webhooks)
- OpenAI SDK / Anthropic SDK (for classification LLM calls)
- Jira Python SDK (atlassian-python-api)
- Slack SDK (slack-bolt)
- SQLAlchemy (ORM for audit logs and state)
- Pydantic (validation and configuration)

**Storage**: PostgreSQL 14+ (audit logs, processing state, shadow mode data) with append-only audit table
**Testing**: pytest (unit, integration, contract), pytest-asyncio (async test support), respx (HTTP mocking)
**Target Platform**: Kubernetes on AWS (Skyscanner infra), containerized with Docker
**Project Type**: Backend service + lightweight web dashboard (single repo, monorepo structure)
**Performance Goals**:
- <5 min ticket processing latency (P95)
- <30 sec LLM classification response time (P95)
- <3 sec dashboard page load
- Support 100 tickets/day concurrent processing

**Constraints**:
- MUST process all tickets (zero loss) even during outages
- MUST complete audit log writes before posting responses
- Classification service timeout: 30 seconds hard limit
- Shadow mode: 48-hour mandatory delay after config changes
- Retraction window: 5 minutes after response posting
- False positive rate: <2% (measured by retractions)

**Scale/Scope**:
- Initial: 11 canned responses, ~50-100 tickets/week
- 1 year: ~20 canned responses, ~200-300 tickets/week
- 3 concurrent users (Green Flag holders across time zones)
- 90-day audit log retention (~13k records)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ System Authority Requirements

| Requirement | Implementation Approach |
|-------------|------------------------|
| Only send pre-approved canned responses | Canned responses stored in version-controlled YAML config. No runtime modification. Template engine for variable substitution only. |
| Escalate if confidence not high | Confidence threshold: 80%. Ambiguity threshold: 10% (multiple matches within 10%). Hard-coded, no learning. |
| Log every ticket and decision | Append-only `audit_logs` table with ticket snapshot, confidence scores, decision, timestamp. No updates/deletes. |
| Preserve original ticket content | Full ticket JSON stored in audit log before any processing. |
| Notify on escalation immediately | Slack webhook call with <5s timeout. Retry queue if Slack unavailable. |
| Include confidence reasoning | LLM prompt instructs model to provide reasoning. Captured in audit log and Slack message. |
| MUST NOT compose custom responses | Code only selects from config file. No LLM response generation, only classification. |
| MUST NOT process sensitive data | Pre-classification scan for keywords: `credentials`, `token`, `password`, `key`, `secret`, `API key`. Immediate escalation if match. |
| Fail safe if integrations down | Queue-based retry for Jira comments. Escalate via Slack if Jira unavailable for >5 min. |
| MUST NOT respond to follow-ups | Track `processed_tickets` table. If ticket ID exists, escalate. Detect by checking Jira comment history. |

### ✅ Safety & Governance Requirements

| Requirement | Implementation Approach |
|-------------|------------------------|
| Audit logs with ticket ID, timestamp, canned response, confidence, full text | `audit_logs` table schema: `id`, `ticket_id`, `ticket_snapshot` (JSONB), `confidence_scores` (JSONB), `matched_response_id`, `action`, `reasoning`, `timestamp`, `system_version`. |
| 90-day retention | Automated cleanup job (cron) archives logs >90 days to cold storage (S3). Not deleted, just archived. |
| Daily summary to Green Flag holder | Scheduled job at 9 AM UTC: queries previous 24h, generates summary (auto/escalated counts, avg confidence), emails via SES. |
| Automated responses clearly labeled | Signature appended to every response: "🤖 Automated response from Cassini Green Flag Bot. If this doesn't help, reply here to reach a human." |
| Instructions to reach human | In signature (see above). |
| One-click retract within 5 min | Dashboard "Retract" button available for responses <5 min old. Adds Jira comment: "This automated response has been retracted, a human will respond shortly." Edits original comment with strikethrough. |
| Manual kill switch | Environment variable `AUTOMATION_ENABLED` (default: true). Dashboard button sets to false, updates config map, reloads service. Accessible via dashboard auth (Cassini squad members only). |
| 48-hour shadow mode after config change | Config file has `version` and `activated_at` timestamp. On merge, system enters shadow mode: processes tickets but logs decisions without posting. After 48h, auto-activates. |

### ✅ Human Oversight Requirements

| Requirement | Implementation Approach |
|-------------|------------------------|
| Escalated tickets reviewed within 4h | Slack escalation message includes ticket link and "Mark as Reviewed" button. Dashboard tracks review status. |
| Weekly accuracy reports | Dashboard page: "Weekly Report" with charts for auto/escalate ratio, confidence distribution, retraction rate. |
| Customer complaints reviewed within 24h | Manual process (out of scope for automation). Dashboard alerts if retraction rate >2% in 24h. |
| System behavior reviewed after updates | Shadow mode enforces 48h review period. |

### ✅ Non-Functional Requirements

| Requirement | Implementation Approach |
|-------------|------------------------|
| Process tickets within 5 min | Webhook ingests to processing queue (Redis). Worker processes async. Monitoring alerts if P95 >5 min. |
| NOT single point of failure | Manual Jira workflow remains unchanged. Automation is additive. If service down, tickets route to Green Flag holder as before. |
| False positive rate <2% | Track retractions in `audit_logs`. Daily job computes rate. If >2% in 24h, auto-disable automation and alert. |
| Transparency | Signature on every response (see Safety above). |
| Data Privacy | Audit logs in secure PostgreSQL. No external sharing. Archive to S3 with encryption. Delete after 90 days from archive. |

### 🔍 Constitution Violations Requiring Justification

**None**. All requirements are implementable within standard microservice architecture and operational best practices.

## Project Structure

### Documentation (this feature)

```text
specs/001-green-flag-automation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: Technology choices and rationale
├── data-model.md        # Phase 1 output: Entity schemas and relationships
├── quickstart.md        # Phase 1 output: Local development setup
├── contracts/           # Phase 1 output: API contracts and schemas
│   ├── openapi.yaml     # REST API spec for dashboard and webhooks
│   ├── jira-webhook.json    # Jira webhook payload schema
│   └── slack-message.json   # Slack notification schema
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Backend service + worker + dashboard
backend/
├── src/
│   ├── models/               # SQLAlchemy models (Ticket, AuditLog, CannedResponse, etc.)
│   ├── services/             # Business logic modules
│   │   ├── classifier.py     # LLM-based ticket classification
│   │   ├── jira_client.py    # Jira API wrapper
│   │   ├── slack_client.py   # Slack API wrapper
│   │   ├── processor.py      # Core ticket processing orchestration
│   │   ├── audit_logger.py   # Immutable audit log writer
│   │   └── shadow_mode.py    # Shadow mode state management
│   ├── api/                  # FastAPI routes
│   │   ├── webhooks.py       # Jira webhook endpoint
│   │   ├── dashboard.py      # Dashboard API (list, retract, kill switch)
│   │   └── health.py         # Health check endpoints
│   ├── workers/              # Background job processors
│   │   ├── ticket_processor_worker.py   # Queue consumer for ticket processing
│   │   ├── daily_summary_job.py         # Scheduled daily summary
│   │   └── audit_cleanup_job.py         # 90-day archive job
│   ├── config/               # Configuration and canned responses
│   │   ├── canned_responses.yaml        # The 11 canned responses catalog
│   │   ├── settings.py                  # Pydantic settings (env vars)
│   │   └── prompts.py                   # LLM system prompts
│   └── main.py               # FastAPI app entrypoint
│
├── tests/
│   ├── contract/             # Contract tests against external APIs (Jira, Slack, LLM)
│   ├── integration/          # Integration tests (DB + services)
│   └── unit/                 # Unit tests for individual modules
│
├── migrations/               # Alembic database migrations
│   └── versions/
│
└── docker/
    ├── Dockerfile            # Service container
    └── docker-compose.yml    # Local development stack (PostgreSQL, Redis, service)

# Frontend dashboard (lightweight)
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── TicketList.tsx    # List of processed tickets
│   │   ├── TicketDetail.tsx  # Detail view with retract button
│   │   ├── EscalationList.tsx # Escalated tickets view
│   │   ├── KillSwitch.tsx    # Kill switch control
│   │   └── WeeklyReport.tsx  # Weekly accuracy report charts
│   ├── pages/                # Page-level components
│   │   ├── Dashboard.tsx     # Main dashboard page
│   │   └── Reports.tsx       # Weekly reports page
│   ├── services/             # API client
│   │   └── api.ts            # Fetch wrapper for backend API
│   └── App.tsx               # Root component
│
└── tests/
    └── components/           # Component tests (Vitest)

# Infrastructure
infra/
├── k8s/                      # Kubernetes manifests
│   ├── deployment.yaml       # Service deployment
│   ├── service.yaml          # Load balancer
│   ├── configmap.yaml        # Canned responses config
│   ├── secrets.yaml          # API keys (Jira, Slack, LLM)
│   └── cronjob.yaml          # Daily summary and cleanup jobs
└── terraform/                # AWS resources (RDS, S3, SES)
    ├── main.tf
    └── variables.tf

# Root-level
README.md                     # Project overview and quickstart
pyproject.toml                # Python dependencies (Poetry)
package.json                  # Frontend dependencies (npm)
.env.example                  # Environment variable template
docker-compose.yml            # Local dev stack
```

**Structure Decision**: Monorepo with backend (Python/FastAPI) and frontend (React/TypeScript) in separate directories. This structure supports:
- Shared infrastructure (K8s, Docker Compose) at root
- Independent backend/frontend deployment if needed
- Clear separation between API service, worker processes, and web UI
- Co-location of related code (canned responses config lives with backend logic)

Backend uses standard FastAPI layered architecture: API routes → Services (business logic) → Models (data access). Workers run as separate processes consuming from Redis queue.

Frontend is a simple React SPA served via CDN or static hosting, calling backend API for data.

## Complexity Tracking

No constitutional violations requiring justification. All requirements are satisfied with standard patterns:
- FastAPI for API and webhook handling
- SQLAlchemy for audit logs with append-only pattern
- Background workers for async processing (standard queue-based pattern)
- LLM SDK for classification (standard integration, no custom ML training)
- Config-driven canned responses (no runtime code generation)
- Shadow mode via timestamp-based state machine (standard feature flag pattern)

---

## Phase 0: Research & Technology Decisions

**Status**: ✅ Complete (see [research.md](./research.md))

### Key Decisions

1. **Classification Approach**: LLM-based semantic matching vs. keyword/regex
   - **Decision**: Use LLM (Claude or GPT-4) with few-shot prompting
   - **Rationale**: Canned responses have nuanced differences (e.g., "Cortex bug" vs "Cortex feature request"). LLMs excel at semantic understanding. More robust than keyword matching.
   - **Alternatives Considered**: TF-IDF + cosine similarity (rejected: poor semantic understanding), BERT embeddings + KNN (rejected: requires training data, complexity)

2. **Storage for Audit Logs**: Relational vs. time-series DB
   - **Decision**: PostgreSQL with append-only table and JSONB columns
   - **Rationale**: Strong consistency, ACID guarantees, immutable audit trail with triggers. JSONB for flexible ticket snapshots. Skyscanner has managed RDS.
   - **Alternatives Considered**: DynamoDB (rejected: eventual consistency), TimescaleDB (rejected: overkill for 13k records/year)

3. **Queue for Ticket Processing**: Redis vs. RabbitMQ vs. SQS
   - **Decision**: Redis with Bull/BullMQ (Python: RQ or Celery)
   - **Rationale**: Simple, fast, good enough for 100 tickets/day. Persistence for fail-safe. Lower ops overhead than RabbitMQ.
   - **Alternatives Considered**: SQS (rejected: higher latency, AWS lock-in), Kafka (rejected: overkill)

4. **Dashboard Framework**: React vs. Svelte vs. Server-rendered
   - **Decision**: React with Vite + TypeScript
   - **Rationale**: Standard at Skyscanner, large ecosystem, good for simple CRUD dashboards. Vite for fast dev experience.
   - **Alternatives Considered**: Server-rendered with Jinja (rejected: need for real-time updates and interactivity)

5. **LLM Provider**: OpenAI vs. Anthropic vs. self-hosted
   - **Decision**: Anthropic Claude (Sonnet)
   - **Rationale**: Strong reasoning capabilities, lower hallucination rate, good for classification tasks. Skyscanner may have existing contract.
   - **Alternatives Considered**: GPT-4 (viable fallback), self-hosted Llama (rejected: ops overhead, latency)

---

## Phase 1: Design & Contracts

**Status**: ✅ Complete (see artifacts below)

### Outputs

- [data-model.md](./data-model.md) - Entity schemas and relationships
- [contracts/openapi.yaml](./contracts/openapi.yaml) - REST API specification
- [contracts/jira-webhook.json](./contracts/jira-webhook.json) - Jira webhook payload schema
- [contracts/slack-message.json](./contracts/slack-message.json) - Slack notification schema
- [quickstart.md](./quickstart.md) - Local development setup instructions

### Key Design Decisions

1. **State Machine for Shadow Mode**: Config version has `activated_at` timestamp. On load, if `now() - activated_at < 48h`, run in shadow mode.

2. **Confidence Scoring**: LLM returns JSON with `{response_id: string, confidence: float, reasoning: string}`. If confidence <80% or multiple within 10%, escalate.

3. **Retraction Mechanism**: Store response comment ID in audit log. Retract = edit comment with strikethrough + add new comment. Only allowed if `now() - posted_at < 5min`.

4. **Kill Switch**: Environment variable `AUTOMATION_ENABLED`. Dashboard updates ConfigMap and triggers rolling restart (or hot reload via signal).

5. **Fail-Safe**: All external calls wrapped in try-catch. Jira failures → queue for retry. Slack failures → fallback email to on-call. Never drop tickets.

---

## Next Steps

This plan is now complete. Proceed with:

1. **`/speckit.tasks`** - Generate task breakdown from this plan
2. **`/speckit.implement`** - Execute tasks and build the system

## Verification Checklist

- [x] Technical Context filled with concrete choices
- [x] Constitution Check shows all requirements satisfied
- [x] Project structure defined with real paths
- [x] Phase 0 research completed with rationale
- [x] Phase 1 design artifacts generated
- [x] No NEEDS CLARIFICATION markers remaining
- [x] No constitutional violations requiring justification
