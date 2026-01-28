"""Dashboard API endpoints for viewing tickets, escalations, and reports."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.base import get_db
from src.models.audit_log import AuditLog
from src.services.jira_client import JiraClient
from src.services.audit_logger import AuditLogger
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/tickets", status_code=status.HTTP_200_OK)
async def get_tickets(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get list of processed tickets.

    Args:
        limit: Maximum number of tickets to return
        offset: Offset for pagination
        action: Filter by action type (auto_respond, escalate, shadow)
        db: Database session

    Returns:
        Dictionary with tickets list and metadata
    """
    try:
        # Build query
        query = db.query(AuditLog).order_by(AuditLog.created_at.desc())

        # Apply action filter if specified
        if action:
            if action not in ["auto_respond", "escalate", "shadow"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action filter: {action}",
                )
            query = query.filter(AuditLog.action == action)

        # Get total count
        total_count = query.count()

        # Apply pagination
        tickets = query.limit(limit).offset(offset).all()

        # Format response
        tickets_data = [
            {
                "id": str(ticket.id),
                "ticket_id": ticket.ticket_id,
                "ticket_key": ticket.ticket_key,
                "action": ticket.action,
                "matched_response_id": ticket.matched_response_id,
                "escalation_reason": ticket.escalation_reason,
                "created_at": ticket.created_at.isoformat(),
                "comment_id": ticket.comment_id,
                "retracted_at": ticket.retracted_at.isoformat() if ticket.retracted_at else None,
                "retracted_by": ticket.retracted_by,
                "processing_duration_ms": ticket.processing_duration_ms,
                "ticket_summary": ticket.ticket_snapshot.get("issue", {})
                .get("fields", {})
                .get("summary", ""),
            }
            for ticket in tickets
        ]

        return {
            "tickets": tickets_data,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to get tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tickets",
        )


@router.get("/dashboard/tickets/{ticket_key}", status_code=status.HTTP_200_OK)
async def get_ticket_detail(
    ticket_key: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get detailed information for a specific ticket.

    Args:
        ticket_key: Jira ticket key (e.g., CASSINI-1234)
        db: Database session

    Returns:
        Detailed ticket information
    """
    try:
        # Get audit log entry
        audit_log = (
            db.query(AuditLog)
            .filter(AuditLog.ticket_key == ticket_key)
            .order_by(AuditLog.created_at.desc())
            .first()
        )

        if not audit_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_key} not found",
            )

        # Extract ticket info from snapshot
        issue = audit_log.ticket_snapshot.get("issue", {})
        fields = issue.get("fields", {})

        # Format response
        return {
            "id": str(audit_log.id),
            "ticket_id": audit_log.ticket_id,
            "ticket_key": audit_log.ticket_key,
            "summary": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "reporter": fields.get("reporter", {}).get("displayName", "Unknown"),
            "created": fields.get("created", ""),
            "action": audit_log.action,
            "matched_response_id": audit_log.matched_response_id,
            "escalation_reason": audit_log.escalation_reason,
            "confidence_scores": audit_log.confidence_scores,
            "comment_id": audit_log.comment_id,
            "comment_posted_at": (
                audit_log.comment_posted_at.isoformat() if audit_log.comment_posted_at else None
            ),
            "retracted_at": (
                audit_log.retracted_at.isoformat() if audit_log.retracted_at else None
            ),
            "retracted_by": audit_log.retracted_by,
            "processing_duration_ms": audit_log.processing_duration_ms,
            "system_version": audit_log.system_version,
            "config_version": audit_log.config_version,
            "created_at": audit_log.created_at.isoformat(),
            "jira_url": f"{settings.JIRA_BASE_URL}/browse/{ticket_key}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticket detail for {ticket_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ticket details",
        )


@router.get("/dashboard/escalations", status_code=status.HTTP_200_OK)
async def get_escalations(
    overdue_only: bool = Query(default=False),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get list of escalated tickets.

    Args:
        overdue_only: Only return escalations older than 4 hours
        limit: Maximum number of escalations to return
        offset: Offset for pagination
        db: Database session

    Returns:
        Dictionary with escalations list and metadata
    """
    try:
        # Build query for escalated tickets
        query = (
            db.query(AuditLog)
            .filter(AuditLog.action == "escalate")
            .order_by(AuditLog.created_at.desc())
        )

        # Apply overdue filter if specified
        if overdue_only:
            four_hours_ago = datetime.utcnow() - timedelta(hours=4)
            query = query.filter(AuditLog.created_at < four_hours_ago)

        # Get total count
        total_count = query.count()

        # Apply pagination
        escalations = query.limit(limit).offset(offset).all()

        # Format response
        escalations_data = [
            {
                "id": str(escalation.id),
                "ticket_key": escalation.ticket_key,
                "escalation_reason": escalation.escalation_reason,
                "created_at": escalation.created_at.isoformat(),
                "is_overdue": (datetime.utcnow() - escalation.created_at).total_seconds()
                > 14400,  # 4 hours
                "ticket_summary": escalation.ticket_snapshot.get("issue", {})
                .get("fields", {})
                .get("summary", ""),
                "reporter": escalation.ticket_snapshot.get("issue", {})
                .get("fields", {})
                .get("reporter", {})
                .get("displayName", "Unknown"),
                "confidence_scores": escalation.confidence_scores,
            }
            for escalation in escalations
        ]

        return {
            "escalations": escalations_data,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to get escalations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve escalations",
        )


@router.post("/dashboard/tickets/{ticket_key}/retract", status_code=status.HTTP_200_OK)
async def retract_response(
    ticket_key: str,
    retracted_by: str = Query(..., description="User who is retracting"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retract an automated response.

    Args:
        ticket_key: Jira ticket key
        retracted_by: User email or name
        db: Database session

    Returns:
        Retraction result

    Raises:
        HTTPException: If retraction fails or window expired
    """
    try:
        # Get audit log entry
        audit_log = AuditLogger.get_audit_log_by_ticket(db, ticket_key)

        if not audit_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_key} not found",
            )

        # Check if ticket has an auto-response
        if audit_log.action != "auto_respond":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket {ticket_key} was not auto-responded (action: {audit_log.action})",
            )

        # Check if already retracted
        if audit_log.retracted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Response already retracted at {audit_log.retracted_at.isoformat()}",
            )

        # Check if within retraction window (5 minutes)
        if audit_log.comment_posted_at:
            elapsed_minutes = (datetime.utcnow() - audit_log.comment_posted_at).total_seconds() / 60

            if elapsed_minutes > settings.RETRACTION_WINDOW_MINUTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Retraction window expired (posted {elapsed_minutes:.1f} minutes ago, limit is {settings.RETRACTION_WINDOW_MINUTES} minutes)",
                )

        # Retract in Jira
        jira_client = JiraClient()

        # Get original comment body from ticket snapshot
        original_response = audit_log.ticket_snapshot.get("response_text", "")

        jira_client.retract_response(
            issue_key=ticket_key,
            comment_id=audit_log.comment_id,
            original_body=original_response,
            retracted_by=retracted_by,
        )

        # Update audit log
        updated_audit_log = AuditLogger.log_retraction(
            db=db,
            audit_log_id=str(audit_log.id),
            retracted_by=retracted_by,
        )

        logger.info(f"Retracted response for {ticket_key} by {retracted_by}")

        return {
            "status": "retracted",
            "ticket_key": ticket_key,
            "retracted_at": updated_audit_log.retracted_at.isoformat(),
            "retracted_by": retracted_by,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retract response for {ticket_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retract response: {str(e)}",
        )


@router.get("/dashboard/reports/weekly", status_code=status.HTTP_200_OK)
async def get_weekly_report(
    weeks_ago: int = Query(default=0, ge=0, le=52),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get weekly report with aggregated statistics.

    Args:
        weeks_ago: Number of weeks ago (0 = current week)
        db: Database session

    Returns:
        Weekly report with statistics
    """
    try:
        # Calculate date range for requested week
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday() + (weeks_ago * 7))
        week_end = week_start + timedelta(days=7)

        # Query tickets in date range
        tickets = (
            db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.created_at >= week_start,
                    AuditLog.created_at < week_end,
                )
            )
            .all()
        )

        # Calculate statistics
        total_tickets = len(tickets)
        auto_responded = sum(1 for t in tickets if t.action == "auto_respond")
        escalated = sum(1 for t in tickets if t.action == "escalate")
        shadow = sum(1 for t in tickets if t.action == "shadow")
        retracted = sum(1 for t in tickets if t.retracted_at is not None)

        # Calculate automation rate
        automation_rate = (auto_responded / total_tickets * 100) if total_tickets > 0 else 0

        # Top canned responses
        response_counts = {}
        for ticket in tickets:
            if ticket.matched_response_id:
                response_counts[ticket.matched_response_id] = (
                    response_counts.get(ticket.matched_response_id, 0) + 1
                )

        top_responses = sorted(response_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Top escalation reasons
        escalation_reasons = {}
        for ticket in tickets:
            if ticket.escalation_reason:
                # Normalize reason (remove specifics like percentages)
                reason = ticket.escalation_reason.split("(")[0].strip()
                escalation_reasons[reason] = escalation_reasons.get(reason, 0) + 1

        top_escalation_reasons = sorted(
            escalation_reasons.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "statistics": {
                "total_tickets": total_tickets,
                "auto_responded": auto_responded,
                "escalated": escalated,
                "shadow": shadow,
                "retracted": retracted,
                "automation_rate": round(automation_rate, 1),
                "false_positive_rate": (
                    round(retracted / auto_responded * 100, 1) if auto_responded > 0 else 0
                ),
            },
            "top_responses": [{"response_id": rid, "count": count} for rid, count in top_responses],
            "top_escalation_reasons": [
                {"reason": reason, "count": count} for reason, count in top_escalation_reasons
            ],
        }

    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate weekly report",
        )
