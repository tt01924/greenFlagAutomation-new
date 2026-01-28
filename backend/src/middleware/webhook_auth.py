"""Webhook authentication middleware for Jira webhooks."""

import hmac
import hashlib
import logging
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from src.config.settings import settings

logger = logging.getLogger(__name__)


async def verify_jira_webhook_signature(request: Request, call_next: Callable) -> Response:
    """Verify Jira webhook signature.

    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint

    Returns:
        Response
    """
    # Only verify webhook endpoints
    if not request.url.path.startswith("/api/webhooks/jira"):
        return await call_next(request)

    # Skip verification for health checks and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Get signature from header
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature:
        logger.warning(f"Missing webhook signature for {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Missing webhook signature"},
        )

    # Read request body
    body = await request.body()

    # Verify signature
    if not verify_signature(body, signature):
        logger.warning(f"Invalid webhook signature for {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid webhook signature"},
        )

    # Signature valid, continue to endpoint
    return await call_next(request)


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature.

    Args:
        payload: Raw webhook payload bytes
        signature: Signature from X-Hub-Signature-256 header

    Returns:
        True if signature is valid
    """
    if not signature.startswith("sha256="):
        return False

    expected_signature = hmac.new(
        settings.JIRA_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    provided_signature = signature.replace("sha256=", "")

    return hmac.compare_digest(expected_signature, provided_signature)
