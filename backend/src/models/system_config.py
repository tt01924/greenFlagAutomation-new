"""SystemConfig model - runtime configuration and state."""

from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, String, Text, DateTime, DECIMAL, CheckConstraint

from src.models.base import Base


class SystemConfig(Base):
    """System configuration table - singleton for runtime state.

    Stores kill switch status, shadow mode state, and error rate tracking.
    """

    __tablename__ = "system_config"

    # Singleton pattern (only one row with id=1)
    id = Column(Integer, primary_key=True, default=1)

    # Kill switch
    automation_enabled = Column(Boolean, nullable=False, default=True)
    disabled_at = Column(DateTime, nullable=True)
    disabled_by = Column(String(100), nullable=True)
    disable_reason = Column(Text, nullable=True)

    # Shadow mode status (derived from config file)
    shadow_mode_active = Column(Boolean, nullable=False, default=False)
    shadow_mode_until = Column(DateTime, nullable=True)

    # Error rate tracking
    error_rate_last_hour = Column(DECIMAL(5, 4), default=0.0000)
    last_error_rate_check = Column(DateTime, nullable=True)

    # Metadata
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Table constraints
    __table_args__ = (CheckConstraint("id = 1", name="system_config_singleton"),)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SystemConfig(automation_enabled={self.automation_enabled}, "
            f"shadow_mode_active={self.shadow_mode_active})>"
        )
