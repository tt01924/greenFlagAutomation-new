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
poetry shell
alembic upgrade head

# 5. Start backend API
uvicorn src.main:app --reload --port 8000

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

- **Backend**: FastAPI (Python 3.11+) with async workers
- **Frontend**: React 18 + TypeScript + Vite
- **Database**: PostgreSQL 14+ with JSONB
- **Queue**: Redis (RQ) for async ticket processing
- **Classification**: Anthropic Claude (Sonnet) with GPT-4 fallback
- **Infrastructure**: Kubernetes + Terraform

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

## Deployment

See [deployment documentation](./docs/deployment.md) for production deployment instructions.

## Documentation

- [Feature Specification](./specs/001-green-flag-automation/spec.md)
- [Implementation Plan](./specs/001-green-flag-automation/plan.md)
- [Quickstart Guide](./specs/001-green-flag-automation/quickstart.md)
- [Data Model](./specs/001-green-flag-automation/data-model.md)
- [API Contracts](./specs/001-green-flag-automation/contracts/)

## Support

- **Slack**: #cassini-squad
- **Email**: cassini@skyscanner.net
- **Jira**: Create ticket with label "Green-Flag-Automation"

## License

Internal Skyscanner project.
