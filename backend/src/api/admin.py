"""Admin API endpoints for system configuration and shadow mode management."""
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.models.system_config import SystemConfig
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.get("/admin/shadow-mode", status_code=status.HTTP_200_OK)
async def get_shadow_mode_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get shadow mode status.

    Returns:
        Dictionary with shadow mode status and timing information

    Constitutional requirement: FR-019 (Shadow mode for new canned responses)
    """
    try:
        # Get system config (singleton with id=1)
        config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

        if not config:
            # Initialize default config if it doesn't exist
            config = SystemConfig(
                id=1,
                automation_enabled=True,
                shadow_mode_active=False,
                shadow_mode_until=None,
            )
            db.add(config)
            db.commit()
            db.refresh(config)

        # Calculate time remaining if shadow mode is active
        time_remaining_seconds = None
        if config.shadow_mode_active and config.shadow_mode_until:
            now = datetime.utcnow()
            if config.shadow_mode_until > now:
                time_remaining_seconds = int(
                    (config.shadow_mode_until - now).total_seconds()
                )
            else:
                # Shadow mode has expired but hasn't been deactivated yet
                time_remaining_seconds = 0

        return {
            "shadow_mode_active": config.shadow_mode_active,
            "shadow_mode_until": (
                config.shadow_mode_until.isoformat()
                if config.shadow_mode_until
                else None
            ),
            "time_remaining_seconds": time_remaining_seconds,
            "time_remaining_hours": (
                round(time_remaining_seconds / 3600, 1)
                if time_remaining_seconds is not None
                else None
            ),
            "automation_enabled": config.automation_enabled,
            "config_version": settings.CONFIG_VERSION,
        }

    except Exception as e:
        logger.error(f"Failed to get shadow mode status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shadow mode status",
        )


@router.post("/admin/shadow-mode/activate", status_code=status.HTTP_200_OK)
async def activate_shadow_mode(
    duration_hours: int = 48, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Activate shadow mode for specified duration.

    Args:
        duration_hours: Number of hours to enable shadow mode (default 48)
        db: Database session

    Returns:
        Updated shadow mode status

    Note: This is typically triggered automatically when canned responses are updated
    """
    try:
        from datetime import timedelta

        # Get or create system config
        config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

        if not config:
            config = SystemConfig(
                id=1, automation_enabled=True, shadow_mode_active=False
            )
            db.add(config)
            db.flush()

        # Activate shadow mode
        now = datetime.utcnow()
        config.shadow_mode_active = True
        config.shadow_mode_until = now + timedelta(hours=duration_hours)

        db.commit()
        db.refresh(config)

        logger.info(
            f"Shadow mode activated until {config.shadow_mode_until.isoformat()}"
        )

        return {
            "shadow_mode_active": True,
            "shadow_mode_until": config.shadow_mode_until.isoformat(),
            "duration_hours": duration_hours,
            "message": f"Shadow mode activated for {duration_hours} hours",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to activate shadow mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate shadow mode",
        )


@router.post("/admin/shadow-mode/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_shadow_mode(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Manually deactivate shadow mode.

    Args:
        db: Database session

    Returns:
        Updated shadow mode status
    """
    try:
        config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System config not found",
            )

        if not config.shadow_mode_active:
            return {
                "shadow_mode_active": False,
                "message": "Shadow mode was already inactive",
            }

        # Deactivate shadow mode
        config.shadow_mode_active = False
        config.shadow_mode_until = None

        db.commit()
        db.refresh(config)

        logger.info("Shadow mode manually deactivated")

        return {
            "shadow_mode_active": False,
            "shadow_mode_until": None,
            "message": "Shadow mode deactivated",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to deactivate shadow mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate shadow mode",
        )


@router.get("/admin/kill-switch", status_code=status.HTTP_200_OK)
async def get_kill_switch_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get kill switch (automation enabled/disabled) status.

    Returns:
        Dictionary with kill switch status

    Constitutional requirement: FR-020 (Kill switch)
    """
    try:
        config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

        if not config:
            # Initialize default config
            config = SystemConfig(
                id=1,
                automation_enabled=True,
                shadow_mode_active=False,
            )
            db.add(config)
            db.commit()
            db.refresh(config)

        return {
            "automation_enabled": config.automation_enabled,
            "status": "enabled" if config.automation_enabled else "disabled",
        }

    except Exception as e:
        logger.error(f"Failed to get kill switch status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve kill switch status",
        )


@router.post("/admin/kill-switch/disable", status_code=status.HTTP_200_OK)
async def disable_automation(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Disable automation (activate kill switch).

    All tickets will be escalated until automation is re-enabled.

    Args:
        db: Database session

    Returns:
        Updated kill switch status
    """
    try:
        config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System config not found",
            )

        if not config.automation_enabled:
            return {
                "automation_enabled": False,
                "message": "Automation was already disabled",
            }

        config.automation_enabled = False
        db.commit()
        db.refresh(config)

        logger.warning("⚠️ KILL SWITCH ACTIVATED - Automation disabled")

        return {
            "automation_enabled": False,
            "status": "disabled",
            "message": "Automation disabled - all tickets will now be escalated",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to disable automation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable automation",
        )


@router.post("/admin/kill-switch/enable", status_code=status.HTTP_200_OK)
async def enable_automation(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Enable automation (deactivate kill switch).

    Resume normal ticket processing.

    Args:
        db: Database session

    Returns:
        Updated kill switch status
    """
    try:
        config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System config not found",
            )

        if config.automation_enabled:
            return {
                "automation_enabled": True,
                "message": "Automation was already enabled",
            }

        config.automation_enabled = True
        db.commit()
        db.refresh(config)

        logger.info("✅ Automation re-enabled")

        return {
            "automation_enabled": True,
            "status": "enabled",
            "message": "Automation enabled - normal ticket processing resumed",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to enable automation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable automation",
        )
