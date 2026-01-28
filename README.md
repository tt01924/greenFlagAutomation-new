# Green Flag Automation

Automated ticket response system for Cassini Squad at Skyscanner.

## Overview

Green Flag Automation automatically processes Jira tickets labeled "Green-Flag" by:
- Classifying tickets against pre-approved canned responses using LLM
- Auto-responding to tickets with high-confidence matches (>80%)
- Escalating low-confidence or ambiguous tickets to the Green Flag holder via Slack
- Providing a dashboard for oversight, retractions, and reporting

## Quick Start

See the [Quickstart Guide](./specs/001-green-flag-automation/quickstart.md) for detailed setup instructions.

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 14+ (via Docker Compose)
- Redis 7+ (via Docker Compose)

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/Skyscanner/green-flag-automation.git
cd green-flag-automation

# 2. Start infrastructure services
docker-compose up -d

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys (Jira, Slack, Anthropic)

# 4. Setup backend
cd backend
poetry install
poetry run alembic upgrade head

# 5. Start backend API
poetry run uvicorn src.main:app --reload --port 8000

# 6. Setup frontend (in another terminal)
cd frontend
npm install
npm run dev

# 7. Open dashboard
open http://localhost:3000
```

## Project Structure

```
greenFlagAutomation/
├── backend/              # Python FastAPI backend
│   ├── src/             # Application code
│   ├── tests/           # Tests
│   ├── migrations/      # Database migrations
│   └── docker/          # Docker configuration
├── frontend/            # React + TypeScript dashboard
│   └── src/            # Frontend code
├── infra/              # Infrastructure as code
│   ├── k8s/           # Kubernetes manifests
│   ├── terraform/     # Terraform configuration
│   └── prometheus/    # Monitoring configuration
├── docs/               # Additional documentation
└── specs/              # Feature specifications
```

## Architecture

### Technology Stack

- **Backend**: FastAPI (Python 3.11+) with async workers
- **Frontend**: React 18 + TypeScript + Vite
- **Database**: PostgreSQL 14+ with JSONB
- **Queue**: Redis (RQ) for async ticket processing
- **Classification**: Anthropic Claude (Sonnet) with GPT-4 fallback
- **Infrastructure**: Kubernetes + Terraform (AWS RDS, ElastiCache, S3)
- **Monitoring**: Prometheus + Grafana

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Services                            │
│  ┌──────────┐      ┌──────────┐      ┌────────────────────────┐   │
│  │   Jira   │      │  Slack   │      │   Anthropic Claude /   │   │
│  │          │      │          │      │      OpenAI GPT-4      │   │
│  └─────┬────┘      └────▲─────┘      └──────────▲─────────────┘   │
└────────┼────────────────┼────────────────────────┼─────────────────┘
         │ Webhooks       │ Escalations            │ Classification
         │                │                        │
┌────────▼────────────────┴────────────────────────┴─────────────────┐
│                   Kubernetes Cluster (EKS)                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                   API Service (3 replicas)                  │   │
│  │  ┌───────────────┬────────────────┬────────────────────┐   │   │
│  │  │  /webhooks    │    /api/       │   /api/admin       │   │   │
│  │  │   endpoint    │  dashboard     │   kill-switch      │   │   │
│  │  └───────────────┴────────────────┴────────────────────┘   │   │
│  │                          │                                   │   │
│  │                          ▼ Enqueue                           │   │
│  └──────────────────────────┼───────────────────────────────────┘   │
│                              │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │                   Redis Queue (ElastiCache)                   │  │
│  │              ┌─────────────────────────────────┐              │  │
│  │              │   ticket_queue (async jobs)     │              │  │
│  │              └─────────────────────────────────┘              │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                              │                                       │
│                              ▼ Dequeue                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Worker Service (2 replicas)                      │  │
│  │  ┌────────────────┬──────────────────┬───────────────────┐   │  │
│  │  │  Classification │  Auto-Response   │   Escalation      │   │  │
│  │  │     (LLM)      │   (Jira API)     │   (Slack API)     │   │  │
│  │  └────────────────┴──────────────────┴───────────────────┘   │  │
│  │                          │                                     │  │
│  │                          ▼ Store results                       │  │
│  └──────────────────────────┼─────────────────────────────────────┘│
│                              │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │                PostgreSQL Database (RDS)                      │  │
│  │  ┌────────────────┬─────────────────┬────────────────────┐   │  │
│  │  │  audit_logs    │ processed_      │ system_config      │   │  │
│  │  │  (immutable)   │   tickets       │ (feature flags)    │   │  │
│  │  └────────────────┴─────────────────┴────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              CronJobs (Scheduled Tasks)                       │  │
│  │  • Daily Summary (9 AM UTC) → Slack                           │  │
│  │  • Audit Cleanup (Weekly) → S3 Archive                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │         Monitoring (Prometheus + Grafana)                     │  │
│  │  • Ticket processing rate • Error rates • Queue depth         │  │
│  │  • Confidence scores • External service latency               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼ Archive (>90 days)
┌────────────────────────────────────────────────────────────────────┐
│                    S3 Bucket (Audit Archive)                        │
│  • 90-day transition to Glacier • 7-year retention                 │
└────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Jira Webhook** → API receives `issue_created` or `issue_updated` event
2. **API** → Validates webhook signature, enqueues job to Redis
3. **Worker** → Dequeues job, classifies ticket using LLM
4. **Decision**:
   - **High confidence (>80%)**: Post canned response to Jira
   - **Low confidence (<80%)**: Escalate to Slack with reasoning
   - **Sensitive data detected**: Always escalate
   - **Error occurred**: Always escalate (fail-safe)
5. **Audit** → Store immutable audit log entry in PostgreSQL
6. **Metrics** → Record Prometheus metrics (processing time, confidence, action)
7. **Dashboard** → Display processed tickets with retraction capability (5-min window)

## Key Features

### Automated Response (User Story 1 - P1)
- Receives Jira webhooks when tickets are created/updated
- Classifies tickets using LLM against 11 canned responses
- Posts canned response to Jira when confidence >80%
- Detects sensitive data and follow-up tickets

### Human Escalation (User Story 2 - P1)
- Escalates low-confidence tickets to Green Flag holder via Slack
- Provides reasoning and top classification matches
- Includes "Mark as Reviewed" button in Slack message
- Handles edge cases: timeouts, errors, ambiguous matches

### Oversight Dashboard (User Story 3 - P2)
- View all processed tickets with actions and confidence scores
- Retract automated responses within 5-minute window
- View escalated tickets with overdue flags
- Weekly reports with metrics and charts

### Canned Response Management (User Story 4 - P3)
- Update canned responses via PR to config YAML
- 48-hour shadow mode before new responses become active
- Shadow mode logs classifications without posting to Jira

## Safety & Governance

Per [constitution.md](./.specify/memory/constitution.md), the system:
- ✅ Only sends pre-approved canned responses (no AI-generated text)
- ✅ Escalates to human when confidence is low (<80%)
- ✅ Detects sensitive data keywords and escalates immediately
- ✅ Maintains immutable audit logs for 90 days
- ✅ Supports kill switch to disable automation instantly
- ✅ Enters 48-hour shadow mode after canned response changes
- ✅ Never drops tickets (fail-safe: all errors escalate)

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
cd backend
python -m tests.e2e.test_ticket_flow
```

## Backend Deployment (API Only)

The backend can be deployed independently without the frontend dashboard.

### Step 1: Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, and MailHog
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

### Step 2: Configure Environment

```bash
# Copy and edit environment variables
cp .env.example .env

# Required variables:
# - DATABASE_URL (PostgreSQL connection)
# - REDIS_URL (Redis connection)
# - JIRA_API_TOKEN, JIRA_EMAIL, JIRA_BASE_URL
# - SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
# - ANTHROPIC_API_KEY (or OPENAI_API_KEY)
# - JIRA_WEBHOOK_SECRET (generate with: openssl rand -hex 32)
```

### Step 3: Initialize Database

```bash
cd backend

# Install dependencies (requires Poetry)
poetry install

# Run database migrations
poetry run alembic upgrade head

# Verify tables created
# Should see: audit_logs, processed_tickets, system_config
```

### Step 4: Start Backend Services

Open 2 terminals:

**Terminal 1 - API Server:**
```bash
cd backend
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Worker Process:**
```bash
cd backend
poetry run python -m src.workers.ticket_processor_worker
```

### Step 5: Configure Jira Webhook

1. Go to Jira → Settings → System → Webhooks
2. Create new webhook:
   - **URL**: `https://your-domain.com/api/webhooks/jira`
   - **Events**: `issue_created`, `issue_updated`
   - **JQL Filter**: `project = CASSINI AND labels = "Green-Flag"`
   - **Secret**: Use value from JIRA_WEBHOOK_SECRET in .env

### Step 6: Verify Deployment

```bash
# Check health endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/ready

# Check API documentation
open http://localhost:8000/docs

# Send test webhook
curl -X POST http://localhost:8000/api/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=YOUR_SIGNATURE" \
  -d @backend/tests/fixtures/jira_webhook_iam_request.json
```

### Optional: Scheduled Jobs

For daily summaries and audit cleanup, set up cron jobs or Kubernetes CronJobs:

```bash
# Daily summary (run at 9 AM UTC)
python -m src.workers.daily_summary_job

# Audit cleanup (run weekly)
python -m src.workers.audit_cleanup_job
```

### Backend-Only Usage

Without the frontend dashboard, you can:
- Use API endpoints directly (see `/docs` for Swagger UI)
- Query audit_logs table in PostgreSQL
- Monitor logs from API server and worker
- Use curl/Postman for retractions and reports

## Full Stack Deployment

See [deployment documentation](./docs/deployment.md) for production deployment with Kubernetes, Terraform, and frontend dashboard.

## Documentation

### Getting Started
- [Quickstart Guide](./specs/001-green-flag-automation/quickstart.md) - Setup for local development
- [Deployment Guide](./docs/deployment.md) - Production deployment with Kubernetes & Terraform
- [Contributing Guide](./CONTRIBUTING.md) - Development workflow and PR process

### Technical Documentation
- [Feature Specification](./specs/001-green-flag-automation/spec.md) - Detailed requirements and success criteria
- [Implementation Plan](./specs/001-green-flag-automation/plan.md) - Technical design and architecture decisions
- [Data Model](./specs/001-green-flag-automation/data-model.md) - Database schema and relationships
- [API Contracts](./specs/001-green-flag-automation/contracts/) - API request/response specifications
- [Operational Runbook](./docs/runbook.md) - Common issues, debugging, and incident response

### Governance
- [Project Constitution](./.specify/memory/constitution.md) - Core principles and non-negotiable requirements

## Support

- **Slack**: #cassini-squad
- **Email**: cassini@skyscanner.net
- **Jira**: Create ticket with label "Green-Flag-Automation"

## License

Internal Skyscanner project.
