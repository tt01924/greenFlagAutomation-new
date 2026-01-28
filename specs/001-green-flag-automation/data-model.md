# Data Model: Green Flag Ticket Automation

**Feature**: Green Flag Ticket Automation
**Date**: 2026-01-27
**Status**: Complete

## Overview

This document defines the data entities, schemas, relationships, and validation rules for the Green Flag automation system. All entities are designed to support constitutional requirements for auditability, immutability, and fail-safe operation.

---

## Entity Relationship Diagram

```
┌─────────────────┐
│  CannedResponse │
│  (Config File)  │
└────────┬────────┘
         │
         │ references
         ▼
┌─────────────────┐      ┌──────────────────┐
│   AuditLog      │      │ProcessedTicket   │
│  (append-only)  │◀─────│  (tracking)      │
└────────┬────────┘ refs └──────────────────┘
         │
         │ references
         ▼
┌─────────────────┐
│   Escalation    │
│ (derived view)  │
└─────────────────┘
```

**Key Relationships**:
- `AuditLog` references `CannedResponse` by ID (if matched)
- `ProcessedTicket` tracks which tickets have been handled (prevents re-processing)
- `Escalation` is a filtered view of `AuditLog` where `action='escalate'`

---

## Entities

### 1. CannedResponse (Configuration)

**Source**: YAML configuration file (`backend/src/config/canned_responses.yaml`)
**Purpose**: Pre-approved response templates with metadata for classification
**Mutability**: Immutable at runtime. Changes require PR + 48h shadow mode.

**Schema**:
```yaml
version: string                  # Semantic version (e.g., "1.2.0")
activated_at: datetime (ISO8601) # When this version became active
shadow_mode_hours: integer       # Duration of shadow mode (default: 48)

canned_responses:
  - id: string                   # Unique identifier (kebab-case)
    name: string                 # Human-readable name
    category: string             # Optional category for grouping
    response: string             # Template with {{variables}}
    keywords: list[string]       # Keywords for LLM classification context
    active: boolean              # Whether response is active (default: true)
```

**Example**:
```yaml
version: "1.0.0"
activated_at: "2026-01-27T10:00:00Z"
shadow_mode_hours: 48

canned_responses:
  - id: "iam-request"
    name: "Cassini - IAM request"
    category: "AWS"
    response: |
      Hey {{issueReporter}}, if you could provide the account, project role and the IAM policy you'd like in JSON format I can review and apply if it looks sensible.

      For the policy - there are examples available online through a quick google search, there's also the AWS Policy Generator if it's easier doing it via a GUI, and AI can also provide a policy (although sometimes these can be overly permissive and in advanced cases it can even make up AWS services or actions).
    keywords:
      - IAM
      - permissions
      - policy
      - account access
      - AWS
    active: true

  - id: "cortex-scorecard-ownership"
    name: "CAS - Cortex Scorecard Ownership"
    category: "Cortex"
    response: |
      Hello {{issueReporter}}!

      Cassini own the Cortex platform but not scorecards. If you need an exemption, please reach out directly to the scorecard owner. You can find the scorecard owners here https://github.com/Skyscanner/production-standards/blob/main/STANDARDS_OWNERS.md.
    keywords:
      - Cortex
      - scorecard
      - exemption
      - ownership
    active: true
```

**Validation Rules**:
- `id` must be unique across all responses
- `id` must match regex: `^[a-z0-9-]+$`
- `version` must follow semver format
- `activated_at` must be valid ISO8601 timestamp
- `response` must contain valid template variables only: `{{issueReporter}}`, `{{issueAssignee}}`
- `keywords` list must not be empty
- At least one response must have `active: true`

**Template Variables**:
- `{{issueReporter}}`: Jira username or display name of ticket creator
- `{{issueAssignee}}`: Jira username or display name of ticket assignee

---

### 2. AuditLog (Database Table)

**Purpose**: Immutable record of every ticket processed by the system
**Table**: `audit_logs`
**Constitutional Requirement**: FR-013, FR-014 (log every decision, 90-day retention)

**Schema** (PostgreSQL):
```sql
CREATE TABLE audit_logs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ticket identification
    ticket_id VARCHAR(50) NOT NULL,
    ticket_key VARCHAR(50) NOT NULL,  -- e.g., "CASSINI-1234"

    -- Ticket snapshot (full Jira payload)
    ticket_snapshot JSONB NOT NULL,

    -- Classification results
    confidence_scores JSONB NOT NULL,  -- {response_id: {confidence: float, reasoning: string}}
    matched_response_id VARCHAR(100),  -- NULL if escalated

    -- Decision and action
    action VARCHAR(20) NOT NULL,       -- 'auto_respond' | 'escalate' | 'shadow'
    escalation_reason VARCHAR(500),    -- NULL if action='auto_respond'

    -- Jira interaction
    comment_id VARCHAR(50),            -- Jira comment ID if response posted
    comment_posted_at TIMESTAMP,       -- When response was posted
    retracted_at TIMESTAMP,            -- NULL if not retracted
    retracted_by VARCHAR(100),         -- User who retracted (NULL if not retracted)

    -- System metadata
    system_version VARCHAR(20) NOT NULL,    -- e.g., "v1.2.3"
    config_version VARCHAR(20) NOT NULL,    -- Canned response config version
    processing_duration_ms INTEGER,         -- Time taken to process

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_action CHECK (action IN ('auto_respond', 'escalate', 'shadow')),
    CONSTRAINT escalation_reason_required CHECK (
        (action = 'escalate' AND escalation_reason IS NOT NULL) OR
        (action != 'escalate')
    ),
    CONSTRAINT matched_response_required CHECK (
        (action = 'auto_respond' AND matched_response_id IS NOT NULL) OR
        (action != 'auto_respond')
    )
);

-- Indexes for performance
CREATE INDEX idx_audit_logs_ticket_id ON audit_logs(ticket_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_retracted_at ON audit_logs(retracted_at) WHERE retracted_at IS NOT NULL;

-- Trigger to prevent updates/deletes (immutability)
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

**Field Descriptions**:
- `ticket_snapshot`: Full Jira webhook payload (preserves original ticket state)
- `confidence_scores`: JSON object mapping each canned response ID to its confidence score and LLM reasoning
  ```json
  {
    "iam-request": {"confidence": 0.85, "reasoning": "Clear mention of IAM policy needed"},
    "cql-request": {"confidence": 0.12, "reasoning": "No Cortex context found"}
  }
  ```
- `escalation_reason`: Human-readable explanation (e.g., "Confidence below threshold", "Ambiguous match", "Sensitive data detected")
- `action='shadow'`: Logged during 48h shadow mode (decision made but not executed)

**Validation Rules**:
- `ticket_id` and `ticket_key` must not be empty
- `confidence_scores` must be valid JSON with at least one entry
- `action='auto_respond'` requires `matched_response_id` and `comment_id`
- `action='escalate'` requires `escalation_reason`
- `retracted_at` can only be set if `comment_posted_at` is set
- `retracted_at` must be within 5 minutes of `comment_posted_at` (enforced by application logic)

**Sample Row**:
```sql
INSERT INTO audit_logs (
    ticket_id, ticket_key, ticket_snapshot, confidence_scores,
    matched_response_id, action, comment_id, system_version, config_version
) VALUES (
    '12345678',
    'CASSINI-1234',
    '{"fields": {"summary": "Need IAM access", ...}}'::jsonb,
    '{"iam-request": {"confidence": 0.92, "reasoning": "Clear IAM request"}}'::jsonb,
    'iam-request',
    'auto_respond',
    '67890',
    'v1.0.0',
    '1.0.0'
);
```

---

### 3. ProcessedTicket (Database Table)

**Purpose**: Track which tickets have been processed to prevent re-processing follow-ups
**Table**: `processed_tickets`
**Constitutional Requirement**: FR-012 (MUST NOT respond to follow-ups)

**Schema** (PostgreSQL):
```sql
CREATE TABLE processed_tickets (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Ticket identification
    ticket_id VARCHAR(50) NOT NULL UNIQUE,
    ticket_key VARCHAR(50) NOT NULL,

    -- Processing metadata
    first_processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    times_seen INTEGER NOT NULL DEFAULT 1,

    -- Index for fast lookup
    INDEX idx_processed_tickets_ticket_id (ticket_id)
);
```

**Usage**:
- Before processing a ticket, check if `ticket_id` exists in `processed_tickets`
- If exists → escalate with reason "Follow-up detected on previously processed ticket"
- If not exists → insert row and proceed with processing
- On webhook receiving updated ticket → update `last_seen_at` and increment `times_seen`

**Retention**: Same as `audit_logs` (90 days), cleaned up in tandem

---

### 4. SystemConfig (Database Table)

**Purpose**: Runtime configuration and state (kill switch, shadow mode status)
**Table**: `system_config`

**Schema** (PostgreSQL):
```sql
CREATE TABLE system_config (
    -- Singleton pattern (only one row)
    id INTEGER PRIMARY KEY DEFAULT 1,

    -- Kill switch
    automation_enabled BOOLEAN NOT NULL DEFAULT true,
    disabled_at TIMESTAMP,
    disabled_by VARCHAR(100),
    disable_reason TEXT,

    -- Shadow mode status (derived from config file)
    shadow_mode_active BOOLEAN NOT NULL DEFAULT false,
    shadow_mode_until TIMESTAMP,

    -- Error rate tracking
    error_rate_last_hour DECIMAL(5,4) DEFAULT 0.0000,  -- e.g., 0.0523 = 5.23%
    last_error_rate_check TIMESTAMP,

    -- Metadata
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Ensure only one row exists
    CONSTRAINT system_config_singleton CHECK (id = 1)
);

-- Initialize with default values
INSERT INTO system_config (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;
```

**Usage**:
- Worker checks `automation_enabled` before posting responses
- If `false` → all tickets are escalated with reason "Automation disabled (kill switch)"
- Dashboard reads this table to show kill switch status
- Dashboard updates `automation_enabled` when kill switch is toggled

---

### 5. Escalation (Derived View)

**Purpose**: Query interface for escalated tickets requiring human review
**Type**: Database view (not a physical table)

**Schema** (PostgreSQL View):
```sql
CREATE VIEW escalations AS
SELECT
    id,
    ticket_id,
    ticket_key,
    ticket_snapshot->>'fields'->>'summary' AS ticket_title,
    escalation_reason,
    confidence_scores,
    created_at,
    -- Calculate if ticket is "urgent" (not reviewed within 4h)
    CASE
        WHEN created_at < NOW() - INTERVAL '4 hours' THEN true
        ELSE false
    END AS is_overdue,
    -- Extract top confidence match for display
    (
        SELECT jsonb_object_keys(confidence_scores)
        ORDER BY (confidence_scores->jsonb_object_keys(confidence_scores)->>'confidence')::float DESC
        LIMIT 1
    ) AS top_match_response_id,
    (
        SELECT MAX((value->>'confidence')::float)
        FROM jsonb_each(confidence_scores)
    ) AS top_confidence_score
FROM audit_logs
WHERE action = 'escalate'
ORDER BY created_at DESC;
```

**Usage**:
- Dashboard queries this view to display escalated tickets
- Green Flag holder sees list with `is_overdue` flag for tickets >4h old
- Can filter by `escalation_reason` (e.g., "Low confidence", "Ambiguous match", "Sensitive data")

---

## State Transitions

### Ticket Processing State Machine

```
┌─────────────────┐
│  Webhook Event  │
│   (Jira)        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Check ProcessedTicket   │
│ (already handled?)      │
└────────┬────────────────┘
         │
         ├─ Yes → Escalate ("Follow-up")
         │
         ├─ No → Continue
         │
         ▼
┌─────────────────────────┐
│ Scan for Sensitive Data │
└────────┬────────────────┘
         │
         ├─ Found → Escalate ("Sensitive data")
         │
         ├─ Not Found → Continue
         │
         ▼
┌─────────────────────────┐
│  LLM Classification     │
└────────┬────────────────┘
         │
         ├─ Timeout → Escalate ("Classification timeout")
         │
         ├─ Success → Parse confidence scores
         │
         ▼
┌─────────────────────────┐
│ Evaluate Confidence     │
└────────┬────────────────┘
         │
         ├─ Max confidence < 80% → Escalate ("Low confidence")
         │
         ├─ Multiple within 10% → Escalate ("Ambiguous")
         │
         ├─ Clear match → Continue
         │
         ▼
┌─────────────────────────┐
│  Check System Config    │
└────────┬────────────────┘
         │
         ├─ automation_enabled=false → Escalate ("Kill switch")
         │
         ├─ shadow_mode_active=true → Log (no post)
         │
         ├─ Enabled → Continue
         │
         ▼
┌─────────────────────────┐
│ Post Response to Jira   │
│ + Write Audit Log       │
└─────────────────────────┘
```

### Retraction State Transition

```
┌─────────────────┐
│  Auto-Response  │
│   Posted        │
└────────┬────────┘
         │
         │ (within 5 min)
         ▼
┌─────────────────────────┐
│ Green Flag Holder       │
│ Clicks "Retract"        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Edit Jira Comment       │
│ (strikethrough text)    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Add New Jira Comment    │
│ ("Retracted...")        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Update AuditLog         │
│ (retracted_at, user)    │
└─────────────────────────┘
         │
         ▼ (ERROR - violates immutability)

         X (Not allowed by trigger)
```

**Correction**: Audit log is append-only. Instead of updating:
- Insert new audit log entry with `action='retraction'` referencing original `id`
- Keep original audit log intact (immutability)

**Revised Retraction Flow**:
```sql
-- Original audit log (untouched)
id: 123, action: 'auto_respond', comment_id: '456', ...

-- New audit log entry for retraction
INSERT INTO audit_logs (
    ticket_id,
    matched_response_id,
    action,
    escalation_reason,
    system_version,
    config_version
) VALUES (
    '12345678',
    NULL,
    'retraction',
    'Retracted by user@skyscanner.net',
    'v1.0.0',
    '1.0.0'
);
```

**Dashboard Query**:
```sql
-- Find retractions
SELECT a1.*, a2.created_at AS retracted_at
FROM audit_logs a1
LEFT JOIN audit_logs a2 ON a1.ticket_id = a2.ticket_id AND a2.action = 'retraction'
WHERE a1.action = 'auto_respond'
```

---

## Data Validation Rules

### Runtime Validation (Application Layer)

**Ticket Processing**:
1. Jira webhook payload must contain: `issue.id`, `issue.key`, `issue.fields`
2. Classification confidence scores must sum to ≤1.0 per response
3. Template variable substitution: `{{issueReporter}}` and `{{issueAssignee}}` must resolve to valid Jira users
4. Escalation notifications must include: ticket link, reason, top N confidence scores

**Configuration Validation**:
1. On service startup, validate `canned_responses.yaml` against schema
2. Ensure no duplicate `id` values
3. Verify `activated_at` is not in future (error if yes)
4. Check shadow mode: if `now() - activated_at < shadow_mode_hours` → enable shadow mode

**Audit Log Validation**:
1. Before inserting, verify all required fields are non-null
2. Ensure `confidence_scores` is valid JSON
3. Check state constraints (e.g., `action='auto_respond'` → `comment_id` must be set)

---

## Data Retention and Archival

### 90-Day Retention Policy

**Scheduled Job** (daily cron at 2 AM UTC):
```sql
-- Archive logs older than 90 days
WITH archived_logs AS (
    DELETE FROM audit_logs
    WHERE created_at < NOW() - INTERVAL '90 days'
    RETURNING *
)
-- Export to S3 (handled by application code)
SELECT * FROM archived_logs;
```

**Archival Process**:
1. Query logs older than 90 days
2. Export to S3 as gzipped JSONL: `s3://green-flag-audit-logs/archive/2026/01/audit-logs-2026-01-27.jsonl.gz`
3. Delete from PostgreSQL
4. Retain in S3 for additional 2 years (compliance), then transition to Glacier

**Same Process for `processed_tickets`**:
```sql
DELETE FROM processed_tickets
WHERE first_processed_at < NOW() - INTERVAL '90 days';
```

---

## Data Size Estimates

### Current State (Year 1)

| Entity | Rows | Size per Row | Total Size |
|--------|------|--------------|------------|
| `audit_logs` | ~5,000/year | ~5 KB (JSONB) | ~25 MB/year |
| `processed_tickets` | ~5,000/year | ~200 B | ~1 MB/year |
| `system_config` | 1 | ~500 B | ~500 B |
| `canned_responses` | 11-20 | Config file | ~10 KB |

**90-Day Retention**: ~12 KB rows in `audit_logs` (3 months of data = ~6 MB)

### Projected Scale (Year 3)

| Entity | Rows | Size per Row | Total Size |
|--------|------|--------------|------------|
| `audit_logs` | ~15,000/year | ~5 KB | ~75 MB/year |
| `processed_tickets` | ~15,000/year | ~200 B | ~3 MB/year |

**Conclusion**: PostgreSQL easily handles this scale. No sharding or optimization needed.

---

## Sensitive Data Handling

### Ticket Content Scanning

**Before Classification**:
```python
SENSITIVE_KEYWORDS = [
    "password", "token", "api key", "secret", "credential",
    "private key", "access key", "auth token", "bearer"
]

def contains_sensitive_data(ticket_text: str) -> bool:
    text_lower = ticket_text.lower()
    return any(keyword in text_lower for keyword in SENSITIVE_KEYWORDS)
```

**If Detected**:
- Immediate escalation with reason "Sensitive data detected: {keyword}"
- Do NOT send to LLM (avoid logging credentials in LLM provider logs)
- Audit log stores original ticket (acceptable - secure PostgreSQL)

---

## Rollback and Disaster Recovery

### Database Backups

- **RDS Automated Backups**: Daily snapshots, 7-day retention
- **Point-in-Time Recovery**: 5-minute granularity
- **Manual Snapshots**: Before major deployments

### Data Loss Scenarios

| Scenario | Impact | Recovery |
|----------|--------|----------|
| **PostgreSQL failure** | New tickets can't be logged | Jira webhook returns 5xx → Jira retries. Queue in Redis preserves tickets. |
| **Redis failure** | Tickets not queued | Webhook returns 5xx → Jira retries. No data loss. |
| **Both DB + Redis fail** | Tickets lost for duration of outage | Jira retries for 24h. After recovery, backlog processed. |
| **Audit log corruption** | Historical data compromised | Restore from RDS backup + S3 archive. |

### Immutability Protection

- Database triggers prevent updates/deletes on `audit_logs`
- Even with `SUPERUSER` access, trigger raises exception
- To modify (e.g., GDPR deletion), must: disable trigger → modify → re-enable trigger (requires explicit action)

---

## Performance Considerations

### Query Optimization

**Dashboard Queries** (must load <3s):
```sql
-- Recent tickets (paginated)
SELECT * FROM audit_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 50;
-- Uses: idx_audit_logs_created_at (fast)

-- Escalations
SELECT * FROM escalations
WHERE is_overdue = true;
-- Uses: view with filtered index

-- Weekly report
SELECT
    DATE_TRUNC('day', created_at) AS day,
    COUNT(*) FILTER (WHERE action = 'auto_respond') AS auto_count,
    COUNT(*) FILTER (WHERE action = 'escalate') AS escalate_count
FROM audit_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY day;
-- Uses: idx_audit_logs_created_at + idx_audit_logs_action
```

### JSONB Performance

- PostgreSQL JSONB is indexed by default (GIN index)
- Queries like `ticket_snapshot->>'fields'->>'summary'` are fast (<10ms)
- For better performance, can add expression index:
  ```sql
  CREATE INDEX idx_ticket_summary ON audit_logs ((ticket_snapshot->'fields'->>'summary'));
  ```

---

## Data Model Versioning

### Schema Migrations (Alembic)

**Migration 001: Initial Schema**
```python
# alembic/versions/001_initial_schema.py
def upgrade():
    op.create_table('audit_logs', ...)
    op.create_table('processed_tickets', ...)
    op.create_table('system_config', ...)
    op.execute('CREATE VIEW escalations AS ...')
    op.execute('CREATE TRIGGER audit_log_immutability ...')

def downgrade():
    op.drop_table('audit_logs')
    op.drop_table('processed_tickets')
    op.drop_table('system_config')
    op.execute('DROP VIEW escalations')
```

**Future Migrations**:
- Add new fields → `ALTER TABLE ... ADD COLUMN ...`
- Update view → `CREATE OR REPLACE VIEW ...`
- Never modify existing columns (backward compatibility)

### Config Versioning

**Breaking Changes** (e.g., schema change in `canned_responses.yaml`):
1. Bump `version` in config file
2. Application checks version on startup
3. If version mismatch → fail fast with clear error message
4. Requires code deployment + config update in lockstep

---

## Summary

This data model provides:
- ✅ Immutable audit trail (append-only `audit_logs`)
- ✅ Fail-safe tracking (`processed_tickets` prevents re-processing)
- ✅ Constitutional compliance (retention, sensitivity, reversibility)
- ✅ Dashboard query performance (<3s load time)
- ✅ Scalability (handles 15k tickets/year comfortably)
- ✅ Data privacy (90-day retention, secure storage)

Next: Generate API contracts ([contracts/](./contracts/)) and quickstart guide ([quickstart.md](./quickstart.md)).
