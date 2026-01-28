"""Logging configuration for the application."""

import logging
import sys

from src.config.settings import settings


def setup_logging() -> None:
    """Configure application logging with appropriate log levels.

    Sets up structured logging for the application with the following:
    - Root logger configured with level from settings (INFO, DEBUG, WARNING, ERROR)
    - Timestamp format: YYYY-MM-DD HH:MM:SS
    - Third-party library log levels set to reduce noise
    - Optional LLM debug logging when LLM_DEBUG=True

    This should be called at application startup (FastAPI lifespan)
    and worker initialization.
    """
    # Get log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("slack_sdk").setLevel(logging.INFO)

    # Enable debug logging for LLM if requested
    if settings.LLM_DEBUG:
        logging.getLogger("anthropic").setLevel(logging.DEBUG)
        logging.getLogger("openai").setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.LOG_LEVEL}")
