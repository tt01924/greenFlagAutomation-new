"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.config.settings import settings
from src.config.logging import setup_logging
from src.api import health, webhooks
from src.middleware.webhook_auth import verify_jira_webhook_signature
# from src.api import dashboard, admin  # Will be added in later phases

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events.

    Args:
        app: FastAPI application
    """
    # Startup
    setup_logging()
    logger.info("Starting Green Flag Automation service")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Automation enabled: {settings.AUTOMATION_ENABLED}")

    yield

    # Shutdown
    logger.info("Shutting down Green Flag Automation service")


# Create FastAPI app
app = FastAPI(
    title="Green Flag Automation",
    description="Automated ticket response system for Cassini Squad",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.DASHBOARD_URL,
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware (security)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.skyscanner.net", "localhost"],
    )

# Add webhook authentication middleware
app.middleware("http")(verify_jira_webhook_signature)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")  # Phase 3 - User Story 1
# app.include_router(dashboard.router, prefix="/api")  # Phase 5
# app.include_router(admin.router, prefix="/api")  # Phase 6


@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "service": "Green Flag Automation",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
