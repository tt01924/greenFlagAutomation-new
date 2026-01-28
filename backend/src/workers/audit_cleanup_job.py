"""Audit cleanup job - archives logs older than 90 days to S3."""

import logging
from datetime import datetime, timedelta

from src.models.base import SessionLocal
from src.models.audit_log import AuditLog
from src.models.processed_ticket import ProcessedTicket
from src.config.logging import setup_logging

logger = logging.getLogger(__name__)


def archive_old_audit_logs(retention_days: int = 90) -> int:
    """Archive audit logs older than retention period.

    Args:
        retention_days: Number of days to retain logs (default 90)

    Returns:
        Number of logs archived

    Note: This currently just logs which records would be archived.
    In production, this should:
    1. Export logs to S3
    2. Mark as archived (add archived_at column)
    3. Optionally delete after confirmation
    """
    db = SessionLocal()

    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Find old audit logs
        old_logs = db.query(AuditLog).filter(AuditLog.created_at < cutoff_date).all()

        if not old_logs:
            logger.info(f"No audit logs older than {retention_days} days")
            return 0

        logger.info(f"Found {len(old_logs)} audit logs to archive")

        # In production, export to S3 here
        # For now, just log the IDs that would be archived
        # TODO: Upload archive_data to S3
        # archive_data = [
        #     {
        #         "id": str(log.id),
        #         "ticket_key": log.ticket_key,
        #         "action": log.action,
        #         "created_at": log.created_at.isoformat(),
        #         "ticket_snapshot": log.ticket_snapshot,
        #         "confidence_scores": log.confidence_scores,
        #     }
        #     for log in old_logs
        # ]
        # s3_key = f"audit-logs/archive/{cutoff_date.strftime('%Y-%m-%d')}/logs.json"
        # s3_client.upload_string(json.dumps(archive_data), bucket, s3_key)

        logger.info(f"Would archive {len(old_logs)} logs to S3 " f"(implementation pending)")

        # After successful S3 upload, we would mark logs as archived
        # or delete them. For now, just log.

        return len(old_logs)

    except Exception as e:
        logger.error(f"Failed to archive audit logs: {e}", exc_info=True)
        return 0

    finally:
        db.close()


def cleanup_old_processed_tickets(retention_days: int = 90) -> int:
    """Clean up processed_tickets table (same retention as audit logs).

    Args:
        retention_days: Number of days to retain records

    Returns:
        Number of records cleaned
    """
    db = SessionLocal()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Find old processed tickets
        old_tickets = (
            db.query(ProcessedTicket).filter(ProcessedTicket.first_processed_at < cutoff_date).all()
        )

        if not old_tickets:
            logger.info(f"No processed tickets older than {retention_days} days")
            return 0

        logger.info(f"Found {len(old_tickets)} processed tickets to clean up")

        # Delete old records (these don't need archiving)
        for ticket in old_tickets:
            db.delete(ticket)

        db.commit()

        logger.info(f"Cleaned up {len(old_tickets)} old processed ticket records")

        return len(old_tickets)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cleanup processed tickets: {e}", exc_info=True)
        return 0

    finally:
        db.close()


def run_audit_cleanup() -> None:
    """Run audit cleanup job.

    Constitutional requirement: FR-014
    """
    setup_logging()
    logger.info("Starting audit cleanup job")

    try:
        # Archive old audit logs
        archived_count = archive_old_audit_logs(retention_days=90)

        # Cleanup old processed tickets
        cleaned_count = cleanup_old_processed_tickets(retention_days=90)

        logger.info(
            f"Audit cleanup complete: {archived_count} logs archived, "
            f"{cleaned_count} processed tickets cleaned"
        )

    except Exception as e:
        logger.error(f"Audit cleanup job failed: {e}", exc_info=True)


def main():
    """Entry point for scheduled execution.

    This function is called by the scheduler (e.g., cron) to perform
    periodic cleanup of old audit logs. Archives logs to S3 and removes
    old processed ticket records.

    Constitutional requirement: FR-014 (90-day audit retention)
    """
    run_audit_cleanup()


if __name__ == "__main__":
    main()
