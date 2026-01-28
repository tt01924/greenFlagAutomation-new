"""ProcessedTicket model - tracks tickets to prevent re-processing follow-ups."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime

from src.models.base import Base


class ProcessedTicket(Base):
    """Processed ticket table - prevents re-processing of follow-ups.

    Constitutional requirement: FR-012 (MUST NOT respond to follow-ups)
    """

    __tablename__ = "processed_tickets"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Ticket identification
    ticket_id = Column(String(50), nullable=False, unique=True, index=True)
    ticket_key = Column(String(50), nullable=False)

    # Processing metadata
    first_processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    times_seen = Column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        """String representation."""
        return f"<ProcessedTicket(id={self.id}, ticket_key={self.ticket_key}, times_seen={self.times_seen})>"
