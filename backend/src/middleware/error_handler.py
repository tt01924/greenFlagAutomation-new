"""Error handling middleware for FastAPI."""
import logging
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """Global error handling middleware.

    Catches unhandled exceptions and returns appropriate error responses.

    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint

    Returns:
        Response
    """
    try:
        response = await call_next(request)
        return response

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database error",
                "detail": "An error occurred while accessing the database",
            },
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "detail": str(e),
            },
        )

    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred",
            },
        )


class HTTPException(Exception):
    """Custom HTTP exception with status code."""

    def __init__(self, status_code: int, detail: str):
        """Initialize HTTP exception.

        Args:
            status_code: HTTP status code
            detail: Error detail message
        """
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
