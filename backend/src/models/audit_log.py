"""AuditLog model - immutable record of every ticket processed."""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.models.base import Base


class AuditLog(Base):
    """Audit log table - append-only record of all ticket processing.

    Constitutional requirement: FR-013, FR-014
    This table is immutable - updates and deletes are prevented by database trigger.
    """

    __tablename__ = "audit_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Ticket identification
    ticket_id = Column(String(50), nullable=False, index=True)
    ticket_key = Column(String(50), nullable=False)

    # Ticket snapshot (full Jira payload)
    ticket_snapshot = Column(JSONB, nullable=False)

    # Classification results
    confidence_scores = Column(JSONB, nullable=False)
    matched_response_id = Column(String(100), nullable=True)

    # Decision and action
    action = Column(String(20), nullable=False, index=True)
    escalation_reason = Column(String(500), nullable=True)

    # Jira interaction
    comment_id = Column(String(50), nullable=True)
    comment_posted_at = Column(DateTime, nullable=True)
    retracted_at = Column(DateTime, nullable=True, index=True)
    retracted_by = Column(String(100), nullable=True)

    # System metadata
    system_version = Column(String(20), nullable=False)
    config_version = Column(String(20), nullable=False)
    processing_duration_ms = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "action IN ('auto_respond', 'escalate', 'shadow')",
            name="valid_action",
        ),
        CheckConstraint(
            "(action = 'escalate' AND escalation_reason IS NOT NULL) OR (action != 'escalate')",
            name="escalation_reason_required",
        ),
        CheckConstraint(
            "(action = 'auto_respond' AND matched_response_id IS NOT NULL) OR (action != 'auto_respond')",
            name="matched_response_required",
        ),
        Index("idx_audit_logs_created_at", "created_at", postgresql_using="btree"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AuditLog(id={self.id}, ticket_key={self.ticket_key}, action={self.action})>"
