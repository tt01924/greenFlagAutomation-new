# Tasks: Green Flag Ticket Automation

**Input**: Design documents from `/specs/001-green-flag-automation/`
**Prerequisites**: plan.md (✓), spec.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

**Tests**: Tests are OPTIONAL in this project - only included for critical paths where specified in the constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Per plan.md, this is a **monorepo with backend + frontend**:
- Backend: `backend/src/`, `backend/tests/`
- Frontend: `frontend/src/`, `frontend/tests/`
- Infrastructure: `infra/`
- Root-level: Configuration files

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create root-level project structure (backend/, frontend/, infra/, docs/)
- [x] T002 Initialize Python backend with Poetry in backend/ (pyproject.toml dependencies per plan.md)
- [x] T003 [P] Initialize React frontend with Vite in frontend/ (package.json dependencies per plan.md)
- [x] T004 [P] Create backend/docker/Dockerfile for backend service
- [x] T005 [P] Create root docker-compose.yml with PostgreSQL, Redis, MailHog services
- [x] T006 [P] Create .env.example with all required environment variables from quickstart.md
- [x] T007 [P] Setup Python linting (black, mypy, pylint) configuration in backend/pyproject.toml
- [x] T008 [P] Setup ESLint and Prettier for frontend in frontend/.eslintrc.js
- [x] T009 [P] Create backend/.gitignore and frontend/.gitignore
- [x] T010 [P] Create root README.md with project overview and quickstart link

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database & Storage Foundation

- [x] T011 Setup Alembic migrations framework in backend/migrations/
- [x] T012 Create initial migration 001_initial_schema.py with audit_logs, processed_tickets, system_config tables per data-model.md
- [x] T013 [P] Implement append-only trigger for audit_logs table in migration
- [x] T014 [P] Create SQLAlchemy base model in backend/src/models/base.py
- [x] T015 [P] Create AuditLog model in backend/src/models/audit_log.py (maps to data-model.md schema)
- [x] T016 [P] Create ProcessedTicket model in backend/src/models/processed_ticket.py
- [x] T017 [P] Create SystemConfig model in backend/src/models/system_config.py

### Configuration & Settings Foundation

- [x] T018 Create Pydantic settings in backend/src/config/settings.py (loads from .env per quickstart.md)
- [x] T019 [P] Create canned_responses.yaml in backend/src/config/ with 11 initial responses from spec.md
- [x] T020 [P] Implement CannedResponse dataclass in backend/src/models/canned_response.py with YAML loading
- [x] T021 [P] Create LLM prompt templates in backend/src/config/prompts.py

### External Client Foundation

- [x] T022 [P] Implement JiraClient wrapper in backend/src/services/jira_client.py (atlassian-python-api)
- [x] T023 [P] Implement SlackClient wrapper in backend/src/services/slack_client.py (slack-bolt SDK)
- [x] T024 [P] Implement LLM classifier in backend/src/services/classifier.py (Anthropic SDK with GPT-4 fallback)

### API & Worker Foundation

- [x] T025 Create FastAPI app in backend/src/main.py with CORS, middleware, routers
- [x] T026 [P] Setup Redis queue in backend/src/services/queue.py (RQ/Celery wrapper)
- [x] T027 [P] Implement audit logger service in backend/src/services/audit_logger.py (append-only writes)
- [x] T028 [P] Create health check endpoints in backend/src/api/health.py per contracts/openapi.yaml
- [x] T029 [P] Setup error handling middleware in backend/src/middleware/error_handler.py
- [x] T030 [P] Setup logging configuration in backend/src/config/logging.py

### Testing Foundation

- [x] T031 [P] Create pytest configuration in backend/pytest.ini
- [x] T032 [P] Create test fixtures in backend/tests/fixtures/ (mock Jira, Slack, LLM responses)
- [x] T033 [P] Create database test helpers in backend/tests/helpers/db.py (test DB setup/teardown)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automated Response for Clear Match (Priority: P1) 🎯 MVP

**Goal**: Enable automatic posting of canned responses to Jira when ticket classification confidence exceeds 80%

**Independent Test**: Create Jira ticket with "Need IAM permissions" → System posts "Cassini - IAM request" canned response within 5 minutes → Ticket has "auto-responded" label

### Implementation for User Story 1

- [x] T034 [P] [US1] Implement Jira webhook endpoint in backend/src/api/webhooks.py per contracts/jira-webhook.json
- [x] T035 [P] [US1] Implement webhook signature verification in backend/src/middleware/webhook_auth.py
- [x] T036 [US1] Implement ticket processor orchestration in backend/src/services/processor.py (FR-001 to FR-007)
- [x] T037 [US1] Implement sensitive data scanner in backend/src/services/sensitive_data_scanner.py (FR-010 keyword detection)
- [x] T038 [US1] Implement confidence evaluation logic in backend/src/services/confidence_evaluator.py (80% threshold, 10% ambiguity)
- [x] T039 [US1] Implement template variable substitution in backend/src/services/template_renderer.py ({{issueReporter}}, {{issueAssignee}})
- [x] T040 [US1] Implement response posting to Jira in backend/src/services/response_poster.py (FR-004 to FR-007)
- [x] T041 [US1] Create ticket processor worker in backend/src/workers/ticket_processor_worker.py (Redis queue consumer)
- [x] T042 [US1] Add follow-up detection logic in backend/src/services/processor.py (FR-012 - check processed_tickets table)
- [x] T043 [US1] Implement shadow mode state management in backend/src/services/shadow_mode.py (48h check per data-model.md)

### Integration Tests for User Story 1

- [x] T044 [US1] Create E2E test script in backend/tests/e2e/test_auto_response_flow.py (simulates full workflow from webhook to Jira posting)

**Checkpoint**: At this point, User Story 1 should be fully functional - tickets with clear matches get automated responses posted to Jira

---

## Phase 4: User Story 2 - Human Escalation for Unclear Requests (Priority: P1)

**Goal**: Escalate tickets to Green Flag holder via Slack when confidence is low, match is ambiguous, or sensitive data is detected

**Independent Test**: Create Jira ticket with ambiguous content "Something is broken" → No Jira response posted → Green Flag holder receives Slack notification with ticket link and reasoning within 5 minutes

### Implementation for User Story 2

- [x] T045 [P] [US2] Implement escalation service in backend/src/services/escalation_service.py (FR-008, FR-009, FR-011, FR-023)
- [x] T046 [P] [US2] Create Slack message builder in backend/src/services/slack_message_builder.py per contracts/slack-message.json (all escalation variants)
- [x] T047 [US2] Integrate escalation logic into processor.py (escalate on low confidence, ambiguous, sensitive data, errors)
- [x] T048 [US2] Implement kill switch check in backend/src/services/processor.py (FR-020, read from system_config.automation_enabled)
- [x] T049 [US2] Add error handling with escalation in backend/src/services/processor.py (FR-022 - fail safe)
- [x] T050 [US2] Implement escalation retry queue in backend/src/services/escalation_service.py (Slack unavailable → queue for retry)

### Integration Tests for User Story 2

- [x] T051 [US2] Create E2E test script in backend/tests/e2e/test_escalation_flow.py (simulates escalation scenarios)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - clear matches auto-respond, unclear matches escalate to human

---

## Phase 5: User Story 3 - Green Flag Holder Oversight Dashboard (Priority: P2)

**Goal**: Provide web dashboard for Green Flag holder to view processed tickets, retract responses, view escalations, and access weekly reports

**Independent Test**: Run system for 1 day with mixed tickets → Open dashboard at http://localhost:3000 → See all tickets listed with actions, confidence scores, timestamps → Click retract button on recent response (<5 min) → Verify Jira comment updated with strikethrough

### Backend API for User Story 3

- [ ] T052 [P] [US3] Implement dashboard API endpoints in backend/src/api/dashboard.py per contracts/openapi.yaml (GET /tickets, GET /tickets/:id)
- [ ] T053 [P] [US3] Implement escalations endpoint in backend/src/api/dashboard.py (GET /escalations with overdue filter)
- [ ] T054 [P] [US3] Implement retraction endpoint in backend/src/api/dashboard.py (POST /tickets/:id/retract with 5-min window check per FR-016)
- [ ] T055 [P] [US3] Implement weekly report endpoint in backend/src/api/dashboard.py (GET /reports/weekly with aggregations per data-model.md)
- [ ] T056 [US3] Implement retraction service in backend/src/services/retraction_service.py (edit Jira comment, add new comment, create audit log entry)

### Frontend Dashboard for User Story 3

- [ ] T057 [P] [US3] Create API client in frontend/src/services/api.ts (Axios wrapper for backend API)
- [ ] T058 [P] [US3] Create TicketList component in frontend/src/components/TicketList.tsx (displays processed tickets with filters)
- [ ] T059 [P] [US3] Create TicketDetail component in frontend/src/components/TicketDetail.tsx (full ticket view with retract button)
- [ ] T060 [P] [US3] Create EscalationList component in frontend/src/components/EscalationList.tsx (shows escalated tickets with overdue flag)
- [ ] T061 [P] [US3] Create WeeklyReport component in frontend/src/components/WeeklyReport.tsx (charts with Recharts)
- [ ] T062 [P] [US3] Create Dashboard page in frontend/src/pages/Dashboard.tsx (main view with ticket list)
- [ ] T063 [P] [US3] Create Reports page in frontend/src/pages/Reports.tsx (weekly report page)
- [ ] T064 [US3] Create App router in frontend/src/App.tsx (React Router with dashboard routes)
- [ ] T065 [US3] Add retract button logic in TicketDetail.tsx (POST to /retract, handle 5-min window validation)

### Scheduled Jobs for User Story 3

- [ ] T066 [P] [US3] Implement daily summary job in backend/src/workers/daily_summary_job.py (FR-017 - generates email at 9 AM UTC)
- [ ] T067 [P] [US3] Implement audit cleanup job in backend/src/workers/audit_cleanup_job.py (FR-014 - archives logs >90 days to S3)

**Checkpoint**: Dashboard is fully functional - Green Flag holder can view all tickets, retract responses, see escalations, and view weekly reports

---

## Phase 6: User Story 4 - Canned Response Management (Priority: P3)

**Goal**: Enable Cassini team to add/update canned responses via PR, with 48-hour shadow mode before activation

**Independent Test**: Add new canned response to config YAML → Merge PR → System enters shadow mode for 48 hours (logs decisions without posting) → After 48h, new response becomes active for auto-responses

### Backend API for User Story 4

- [ ] T068 [P] [US4] Implement shadow mode status endpoint in backend/src/api/admin.py (GET /admin/shadow-mode per contracts/openapi.yaml)
- [ ] T069 [US4] Add config version tracking to processor.py (log config_version in audit_logs per data-model.md)
- [ ] T070 [US4] Implement shadow mode enforcement in processor.py (if shadow_mode_active, log action='shadow' but don't post to Jira)
- [ ] T071 [US4] Add automatic shadow mode expiration check in backend/src/services/shadow_mode.py (after 48h, set shadow_mode_active=false)

### Frontend for User Story 4

- [ ] T072 [P] [US4] Create ShadowModeStatus component in frontend/src/components/ShadowModeStatus.tsx (banner showing time remaining)
- [ ] T073 [US4] Add shadow mode indicator to Dashboard page (displays banner if active)

### Infrastructure for User Story 4

- [ ] T074 [US4] Create ConfigMap template in infra/k8s/configmap.yaml (for canned_responses.yaml deployment)
- [ ] T075 [US4] Document canned response update workflow in docs/canned-response-management.md (PR process, shadow mode, activation)

**Checkpoint**: Canned response management is complete - new responses can be added via PR with 48h safety window

---

## Phase 7: Kill Switch & Error Rate Monitoring

**Goal**: Implement kill switch and automated error rate monitoring per constitutional requirements

**Independent Test**: Activate kill switch via dashboard → Send test ticket → Verify ticket is escalated with "Automation disabled" reason → All subsequent tickets escalate until re-enabled

### Backend Implementation

- [ ] T076 [P] Implement kill switch endpoints in backend/src/api/admin.py (GET/POST /admin/kill-switch per contracts/openapi.yaml)
- [ ] T077 [P] Create KillSwitch component in frontend/src/components/KillSwitch.tsx (toggle button with reason input)
- [ ] T078 Add kill switch page in frontend/src/pages/Settings.tsx (includes kill switch component)
- [ ] T079 [P] Implement Prometheus metrics in backend/src/services/metrics.py (tickets_processed_total, tickets_failed_total, automation_enabled gauge)
- [ ] T080 [P] Create Prometheus alerting rules in infra/prometheus/alerts.yaml (5% error rate threshold)
- [ ] T081 [P] Implement circuit breaker endpoint in backend/src/api/admin.py (POST /circuit-breaker/disable called by Alertmanager)
- [ ] T082 Add error rate monitoring to processor.py (increment failure counter on exceptions)

**Checkpoint**: Kill switch and error monitoring fully operational - automation can be disabled manually or automatically

---

## Phase 8: Deployment & Infrastructure

**Purpose**: Deploy-ready infrastructure configuration

- [ ] T083 [P] Create Kubernetes deployment manifest in infra/k8s/deployment.yaml (backend pods with health checks)
- [ ] T084 [P] Create Kubernetes service manifest in infra/k8s/service.yaml (LoadBalancer for API)
- [ ] T085 [P] Create Kubernetes secrets template in infra/k8s/secrets.yaml (Jira, Slack, LLM API keys)
- [ ] T086 [P] Create Kubernetes CronJob manifests in infra/k8s/cronjob.yaml (daily summary and audit cleanup)
- [ ] T087 [P] Create Terraform configuration in infra/terraform/main.tf (RDS PostgreSQL, ElastiCache Redis, S3 audit archive bucket)
- [ ] T088 [P] Create Terraform variables in infra/terraform/variables.tf
- [ ] T089 [P] Setup Grafana dashboard JSON in infra/grafana/dashboard.json (ticket metrics, error rates, latencies)
- [ ] T090 [P] Create deployment documentation in docs/deployment.md (kubectl commands, terraform apply steps)

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and documentation

- [ ] T091 [P] Create root README.md with project overview, architecture diagram, and links to quickstart
- [ ] T092 [P] Create CONTRIBUTING.md with development workflow, testing guidelines, PR process
- [ ] T093 [P] Add inline documentation (docstrings) for all public functions in backend/src/
- [ ] T094 [P] Generate OpenAPI docs from FastAPI app (auto-generated at /docs endpoint)
- [ ] T095 [P] Run security audit with bandit in backend/ (check for common vulnerabilities)
- [ ] T096 [P] Run frontend accessibility audit with axe-core
- [ ] T097 Run full E2E validation following quickstart.md (verify all steps work)
- [ ] T098 Create operational runbook in docs/runbook.md (common issues, debugging, alerting)
- [ ] T099 Performance testing with locust (simulate 100 tickets/day load)
- [ ] T100 [P] Code cleanup and linting pass (black, mypy, pylint, eslint)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T010) completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T011-T033) - Core MVP feature
- **User Story 2 (Phase 4)**: Depends on Foundational (T011-T033) - Can run in parallel with US1 if staffed
- **User Story 3 (Phase 5)**: Depends on US1 and US2 completion (needs audit logs populated)
- **User Story 4 (Phase 6)**: Depends on Foundational only (independent of other stories)
- **Kill Switch (Phase 7)**: Depends on US1 and US2 (needs processor logic in place)
- **Deployment (Phase 8)**: Depends on all user stories you want to deploy
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories (can run parallel with US1)
- **User Story 3 (P2)**: Should start after US1 and US2 complete (needs audit data to display)
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Independent of other stories

### Within Each User Story

Tasks within a story follow this general pattern:
1. Backend models/services (parallelizable if different files)
2. Core business logic (sequential - depends on models)
3. API endpoints (depends on services)
4. Frontend components (parallelizable if different files)
5. Integration (depends on backend + frontend)

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003, T004, T005, T006, T007, T008, T009, T010 can all run in parallel

**Phase 2 (Foundational)**:
- Database models (T015-T017) can run in parallel
- External clients (T022-T024) can run in parallel
- Testing foundation (T031-T033) can run in parallel

**Phase 3 (US1)**:
- T034, T035, T037 can run in parallel (different files, no dependencies)

**Phase 5 (US3)**:
- Backend API endpoints (T052-T055) can run in parallel
- Frontend components (T057-T063) can all run in parallel
- Scheduled jobs (T066-T067) can run in parallel

**Phase 6 (US4)**:
- T068, T072, T074 can run in parallel

**Phase 7 (Kill Switch)**:
- T076, T077, T079, T080, T081 can run in parallel

**Phase 8 (Deployment)**:
- All infrastructure tasks (T083-T090) can run in parallel

**Phase 9 (Polish)**:
- Most tasks (T091-T096, T098, T100) can run in parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch User Story 1 tasks in parallel:

# First wave (independent files):
Task T034: "Implement Jira webhook endpoint in backend/src/api/webhooks.py"
Task T035: "Implement webhook signature verification in backend/src/middleware/webhook_auth.py"
Task T037: "Implement sensitive data scanner in backend/src/services/sensitive_data_scanner.py"

# Second wave (depends on first wave):
Task T036: "Implement ticket processor orchestration in backend/src/services/processor.py"
Task T038: "Implement confidence evaluation in backend/src/services/confidence_evaluator.py"

# Third wave:
Task T039: "Implement template rendering in backend/src/services/template_renderer.py"
Task T040: "Implement response posting in backend/src/services/response_poster.py"
Task T041: "Create worker in backend/src/workers/ticket_processor_worker.py"
```

---

## Parallel Example: User Story 3 (Dashboard)

```bash
# Backend API endpoints (all parallel):
Task T052: "Implement dashboard tickets endpoint"
Task T053: "Implement escalations endpoint"
Task T054: "Implement retraction endpoint"
Task T055: "Implement weekly report endpoint"

# Frontend components (all parallel):
Task T057: "Create API client"
Task T058: "Create TicketList component"
Task T059: "Create TicketDetail component"
Task T060: "Create EscalationList component"
Task T061: "Create WeeklyReport component"
Task T062: "Create Dashboard page"
Task T063: "Create Reports page"

# Then integrate with router (depends on pages):
Task T064: "Create App router"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

**Rationale**: Delivers core value (automated responses + escalation) with minimal surface area

1. Complete Phase 1: Setup (T001-T010)
2. Complete Phase 2: Foundational (T011-T033) - CRITICAL BLOCKER
3. Complete Phase 3: User Story 1 (T034-T044) - Auto-response capability
4. Complete Phase 4: User Story 2 (T045-T051) - Escalation capability
5. **STOP and VALIDATE**: Test US1 and US2 independently with real Jira tickets
6. Deploy MVP to staging

**MVP delivers**:
- ✅ 60% automation rate (SC-001)
- ✅ <5 min response time (SC-002)
- ✅ Fail-safe escalation (SC-008)
- ✅ Constitutional compliance (audit logs, safety mechanisms)

### Incremental Delivery (Add Dashboard)

After MVP is validated:

1. Complete Phase 5: User Story 3 (T052-T067) - Dashboard for oversight
2. Test dashboard independently with existing audit data
3. Deploy dashboard to production
4. **Now delivers**: Full operational visibility + retraction capability

### Optional Features (Lower Priority)

Only if needed:

1. Phase 6: User Story 4 (T068-T075) - Canned response management (can be manual initially)
2. Phase 7: Kill Switch (T076-T082) - Additional safety (can be environment variable initially)

### Parallel Team Strategy

With 2-3 developers:

1. **Week 1**: Everyone on Setup + Foundational (T001-T033)
2. **Week 2-3**:
   - Developer A: User Story 1 (T034-T044)
   - Developer B: User Story 2 (T045-T051)
3. **Week 4**: Integration testing + MVP validation
4. **Week 5-6**:
   - Developer A: Backend API for US3 (T052-T056, T066-T067)
   - Developer B: Frontend for US3 (T057-T065)
   - Developer C: Kill switch (T076-T082)
5. **Week 7**: Deployment (T083-T090)
6. **Week 8**: Polish (T091-T100)

---

## Validation Checkpoints

### After Phase 2 (Foundational):
- [ ] Database migrations run successfully
- [ ] All SQLAlchemy models can be imported
- [ ] Jira/Slack/LLM clients can authenticate
- [ ] Health check endpoint returns 200
- [ ] Redis queue accepts jobs

### After Phase 3 (US1):
- [ ] Webhook endpoint accepts Jira payloads
- [ ] Classification returns confidence scores
- [ ] High-confidence tickets get Jira responses
- [ ] Audit log entries created for all actions
- [ ] Template variables substituted correctly

### After Phase 4 (US2):
- [ ] Low-confidence tickets escalate to Slack
- [ ] Ambiguous matches escalate with reasoning
- [ ] Sensitive data keywords trigger escalation
- [ ] Kill switch blocks auto-responses

### After Phase 5 (US3):
- [ ] Dashboard loads within 3 seconds
- [ ] Ticket list displays all processed tickets
- [ ] Retract button works within 5-min window
- [ ] Weekly report shows accurate metrics
- [ ] Escalation list filters overdue tickets

### MVP Acceptance:
- [ ] Can process 10 test tickets end-to-end
- [ ] Auto-response rate >60%
- [ ] False positive rate <2% (measured via manual review)
- [ ] No tickets lost during testing
- [ ] All constitutional requirements validated

---

## Notes

- **[P] tasks** = different files, no dependencies, safe to parallelize
- **[Story] label** maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- **Constitution compliance**: Tasks T012-T013 (append-only audit logs), T037 (sensitive data), T048 (kill switch), T054 (retraction), T066-T067 (retention/summaries) directly implement constitutional requirements

---

## Task Count Summary

- **Phase 1 (Setup)**: 10 tasks
- **Phase 2 (Foundational)**: 23 tasks (BLOCKS all user stories)
- **Phase 3 (User Story 1 - P1)**: 11 tasks (MVP core)
- **Phase 4 (User Story 2 - P1)**: 7 tasks (MVP escalation)
- **Phase 5 (User Story 3 - P2)**: 16 tasks (Dashboard)
- **Phase 6 (User Story 4 - P3)**: 8 tasks (Config management)
- **Phase 7 (Kill Switch)**: 7 tasks
- **Phase 8 (Deployment)**: 8 tasks
- **Phase 9 (Polish)**: 10 tasks

**Total**: 100 tasks

**MVP Scope** (Phases 1-4): 51 tasks
**Full Feature** (All phases): 100 tasks

**Parallel Opportunities**: 58 tasks marked [P] can run in parallel (58% of total)

**Independent Stories**: US1, US2, and US4 are fully independent. US3 depends on US1+US2 for audit data to display.
