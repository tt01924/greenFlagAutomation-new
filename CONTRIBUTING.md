# Contributing to Green Flag Automation

Thank you for contributing to Green Flag Automation! This guide will help you set up your development environment and follow our contribution process.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Code Standards](#code-standards)
4. [Testing Guidelines](#testing-guidelines)
5. [Pull Request Process](#pull-request-process)
6. [Architecture Guidelines](#architecture-guidelines)
7. [Common Tasks](#common-tasks)

---

## Getting Started

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18+** (frontend)
- **Docker & Docker Compose** (local infrastructure)
- **Poetry** (Python dependency management)
- **Git** (version control)

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Skyscanner/green-flag-automation.git
   cd green-flag-automation
   ```

2. **Start infrastructure services**:
   ```bash
   docker-compose up -d
   ```

3. **Set up backend**:
   ```bash
   cd backend
   poetry install
   poetry shell
   alembic upgrade head
   ```

4. **Set up frontend**:
   ```bash
   cd frontend
   npm install
   ```

5. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (see Quickstart Guide for details)
   ```

6. **Verify setup**:
   ```bash
   # Terminal 1: Start API
   cd backend && uvicorn src.main:app --reload

   # Terminal 2: Start worker
   cd backend && python -m src.workers.ticket_processor_worker

   # Terminal 3: Start frontend
   cd frontend && npm run dev
   ```

---

## Development Workflow

### Branching Strategy

We follow **GitHub Flow** with feature branches:

```
main (protected)
  └── feature/ticket-123-add-new-classifier
  └── fix/ticket-456-fix-redis-connection
  └── docs/ticket-789-update-readme
```

### Branch Naming Convention

- **Features**: `feature/ticket-123-short-description`
- **Bug Fixes**: `fix/ticket-123-short-description`
- **Documentation**: `docs/ticket-123-short-description`
- **Refactoring**: `refactor/ticket-123-short-description`

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no functionality change)
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, tooling

**Examples**:

```
feat(classifier): Add support for multi-label classification

Implements LLM-based multi-label classifier for tickets that match
multiple canned responses. Returns top 3 matches with confidence scores.

Closes CASSINI-123
```

```
fix(webhook): Validate HMAC signature before processing

Previously, webhook endpoint did not verify HMAC signature from Jira,
allowing potential replay attacks. This fix adds signature validation.

Fixes CASSINI-456
```

```
docs(readme): Update architecture diagram with S3 audit archive

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Development Cycle

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/ticket-123-add-new-feature
   ```

2. **Make changes** and commit frequently:
   ```bash
   git add .
   git commit -m "feat(api): Add new endpoint for ticket retractions"
   ```

3. **Run tests** before pushing:
   ```bash
   # Backend tests
   cd backend && pytest

   # Frontend tests
   cd frontend && npm test

   # Linting
   cd backend && ruff check .
   cd frontend && npm run lint
   ```

4. **Push changes**:
   ```bash
   git push origin feature/ticket-123-add-new-feature
   ```

5. **Create Pull Request** (see [Pull Request Process](#pull-request-process))

---

## Code Standards

### Python (Backend)

#### Style Guide

- Follow **PEP 8** with **Black** formatter (line length: 100)
- Use **type hints** for all function signatures
- Use **async/await** for I/O-bound operations
- Prefer **f-strings** over `.format()` or `%` formatting

#### Code Quality Tools

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff (faster alternative to flake8, pylint, isort)
ruff check .

# Type checking with mypy
mypy src/

# Security audit with bandit
bandit -r src/
```

#### Example Code

```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.models.processed_ticket import ProcessedTicket

router = APIRouter(tags=["tickets"])


@router.get("/tickets/{ticket_id}", status_code=status.HTTP_200_OK)
async def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db)
) -> ProcessedTicket:
    """Retrieve a processed ticket by ID.

    Args:
        ticket_id: The Jira ticket ID (e.g., "CASSINI-123")
        db: Database session dependency

    Returns:
        ProcessedTicket: The processed ticket record

    Raises:
        HTTPException: If ticket is not found (404)
    """
    ticket = db.query(ProcessedTicket).filter(
        ProcessedTicket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    return ticket
```

### TypeScript (Frontend)

#### Style Guide

- Follow **ESLint** configuration (Airbnb style guide)
- Use **functional components** with **hooks** (no class components)
- Use **TypeScript strict mode** (no `any` types)
- Prefer **named exports** over default exports

#### Code Quality Tools

```bash
# Lint with ESLint
npm run lint

# Fix auto-fixable issues
npm run lint:fix

# Type checking
npm run type-check

# Format with Prettier
npm run format
```

#### Example Code

```typescript
import React, { useState, useEffect } from 'react'
import { getTickets } from '../api'
import { ProcessedTicket } from '../types'

interface TicketListProps {
  showEscalatedOnly?: boolean
}

export function TicketList({ showEscalatedOnly = false }: TicketListProps): JSX.Element {
  const [tickets, setTickets] = useState<ProcessedTicket[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTickets = async (): Promise<void> => {
      try {
        setLoading(true)
        const data = await getTickets({ escalatedOnly: showEscalatedOnly })
        setTickets(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch tickets')
      } finally {
        setLoading(false)
      }
    }

    void fetchTickets()
  }, [showEscalatedOnly])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <div className="ticket-list">
      {tickets.map((ticket) => (
        <TicketCard key={ticket.id} ticket={ticket} />
      ))}
    </div>
  )
}
```

### Documentation

#### Docstrings (Python)

Use **Google style** docstrings:

```python
def classify_ticket(ticket_description: str, canned_responses: List[str]) -> ClassificationResult:
    """Classify a ticket against canned responses using LLM.

    This function sends the ticket description to the LLM along with
    available canned responses and returns the best match with a
    confidence score.

    Args:
        ticket_description: The ticket description text
        canned_responses: List of pre-approved canned response texts

    Returns:
        ClassificationResult: Contains matched response ID, confidence
            score (0-1), and reasoning for the classification

    Raises:
        LLMTimeoutError: If LLM API call exceeds 30 second timeout
        LLMAPIError: If LLM API returns an error response

    Example:
        >>> result = classify_ticket(
        ...     "How do I reset my password?",
        ...     ["Follow password reset link...", "Contact support..."]
        ... )
        >>> print(result.confidence_score)
        0.95
    """
    pass
```

#### JSDoc (TypeScript)

```typescript
/**
 * Retract an auto-responded ticket within the 5-minute retraction window.
 *
 * @param ticketId - The Jira ticket ID (e.g., "CASSINI-123")
 * @param reason - Reason for retraction (required for audit log)
 * @returns Promise resolving to the retracted ticket record
 * @throws {Error} If ticket is outside retraction window or already retracted
 *
 * @example
 * ```typescript
 * const ticket = await retractTicket("CASSINI-123", "Incorrect classification")
 * console.log(ticket.status) // "retracted"
 * ```
 */
export async function retractTicket(
  ticketId: string,
  reason: string
): Promise<ProcessedTicket> {
  // Implementation
}
```

---

## Testing Guidelines

### Test Coverage Requirements

- **Backend**: Minimum 80% code coverage
- **Frontend**: Minimum 70% code coverage
- **Critical paths**: 100% coverage (classification, webhook handling, escalation)

### Backend Testing (pytest)

#### Test Structure

```
backend/tests/
├── unit/
│   ├── test_classifier.py
│   ├── test_jira_client.py
│   └── test_slack_client.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_ticket_processor.py
├── e2e/
│   └── test_ticket_flow.py
└── fixtures/
    ├── jira_webhook_iam_request.json
    └── mock_responses.py
```

#### Writing Tests

```python
import pytest
from unittest.mock import MagicMock, patch

from src.services.classifier import TicketClassifier


@pytest.fixture
def classifier():
    """Fixture providing a TicketClassifier instance."""
    return TicketClassifier()


@pytest.mark.unit
def test_classify_high_confidence(classifier):
    """Test classification returns high confidence for exact match."""
    # Arrange
    ticket_description = "How do I reset my password?"
    canned_responses = [
        {"id": "CR-001", "text": "Follow the password reset link..."},
        {"id": "CR-002", "text": "Contact IT support..."}
    ]

    # Act
    result = classifier.classify(ticket_description, canned_responses)

    # Assert
    assert result.confidence_score > 0.8
    assert result.matched_response_id == "CR-001"


@pytest.mark.integration
@patch('src.services.classifier.anthropic_client')
async def test_classify_with_llm_timeout(mock_anthropic, classifier):
    """Test classification handles LLM timeout gracefully."""
    # Arrange
    mock_anthropic.messages.create.side_effect = TimeoutError()

    # Act & Assert
    with pytest.raises(LLMTimeoutError):
        await classifier.classify_async("Test ticket", [])
```

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_classifier.py

# Run with coverage report
pytest --cov=src --cov-report=html

# Run only unit tests
pytest -m unit

# Run with verbose output
pytest -v
```

### Frontend Testing (Vitest + React Testing Library)

#### Test Structure

```
frontend/src/
├── components/
│   ├── TicketList.tsx
│   └── TicketList.test.tsx
├── pages/
│   ├── Dashboard.tsx
│   └── Dashboard.test.tsx
└── utils/
    ├── api.ts
    └── api.test.ts
```

#### Writing Tests

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { TicketList } from './TicketList'
import * as api from '../api'

vi.mock('../api')

describe('TicketList', () => {
  it('renders tickets after loading', async () => {
    // Arrange
    const mockTickets = [
      { id: '1', ticket_id: 'CASSINI-123', status: 'auto_responded' },
      { id: '2', ticket_id: 'CASSINI-456', status: 'escalated' }
    ]
    vi.mocked(api.getTickets).mockResolvedValue(mockTickets)

    // Act
    render(<TicketList />)

    // Assert
    await waitFor(() => {
      expect(screen.getByText('CASSINI-123')).toBeInTheDocument()
      expect(screen.getByText('CASSINI-456')).toBeInTheDocument()
    })
  })

  it('displays error message on API failure', async () => {
    // Arrange
    vi.mocked(api.getTickets).mockRejectedValue(new Error('API Error'))

    // Act
    render(<TicketList />)

    // Assert
    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument()
    })
  })
})
```

#### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch

# Run specific test file
npm test TicketList.test.tsx
```

---

## Pull Request Process

### Before Submitting

1. **Ensure all tests pass**:
   ```bash
   cd backend && pytest
   cd frontend && npm test
   ```

2. **Run linters and formatters**:
   ```bash
   cd backend && ruff check . && black src/ tests/
   cd frontend && npm run lint:fix && npm run format
   ```

3. **Update documentation** if needed (README, API docs, comments)

4. **Add tests** for new features or bug fixes

5. **Verify constitutional compliance** (see `.specify/memory/constitution.md`)

### Creating the Pull Request

1. **Push your branch** to origin:
   ```bash
   git push origin feature/ticket-123-add-new-feature
   ```

2. **Create PR** on GitHub with:
   - **Title**: Clear, concise summary (same as commit message format)
   - **Description**: Use the PR template (auto-populated):

   ```markdown
   ## Summary
   Brief description of changes

   ## Changes Made
   - Added new classifier for multi-label classification
   - Updated webhook handler to support new Jira event types
   - Added integration tests for new functionality

   ## Testing
   - [ ] Unit tests added/updated
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   - [ ] No regressions observed

   ## Screenshots (if UI changes)
   [Add screenshots here]

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Tests pass locally
   - [ ] Documentation updated
   - [ ] No new warnings or errors
   - [ ] Constitutional requirements validated

   ## Related Issues
   Closes CASSINI-123
   ```

3. **Request review** from at least 2 team members

4. **Add labels**: `feature`, `bug`, `documentation`, etc.

### Review Process

#### As an Author

- **Respond to feedback** promptly and professionally
- **Push fixes** to the same branch (PR updates automatically)
- **Request re-review** after addressing comments
- **Resolve conversations** once feedback is addressed

#### As a Reviewer

- **Review within 24 hours** of request
- **Check for**:
  - Code correctness and logic errors
  - Test coverage and quality
  - Performance implications
  - Security vulnerabilities
  - Adherence to style guide
  - Constitutional compliance
- **Use GitHub suggestions** for minor fixes
- **Approve** when satisfied, or **Request changes** with clear feedback

### Merging

- **Squash and merge** is preferred (keeps main history clean)
- **Delete branch** after merge
- **Verify CI/CD pipeline** completes successfully

---

## Architecture Guidelines

### When to Add New Dependencies

Only add dependencies if:
- They solve a real problem (not speculative)
- They are actively maintained (recent commits, active issues)
- They have good documentation
- They don't duplicate existing functionality

**Examples**:
- ✅ **Add** `httpx` for async HTTP requests (better than `requests` for async)
- ❌ **Don't add** `moment.js` (use native `Date` or `date-fns`)
- ❌ **Don't add** utility libraries for one-off functions (write custom code)

### Database Migrations

Always use **Alembic** for schema changes:

```bash
# Create new migration
alembic revision -m "Add confidence_threshold column to system_config"

# Edit migration file to add upgrade/downgrade logic

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

**Migration guidelines**:
- Never delete columns (add deprecation warnings instead)
- Always provide `downgrade()` function
- Test migrations on local database before committing

### API Design

Follow **RESTful** conventions:

- `GET /api/tickets` - List tickets
- `GET /api/tickets/{id}` - Get single ticket
- `POST /api/tickets` - Create ticket (usually webhook)
- `PATCH /api/tickets/{id}` - Update ticket
- `DELETE /api/tickets/{id}` - Delete ticket (soft delete preferred)

Use **HTTP status codes** correctly:
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing auth
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Constitutional Compliance

Before merging, verify your changes comply with the [constitution](./.specify/memory/constitution.md):

- **FR-001**: Only send pre-approved canned responses (no AI-generated text)
- **FR-002**: Escalate when confidence <80%
- **FR-003**: Detect sensitive data and escalate
- **FR-007**: Never drop tickets (fail-safe escalation)
- **FR-014**: Maintain immutable audit logs
- **FR-019**: Support 48-hour shadow mode
- **FR-020**: Support kill switch

---

## Common Tasks

### Adding a New Canned Response

1. Edit `backend/src/config/canned_responses.yaml`:
   ```yaml
   canned_responses:
     - id: "CR-012"
       trigger: "VPN connection issues"
       response: "For VPN issues, please try..."
       category: "network"
       keywords: ["vpn", "virtual private network", "network access"]
   ```

2. Increment `CONFIG_VERSION` in `backend/src/config/settings.py`:
   ```python
   CONFIG_VERSION: str = "1.1.0"  # Increment when canned responses change
   ```

3. Test classification with new response:
   ```bash
   cd backend
   python -m tests.integration.test_classifier
   ```

4. Deploy and activate shadow mode (48 hours):
   ```bash
   curl -X POST https://api.example.com/api/admin/shadow-mode/activate
   ```

### Updating Dependencies

**Backend (Poetry)**:
```bash
cd backend
poetry update  # Update all dependencies
poetry update fastapi  # Update specific package
poetry lock  # Regenerate lock file
```

**Frontend (npm)**:
```bash
cd frontend
npm update  # Update all dependencies
npm update react  # Update specific package
npm audit fix  # Fix security vulnerabilities
```

### Debugging

**Backend debugging**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn src.main:app --reload

# Use pdb for breakpoints
import pdb; pdb.set_trace()

# Check database queries
export SQLALCHEMY_ECHO=1
```

**Frontend debugging**:
```bash
# Use React DevTools browser extension
# Add console.log or debugger statements
console.log('Tickets:', tickets)
debugger  // Pauses execution in browser DevTools
```

### Creating a New API Endpoint

1. **Add route** in `backend/src/api/`:
   ```python
   # backend/src/api/tickets.py
   @router.get("/tickets/summary", status_code=status.HTTP_200_OK)
   async def get_ticket_summary(
       db: Session = Depends(get_db)
   ) -> Dict[str, Any]:
       """Get summary statistics for all tickets."""
       total = db.query(ProcessedTicket).count()
       auto_responded = db.query(ProcessedTicket).filter(
           ProcessedTicket.action == "auto_respond"
       ).count()

       return {
           "total": total,
           "auto_responded": auto_responded,
           "automation_rate": auto_responded / total if total > 0 else 0
       }
   ```

2. **Add tests** in `backend/tests/integration/test_api_endpoints.py`

3. **Update OpenAPI docs** (auto-generated at `/docs`)

4. **Add frontend API call** in `frontend/src/api.ts`:
   ```typescript
   export async function getTicketSummary(): Promise<TicketSummary> {
     const response = await fetch(`${API_BASE_URL}/tickets/summary`)
     if (!response.ok) throw new Error('Failed to fetch summary')
     return response.json()
   }
   ```

---

## Getting Help

- **Slack**: #cassini-squad (general questions)
- **GitHub Issues**: For bugs and feature requests
- **Code Reviews**: Ask in PR comments
- **Documentation**: See [README.md](./README.md) and [docs/](./docs/)

Thank you for contributing to Green Flag Automation!
