"""Health check endpoints."""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.services.queue import TicketQueue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "green-flag-automation",
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Readiness check - verifies all dependencies are available.

    Args:
        db: Database session

    Returns:
        Readiness status with dependency checks
    """
    checks = {
        "database": False,
        "redis": False,
    }

    # Check database
    try:
        db.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        queue = TicketQueue()
        checks["redis"] = queue.health_check()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    # Overall ready if all checks pass
    is_ready = all(checks.values())

    response = {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }

    if not is_ready:
        return response

    return response


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, str]:
    """Liveness check - verifies application is running.

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
    }
