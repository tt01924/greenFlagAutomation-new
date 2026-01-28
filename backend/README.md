# Green Flag Automation - Backend

This is the backend API service for Green Flag Automation.

## Documentation

See the [main README](../README.md) for:
- Project overview and architecture
- Full setup instructions
- Deployment guides

## Quick Start

```bash
# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start API server
poetry run uvicorn src.main:app --reload --port 8000

# Start worker (in separate terminal)
poetry run python -m src.workers.ticket_processor_worker
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## Development

### Environment Setup

1. **Start infrastructure services**:
   ```bash
   cd .. && docker-compose up -d
   ```

2. **Configure environment**:
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your API keys
   ```

3. **Activate virtual environment**:
   ```bash
   # Option 1: Use poetry run for each command
   poetry run <command>

   # Option 2: Activate venv manually
   source $(poetry env info --path)/bin/activate
   ```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_classifier.py
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint code
poetry run ruff check src/

# Type checking
poetry run mypy src/

# Security audit
poetry run bandit -r src/
```

## Project Structure

```
backend/
├── src/
│   ├── api/              # FastAPI route handlers
│   ├── config/           # Configuration and settings
│   ├── middleware/       # Request/response middleware
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic services
│   └── workers/          # Background job workers
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # End-to-end tests
├── migrations/          # Alembic database migrations
└── docker/              # Docker configuration
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection
poetry run python -c "from src.models.base import engine; engine.connect()"
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
poetry run python -c "from src.services.queue import TicketQueue; TicketQueue().redis_client.ping()"
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000

# Kill process
kill -9 $(lsof -ti:8000)
```

## License

Internal Skyscanner project.
