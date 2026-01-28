"""Daily summary job - sends summary email/Slack at 9 AM UTC."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.models.base import SessionLocal
from src.models.audit_log import AuditLog
from src.services.slack_client import SlackClient
from src.config.logging import setup_logging
from src.config.settings import settings

logger = logging.getLogger(__name__)


def calculate_daily_stats() -> Dict[str, Any]:
    """Calculate statistics for yesterday's tickets.

    Returns:
        Dictionary with statistics
    """
    db = SessionLocal()

    try:
        # Get yesterday's date range
        today = datetime.utcnow().date()
        yesterday_start = datetime.combine(
            today - timedelta(days=1), datetime.min.time()
        )
        yesterday_end = datetime.combine(today, datetime.min.time())

        # Query tickets from yesterday
        tickets = (
            db.query(AuditLog)
            .filter(
                AuditLog.created_at >= yesterday_start,
                AuditLog.created_at < yesterday_end,
            )
            .all()
        )

        # Calculate statistics
        total_tickets = len(tickets)
        auto_responded = sum(1 for t in tickets if t.action == "auto_respond")
        escalated = sum(1 for t in tickets if t.action == "escalate")
        retracted = sum(1 for t in tickets if t.retracted_at is not None)

        # Top response categories
        response_counts: Dict[str, int] = {}
        for ticket in tickets:
            if ticket.matched_response_id:
                response_counts[ticket.matched_response_id] = (
                    response_counts.get(ticket.matched_response_id, 0) + 1
                )

        top_categories = sorted(
            response_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "date": (today - timedelta(days=1)).isoformat(),
            "total_tickets": total_tickets,
            "auto_responded": auto_responded,
            "escalated": escalated,
            "retracted": retracted,
            "top_categories": [
                {"name": name, "count": count} for name, count in top_categories
            ],
        }

    finally:
        db.close()


def send_daily_summary() -> None:
    """Send daily summary via Slack.

    Constitutional requirement: FR-017
    """
    setup_logging()
    logger.info("Starting daily summary job")

    try:
        # Calculate stats
        stats = calculate_daily_stats()

        # Send to Slack
        slack_client = SlackClient()

        slack_client.send_daily_summary(
            channel_id="#cassini-squad",  # TODO: Get from config
            date=stats["date"],
            total_tickets=stats["total_tickets"],
            auto_responded=stats["auto_responded"],
            escalated=stats["escalated"],
            retracted=stats["retracted"],
            top_categories=stats["top_categories"],
        )

        logger.info(f"Daily summary sent for {stats['date']}")

    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}", exc_info=True)
        # Don't raise - this is a non-critical job


def main():
    """Entry point for scheduled execution."""
    send_daily_summary()


if __name__ == "__main__":
    main()
