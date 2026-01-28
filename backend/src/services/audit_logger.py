"""Audit logger service for immutable audit log entries."""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.models.base import get_db

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for writing to immutable audit logs.

    Constitutional requirement: FR-013, FR-014
    All entries are append-only and cannot be modified or deleted.
    """

    @staticmethod
    def log_ticket_processing(
        db: Session,
        ticket_id: str,
        ticket_key: str,
        ticket_snapshot: Dict[str, Any],
        confidence_scores: Dict[str, Any],
        action: str,
        matched_response_id: Optional[str] = None,
        escalation_reason: Optional[str] = None,
        comment_id: Optional[str] = None,
        comment_posted_at: Optional[datetime] = None,
        system_version: str = "v1.0.0",
        config_version: str = "1.0.0",
        processing_duration_ms: Optional[int] = None,
    ) -> AuditLog:
        """Create an audit log entry for ticket processing.

        Args:
            db: Database session
            ticket_id: Jira ticket ID
            ticket_key: Jira ticket key (e.g., CASSINI-1234)
            ticket_snapshot: Full ticket data from webhook
            confidence_scores: Classification confidence scores
            action: Action taken ('auto_respond', 'escalate', 'shadow')
            matched_response_id: Canned response ID if matched
            escalation_reason: Reason for escalation
            comment_id: Jira comment ID if response posted
            comment_posted_at: Timestamp when response posted
            system_version: Application version
            config_version: Canned response config version
            processing_duration_ms: Processing duration in milliseconds

        Returns:
            Created AuditLog entry

        Raises:
            ValueError: If action is invalid or required fields missing
        """
        # Validate action
        valid_actions = ["auto_respond", "escalate", "shadow"]
        if action not in valid_actions:
            raise ValueError(f"Invalid action '{action}'. Must be one of: {valid_actions}")

        # Validate action-specific requirements
        if action == "auto_respond" and not matched_response_id:
            raise ValueError("matched_response_id required for auto_respond action")

        if action == "escalate" and not escalation_reason:
            raise ValueError("escalation_reason required for escalate action")

        # Create audit log entry
        audit_log = AuditLog(
            ticket_id=ticket_id,
            ticket_key=ticket_key,
            ticket_snapshot=ticket_snapshot,
            confidence_scores=confidence_scores,
            matched_response_id=matched_response_id,
            action=action,
            escalation_reason=escalation_reason,
            comment_id=comment_id,
            comment_posted_at=comment_posted_at,
            system_version=system_version,
            config_version=config_version,
            processing_duration_ms=processing_duration_ms,
        )

        try:
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)

            logger.info(
                f"Created audit log {audit_log.id} for {ticket_key} "
                f"(action: {action})"
            )

            return audit_log

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create audit log for {ticket_key}: {e}")
            raise

    @staticmethod
    def log_retraction(
        db: Session,
        audit_log_id: str,
        retracted_by: str,
    ) -> AuditLog:
        """Update audit log to mark response as retracted.

        Note: This is one of the few allowed updates to audit_logs table.
        Only retracted_at and retracted_by fields can be updated.

        Args:
            db: Database session
            audit_log_id: Audit log ID to update
            retracted_by: User who retracted

        Returns:
            Updated AuditLog entry

        Raises:
            ValueError: If audit log not found or already retracted
        """
        try:
            audit_log = db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()

            if not audit_log:
                raise ValueError(f"Audit log {audit_log_id} not found")

            if audit_log.retracted_at:
                raise ValueError(f"Audit log {audit_log_id} already retracted")

            # Check if within retraction window (5 minutes)
            if audit_log.comment_posted_at:
                elapsed = (datetime.utcnow() - audit_log.comment_posted_at).total_seconds()
                if elapsed > 300:  # 5 minutes
                    raise ValueError(
                        f"Retraction window expired (posted {int(elapsed)}s ago)"
                    )

            # Update retraction fields
            audit_log.retracted_at = datetime.utcnow()
            audit_log.retracted_by = retracted_by

            db.commit()
            db.refresh(audit_log)

            logger.info(
                f"Marked audit log {audit_log_id} as retracted by {retracted_by}"
            )

            return audit_log

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log retraction for {audit_log_id}: {e}")
            raise

    @staticmethod
    def get_audit_log_by_ticket(
        db: Session,
        ticket_key: str,
    ) -> Optional[AuditLog]:
        """Get most recent audit log for a ticket.

        Args:
            db: Database session
            ticket_key: Jira ticket key

        Returns:
            AuditLog entry or None
        """
        try:
            return (
                db.query(AuditLog)
                .filter(AuditLog.ticket_key == ticket_key)
                .order_by(AuditLog.created_at.desc())
                .first()
            )
        except Exception as e:
            logger.error(f"Failed to get audit log for {ticket_key}: {e}")
            return None

    @staticmethod
    def get_audit_log_by_id(
        db: Session,
        audit_log_id: str,
    ) -> Optional[AuditLog]:
        """Get audit log by ID.

        Args:
            db: Database session
            audit_log_id: Audit log UUID

        Returns:
            AuditLog entry or None
        """
        try:
            return db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()
        except Exception as e:
            logger.error(f"Failed to get audit log {audit_log_id}: {e}")
            return None
