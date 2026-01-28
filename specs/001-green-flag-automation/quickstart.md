# Quickstart: Green Flag Ticket Automation

**Feature**: Green Flag Ticket Automation
**Date**: 2026-01-27
**Audience**: Developers setting up local development environment

## Overview

This guide walks you through setting up the Green Flag automation system on your local machine for development and testing.

---

## Prerequisites

### Required Tools

- **Python 3.11+**: `python3 --version`
- **Poetry** (dependency management): `curl -sSL https://install.python-poetry.org | python3 -`
- **Node.js 18+** (for dashboard): `node --version`
- **Docker & Docker Compose**: `docker --version && docker-compose --version`
- **PostgreSQL 14+**: Via Docker Compose (included)
- **Redis 7+**: Via Docker Compose (included)

### External Service Accounts

You'll need API keys/credentials for:

1. **Jira Cloud**: [Create API token](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Email: your@skyscanner.net
   - API Token: [generated token]

2. **Slack Bot**: [Create Slack app](https://api.slack.com/apps)
   - Bot Token Scopes: `chat:write`, `users:read`, `users:read.email`
   - Install app to workspace → copy Bot Token

3. **Anthropic API**: [Get API key](https://console.anthropic.com/)
   - Create account → Generate API key
   - Note: Can use GPT-4 as fallback (OpenAI API key)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/Skyscanner/green-flag-automation.git
cd green-flag-automation

# Checkout feature branch for development
git checkout 001-green-flag-automation
```

---

## Step 2: Configure Environment

### Backend Configuration

Create `.env` file in project root:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Database (Docker Compose will start PostgreSQL)
DATABASE_URL=postgresql://green_flag:green_flag_dev@localhost:5432/green_flag_automation

# Redis (Docker Compose will start Redis)
REDIS_URL=redis://localhost:6379/0

# Jira API
JIRA_BASE_URL=https://skyscanner.atlassian.net
JIRA_EMAIL=your@skyscanner.net
JIRA_API_TOKEN=your_jira_api_token_here
JIRA_WEBHOOK_SECRET=generate_random_secret_here  # Use: openssl rand -hex 32

# Slack API
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_SIGNING_SECRET=your_slack_signing_secret_here

# LLM Provider (Anthropic Claude)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
# Optional fallback to OpenAI
# OPENAI_API_KEY=sk-your-openai-api-key-here

# Email (for daily summaries - use MailHog for local dev)
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_FROM=green-flag-bot@skyscanner.net

# Application Settings
ENVIRONMENT=development
AUTOMATION_ENABLED=true
LOG_LEVEL=DEBUG

# Dashboard URL (for links in Slack messages)
DASHBOARD_URL=http://localhost:3000

# SSO (not needed for local dev)
# OIDC_ISSUER=https://skyscanner.okta.com
# OIDC_CLIENT_ID=your_client_id
# OIDC_CLIENT_SECRET=your_client_secret
```

**Generate Webhook Secret**:
```bash
openssl rand -hex 32
```

---

## Step 3: Start Infrastructure Services

Start PostgreSQL, Redis, and MailHog (email testing):

```bash
docker-compose up -d

# Check services are running
docker-compose ps
```

Expected output:
```
NAME                         STATUS
green-flag-postgres          Up (healthy)
green-flag-redis             Up
green-flag-mailhog           Up 1025/tcp, 8025/tcp
```

---

## Step 4: Setup Backend

### Install Dependencies

```bash
cd backend
poetry install
```

### Initialize Database

Create tables and run migrations:

```bash
# Activate virtual environment
poetry shell

# Run database migrations
alembic upgrade head

# Load initial canned responses (seed data)
python -m src.scripts.seed_canned_responses
```

Expected output:
```
✅ Database migrated to latest version (rev: abc123)
✅ Loaded 11 canned responses from config/canned_responses.yaml
```

### Verify Database

```bash
# Connect to PostgreSQL
docker exec -it green-flag-postgres psql -U green_flag -d green_flag_automation

# Check tables
\dt
# Expected: audit_logs, processed_tickets, system_config, alembic_version

# Check canned responses loaded correctly
SELECT version, jsonb_array_length(config->'canned_responses') AS response_count
FROM system_config WHERE id = 1;

# Exit psql
\q
```

---

## Step 5: Run Backend Services

Open 3 terminal windows:

### Terminal 1: API Server (FastAPI)

```bash
cd backend
poetry shell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`
API docs (Swagger): `http://localhost:8000/docs`

### Terminal 2: Ticket Processor Worker

```bash
cd backend
poetry shell
python -m src.workers.ticket_processor_worker
```

Worker will consume from Redis queue and process tickets.

### Terminal 3: Scheduled Jobs (Optional)

For testing daily summary and cleanup jobs:

```bash
cd backend
poetry shell

# Run daily summary manually
python -m src.workers.daily_summary_job

# Run audit cleanup manually (archives logs >90 days)
python -m src.workers.audit_cleanup_job
```

---

## Step 6: Setup Frontend Dashboard

### Install Dependencies

```bash
cd frontend
npm install
```

### Configure Frontend

Create `frontend/.env.local`:

```bash
VITE_API_URL=http://localhost:8000/api
VITE_ENABLE_SSO=false  # Disable SSO for local dev
```

### Start Development Server

```bash
npm run dev
```

Dashboard will be available at: `http://localhost:3000`

---

## Step 7: Test End-to-End Flow

### Option A: Simulate Jira Webhook

Create a test ticket webhook payload:

```bash
cd backend
poetry shell

# Run E2E test script (creates fake Jira webhook)
python -m tests.e2e.test_ticket_flow
```

Expected output:
```
✅ Jira webhook received (202)
✅ Ticket queued in Redis
✅ Worker picked up ticket
✅ Classification complete: iam-request (confidence: 0.92)
✅ Response posted to Jira (mocked)
✅ Audit log created
```

### Option B: Send Webhook Manually

```bash
curl -X POST http://localhost:8000/api/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$(echo -n '{}' | openssl dgst -sha256 -hmac 'YOUR_WEBHOOK_SECRET' -binary | xxd -p)" \
  -d @tests/fixtures/jira_webhook_iam_request.json
```

Response:
```json
{
  "status": "queued",
  "ticket_id": "12345678"
}
```

### Option C: Use Ngrok for Real Jira Webhooks

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
```

Copy the `https://` URL (e.g., `https://abc123.ngrok.io`) and configure in Jira:

1. Go to Jira → Settings → System → Webhooks
2. Create webhook:
   - URL: `https://abc123.ngrok.io/api/webhooks/jira`
   - Events: `issue_created`, `issue_updated`
   - JQL Filter: `project = CASSINI AND labels = "Green-Flag"`
3. Create a test ticket in Jira with label "Green-Flag"
4. Watch logs in Terminal 1 and 2

---

## Step 8: View Results in Dashboard

1. Open dashboard: `http://localhost:3000`
2. Navigate to "Tickets" page
3. See processed ticket with:
   - Ticket key (e.g., CASSINI-1234)
   - Action (auto_respond or escalate)
   - Confidence score
   - Timestamp
4. Click ticket to view details and audit history
5. Try "Retract" button (only works within 5 min)

---

## Step 9: Test Escalation Flow

Create a ticket that will escalate (low confidence):

```bash
curl -X POST http://localhost:8000/api/webhooks/jira \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/jira_webhook_ambiguous.json
```

Expected:
- No Jira response posted
- Slack message sent to Green Flag holder (check MailHog if using email fallback)
- Ticket appears in "Escalations" tab in dashboard

**View Escalation Slack Message**:
- Open MailHog: `http://localhost:8025`
- See email with escalation details (if Slack unavailable)

---

## Step 10: Test Kill Switch

### Via API

```bash
curl -X POST http://localhost:8000/api/admin/kill-switch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fake-token-for-local-dev" \
  -d '{"enabled": false, "reason": "Testing kill switch"}'
```

Response:
```json
{
  "automation_enabled": false,
  "updated_at": "2026-01-27T12:00:00Z"
}
```

### Via Dashboard

1. Open dashboard: `http://localhost:3000/settings`
2. Click "Disable Automation" button
3. Enter reason: "Testing"
4. Confirm

### Verify

Send another webhook - ticket should be escalated with reason "Automation disabled (kill switch)".

---

## Step 11: Test Shadow Mode

### Activate Shadow Mode

Edit `backend/src/config/canned_responses.yaml`:

```yaml
version: "1.1.0"
activated_at: "2026-01-27T12:00:00Z"  # Set to now
shadow_mode_hours: 48
```

Restart backend (Ctrl+C in Terminal 1, then `uvicorn...` again).

### Send Test Ticket

```bash
curl -X POST http://localhost:8000/api/webhooks/jira \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/jira_webhook_iam_request.json
```

Expected:
- Classification runs
- Audit log created with `action='shadow'`
- No Jira response posted
- Dashboard shows "Shadow Mode Active" banner

---

## Development Workflows

### Running Tests

```bash
cd backend
poetry shell

# Unit tests
pytest tests/unit

# Integration tests (requires Docker services running)
pytest tests/integration

# Contract tests (mocks external APIs)
pytest tests/contract

# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Database Migrations

Create a new migration:

```bash
cd backend
poetry shell

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to audit_logs"

# Review generated migration in alembic/versions/
# Edit if needed, then apply:
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Adding New Canned Response

1. Edit `backend/src/config/canned_responses.yaml`:
   ```yaml
   - id: "new-response"
     name: "New Response Category"
     response: "Response template with {{issueReporter}}"
     keywords:
       - keyword1
       - keyword2
   ```

2. Update version and `activated_at`:
   ```yaml
   version: "1.2.0"
   activated_at: "2026-01-28T10:00:00Z"
   ```

3. Restart backend → enters 48h shadow mode
4. After 48h, new response becomes active

### Viewing Logs

```bash
# API server logs
# (in Terminal 1 where uvicorn is running)

# Worker logs
# (in Terminal 2 where worker is running)

# PostgreSQL logs
docker logs -f green-flag-postgres

# Redis logs
docker logs -f green-flag-redis
```

### Debugging Classification

Enable LLM request/response logging:

```bash
# In .env
LOG_LEVEL=DEBUG
LLM_DEBUG=true
```

Restart backend. LLM prompts and responses will be logged.

---

## Troubleshooting

### Issue: "Database connection failed"

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps green-flag-postgres

# Check connection
docker exec -it green-flag-postgres pg_isready

# Check DATABASE_URL in .env matches Docker Compose
```

### Issue: "Redis connection refused"

**Solution**:
```bash
# Check Redis is running
docker-compose ps green-flag-redis

# Test connection
redis-cli -h localhost -p 6379 ping
# Expected: PONG

# Check REDIS_URL in .env
```

### Issue: "Jira API authentication failed"

**Solution**:
```bash
# Verify API token is valid
curl -u your@skyscanner.net:YOUR_API_TOKEN \
  https://skyscanner.atlassian.net/rest/api/3/myself

# If 401: regenerate API token in Jira
```

### Issue: "Anthropic API key invalid"

**Solution**:
```bash
# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5-20250929","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# If 401: check API key in console.anthropic.com
```

### Issue: "Worker not processing tickets"

**Solution**:
```bash
# Check Redis queue
redis-cli -h localhost -p 6379
> LLEN green_flag_tickets
# Should show queued tickets

# Check worker logs for errors
# (in Terminal 2)

# Restart worker (Ctrl+C, then python -m src.workers...)
```

### Issue: "Dashboard not loading"

**Solution**:
```bash
# Check frontend dev server is running
# (in Terminal 3: npm run dev)

# Check API_URL in frontend/.env.local
# Should be: http://localhost:8000/api

# Check browser console for errors
# Open DevTools → Console tab
```

---

## Next Steps

Once local development is working:

1. **Write tests** for new features:
   ```bash
   cd backend/tests/unit
   # Add test files
   ```

2. **Run linters**:
   ```bash
   cd backend
   poetry run black src tests
   poetry run mypy src
   poetry run pylint src
   ```

3. **Build Docker image**:
   ```bash
   cd backend
   docker build -t green-flag-automation:local -f docker/Dockerfile .
   ```

4. **Deploy to staging** (requires Skyscanner infra access):
   ```bash
   cd infra/k8s
   kubectl apply -f staging/ --namespace=cassini-staging
   ```

---

## Additional Resources

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Feature Specification**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contracts**: [contracts/](./contracts/)

## Support

For questions or issues:
- **Slack**: #cassini-squad
- **Jira**: Create ticket with label "Green-Flag-Automation"
- **Email**: cassini@skyscanner.net
