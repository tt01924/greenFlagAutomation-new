"""Shadow mode state management."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from src.models.canned_response import CannedResponseConfig
from src.models.system_config import SystemConfig
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ShadowModeManager:
    """Manages shadow mode state and transitions."""

    @staticmethod
    def check_shadow_mode(
        db: Session,
        config: CannedResponseConfig,
    ) -> Tuple[bool, Optional[datetime]]:
        """Check if system is in shadow mode.

        Args:
            db: Database session
            config: Canned response configuration

        Returns:
            Tuple of (is_shadow_mode, shadow_mode_until)
        """
        # Calculate shadow mode end time
        activated_at = config.activated_at.replace(tzinfo=timezone.utc)
        shadow_mode_until = activated_at + timedelta(hours=config.shadow_mode_hours)

        now = datetime.now(timezone.utc)
        is_shadow_mode = now < shadow_mode_until

        if is_shadow_mode:
            remaining_hours = (shadow_mode_until - now).total_seconds() / 3600
            logger.info(
                f"Shadow mode active - {remaining_hours:.1f} hours remaining "
                f"(until {shadow_mode_until.isoformat()})"
            )
        else:
            logger.debug("Shadow mode not active")

        # Update system_config table
        ShadowModeManager._update_system_config(db, is_shadow_mode, shadow_mode_until)

        return is_shadow_mode, shadow_mode_until

    @staticmethod
    def _update_system_config(
        db: Session,
        is_shadow_mode: bool,
        shadow_mode_until: datetime,
    ) -> None:
        """Update system_config table with shadow mode state.

        Args:
            db: Database session
            is_shadow_mode: Whether shadow mode is active
            shadow_mode_until: Shadow mode end time
        """
        try:
            # Get or create system config
            system_config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

            if not system_config:
                system_config = SystemConfig(id=1)
                db.add(system_config)

            # Update shadow mode fields
            system_config.shadow_mode_active = is_shadow_mode
            system_config.shadow_mode_until = shadow_mode_until if is_shadow_mode else None

            db.commit()

            logger.debug(f"Updated system_config: shadow_mode_active={is_shadow_mode}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update system_config: {e}")

    @staticmethod
    def load_canned_response_config() -> CannedResponseConfig:
        """Load canned response configuration from YAML.

        Returns:
            CannedResponseConfig instance

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        try:
            config = CannedResponseConfig.load_from_yaml(settings.CANNED_RESPONSES_PATH)
            logger.info(
                f"Loaded canned response config version {config.version} "
                f"with {len(config.canned_responses)} responses"
            )
            return config

        except FileNotFoundError:
            logger.error(f"Config file not found: {settings.CANNED_RESPONSES_PATH}")
            raise

        except Exception as e:
            logger.error(f"Failed to load canned response config: {e}")
            raise ValueError(f"Invalid canned response config: {e}")

    @staticmethod
    def get_shadow_mode_status(db: Session) -> dict:
        """Get current shadow mode status.

        Args:
            db: Database session

        Returns:
            Dictionary with shadow mode status info
        """
        try:
            system_config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

            if not system_config:
                return {
                    "active": False,
                    "until": None,
                    "remaining_hours": None,
                }

            if not system_config.shadow_mode_active:
                return {
                    "active": False,
                    "until": None,
                    "remaining_hours": None,
                }

            # Calculate remaining time
            now = datetime.now(timezone.utc)
            until = system_config.shadow_mode_until.replace(tzinfo=timezone.utc)
            remaining = (until - now).total_seconds() / 3600

            return {
                "active": True,
                "until": until.isoformat(),
                "remaining_hours": round(remaining, 1),
            }

        except Exception as e:
            logger.error(f"Failed to get shadow mode status: {e}")
            return {
                "active": False,
                "until": None,
                "remaining_hours": None,
                "error": str(e),
            }
