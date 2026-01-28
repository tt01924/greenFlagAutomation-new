"""Jira webhook endpoints."""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, status, Depends
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.services.queue import TicketQueue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/jira", status_code=status.HTTP_202_ACCEPTED)
async def jira_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Receive Jira webhook events.

    Args:
        request: FastAPI request with webhook payload
        db: Database session

    Returns:
        Acceptance response with ticket ID
    """
    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return {
            "status": "error",
            "error": "Invalid JSON payload",
        }

    # Extract webhook event type
    webhook_event = payload.get("webhookEvent")

    # Only process issue_created and issue_updated events
    if webhook_event not in ["jira:issue_created", "jira:issue_updated"]:
        logger.info(f"Ignoring webhook event: {webhook_event}")
        return {
            "status": "ignored",
            "reason": f"Event type {webhook_event} not processed",
        }

    # Extract issue data
    issue = payload.get("issue", {})
    ticket_id = issue.get("id")
    ticket_key = issue.get("key")

    if not ticket_id or not ticket_key:
        logger.error("Webhook missing ticket_id or ticket_key")
        return {
            "status": "error",
            "error": "Missing ticket_id or ticket_key",
        }

    # Check if ticket has Green-Flag label
    labels = issue.get("fields", {}).get("labels", [])
    if "Green-Flag" not in labels:
        logger.info(f"Ticket {ticket_key} does not have Green-Flag label, ignoring")
        return {
            "status": "ignored",
            "reason": "Ticket does not have Green-Flag label",
        }

    # Enqueue ticket for processing
    try:
        queue = TicketQueue()

        # Determine priority based on webhook event
        priority = "high" if webhook_event == "jira:issue_created" else "normal"

        queue.enqueue_ticket(
            ticket_id=ticket_id,
            ticket_key=ticket_key,
            webhook_payload=payload,
            priority=priority,
        )

        logger.info(
            f"Enqueued ticket {ticket_key} for processing (priority: {priority})"
        )

        return {
            "status": "queued",
            "ticket_id": ticket_id,
            "ticket_key": ticket_key,
        }

    except Exception as e:
        logger.error(f"Failed to enqueue ticket {ticket_key}: {e}")
        return {
            "status": "error",
            "error": "Failed to enqueue ticket",
        }
