"""Ticket processor orchestration - coordinates all processing steps."""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from src.models.processed_ticket import ProcessedTicket
from src.models.system_config import SystemConfig
from src.services.classifier import LLMClassifier, ClassificationResult
from src.services.confidence_evaluator import ConfidenceEvaluator
from src.services.sensitive_data_scanner import SensitiveDataScanner
from src.services.shadow_mode import ShadowModeManager
from src.services.response_poster import ResponsePoster
from src.services.template_renderer import TemplateRenderer
from src.services.audit_logger import AuditLogger
from src.services.slack_client import SlackClient
from src.services.escalation_service import EscalationService
from src.config.settings import settings

logger = logging.getLogger(__name__)


class TicketProcessor:
    """Orchestrates ticket processing workflow."""

    def __init__(self, db: Session):
        """Initialize ticket processor.

        Args:
            db: Database session
        """
        self.db = db
        self.classifier = LLMClassifier()
        self.evaluator = ConfidenceEvaluator()
        self.scanner = SensitiveDataScanner()
        self.response_poster = ResponsePoster()
        self.escalation_service = EscalationService()

    def process_ticket(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single ticket through full workflow.

        Args:
            webhook_payload: Jira webhook payload

        Returns:
            Processing result dictionary

        Constitutional requirements:
        - FR-001 to FR-007: Auto-response logic
        - FR-008 to FR-011: Escalation logic
        - FR-012: Follow-up detection
        - FR-013, FR-014: Audit logging
        - FR-019: Shadow mode
        - FR-020: Kill switch
        """
        start_time = datetime.utcnow()

        # Extract ticket info
        issue = webhook_payload.get("issue", {})
        ticket_id = issue.get("id")
        ticket_key = issue.get("key")
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        description = fields.get("description", "")

        logger.info(f"Processing ticket {ticket_key}: {summary[:50]}...")

        try:
            # Step 1: Check kill switch (FR-020)
            if not self._check_automation_enabled():
                return self._escalate(
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    webhook_payload=webhook_payload,
                    reason="Automation disabled (kill switch activated)",
                    confidence_scores={},
                    processing_duration_ms=None,
                )

            # Step 2: Check for follow-ups (FR-012)
            if self._is_follow_up(ticket_id):
                return self._escalate(
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    webhook_payload=webhook_payload,
                    reason="Follow-up detected on previously processed ticket",
                    confidence_scores={},
                    processing_duration_ms=None,
                )

            # Step 3: Mark ticket as processed
            self._mark_ticket_processed(ticket_id, ticket_key)

            # Step 4: Scan for sensitive data (FR-010)
            has_sensitive, detected_items = self.scanner.scan_ticket(
                summary, description
            )
            if has_sensitive:
                reason = self.scanner.get_escalation_reason(detected_items)
                return self._escalate(
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    webhook_payload=webhook_payload,
                    reason=reason,
                    confidence_scores={},
                    processing_duration_ms=self._get_duration_ms(start_time),
                )

            # Step 5: Load canned responses
            config = ShadowModeManager.load_canned_response_config()
            active_responses = config.get_active_responses()

            if not active_responses:
                return self._escalate(
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    webhook_payload=webhook_payload,
                    reason="No active canned responses available",
                    confidence_scores={},
                    processing_duration_ms=self._get_duration_ms(start_time),
                )

            # Step 6: Classify ticket (FR-002, FR-003)
            reporter_name = fields.get("reporter", {}).get("displayName", "Reporter")

            try:
                classification = self.classifier.classify_ticket(
                    ticket_key=ticket_key,
                    summary=summary,
                    description=description,
                    reporter=reporter_name,
                    canned_responses=active_responses,
                    timeout=30,
                )
            except Exception as e:
                logger.error(f"Classification failed for {ticket_key}: {e}")
                return self._escalate(
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    webhook_payload=webhook_payload,
                    reason=f"Classification timeout or error: {str(e)[:100]}",
                    confidence_scores={},
                    processing_duration_ms=self._get_duration_ms(start_time),
                )

            # Step 7: Evaluate confidence (FR-004, FR-008, FR-009)
            action, response_id, escalation_reason = self.evaluator.evaluate(
                classification
            )

            # Step 8: Check shadow mode (FR-019)
            is_shadow_mode, _ = ShadowModeManager.check_shadow_mode(self.db, config)

            if is_shadow_mode:
                # Log action as 'shadow' instead of executing
                action = "shadow"
                logger.info(f"Shadow mode active - action logged but not executed")

            # Step 9: Execute action
            processing_duration_ms = self._get_duration_ms(start_time)

            if action == "auto_respond" or action == "shadow":
                # Get the matched response
                matched_response = next(
                    (r for r in active_responses if r.id == response_id), None
                )

                if not matched_response:
                    logger.error(f"Matched response {response_id} not found")
                    return self._escalate(
                        ticket_id=ticket_id,
                        ticket_key=ticket_key,
                        webhook_payload=webhook_payload,
                        reason=f"Internal error: response {response_id} not found",
                        confidence_scores=classification.confidence_scores,
                        processing_duration_ms=processing_duration_ms,
                    )

                # Post response (or skip if shadow mode)
                if action == "auto_respond":
                    return self._auto_respond(
                        ticket_id=ticket_id,
                        ticket_key=ticket_key,
                        webhook_payload=webhook_payload,
                        matched_response=matched_response,
                        confidence_scores=classification.confidence_scores,
                        config_version=config.version,
                        processing_duration_ms=processing_duration_ms,
                    )
                else:  # shadow mode
                    return self._log_shadow_action(
                        ticket_id=ticket_id,
                        ticket_key=ticket_key,
                        webhook_payload=webhook_payload,
                        matched_response=matched_response,
                        confidence_scores=classification.confidence_scores,
                        config_version=config.version,
                        processing_duration_ms=processing_duration_ms,
                    )

            else:  # escalate
                return self._escalate(
                    ticket_id=ticket_id,
                    ticket_key=ticket_key,
                    webhook_payload=webhook_payload,
                    reason=escalation_reason,
                    confidence_scores=classification.confidence_scores,
                    processing_duration_ms=processing_duration_ms,
                )

        except Exception as e:
            logger.error(f"Unexpected error processing {ticket_key}: {e}", exc_info=True)
            # Fail-safe: escalate on any error (FR-022)
            return self._escalate(
                ticket_id=ticket_id,
                ticket_key=ticket_key,
                webhook_payload=webhook_payload,
                reason=f"Processing error: {str(e)[:100]}",
                confidence_scores={},
                processing_duration_ms=self._get_duration_ms(start_time),
            )

    def _check_automation_enabled(self) -> bool:
        """Check if automation is enabled (kill switch check).

        Returns:
            True if automation enabled
        """
        try:
            system_config = (
                self.db.query(SystemConfig).filter(SystemConfig.id == 1).first()
            )
            if not system_config:
                logger.warning("SystemConfig not found, assuming enabled")
                return True
            return system_config.automation_enabled
        except Exception as e:
            logger.error(f"Failed to check kill switch: {e}")
            # Fail-safe: assume disabled on error
            return False

    def _is_follow_up(self, ticket_id: str) -> bool:
        """Check if ticket has been processed before.

        Args:
            ticket_id: Jira ticket ID

        Returns:
            True if ticket already processed
        """
        try:
            existing = (
                self.db.query(ProcessedTicket)
                .filter(ProcessedTicket.ticket_id == ticket_id)
                .first()
            )
            return existing is not None
        except Exception as e:
            logger.error(f"Failed to check follow-up: {e}")
            # Fail-safe: assume it's a follow-up to avoid double-processing
            return True

    def _mark_ticket_processed(self, ticket_id: str, ticket_key: str) -> None:
        """Mark ticket as processed.

        Args:
            ticket_id: Jira ticket ID
            ticket_key: Jira ticket key
        """
        try:
            processed_ticket = ProcessedTicket(
                ticket_id=ticket_id,
                ticket_key=ticket_key,
            )
            self.db.add(processed_ticket)
            self.db.commit()
            logger.debug(f"Marked {ticket_key} as processed")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to mark ticket processed: {e}")

    def _auto_respond(
        self,
        ticket_id: str,
        ticket_key: str,
        webhook_payload: Dict[str, Any],
        matched_response: Any,
        confidence_scores: Dict[str, Any],
        config_version: str,
        processing_duration_ms: int,
    ) -> Dict[str, Any]:
        """Auto-respond to ticket."""
        # Extract template variables
        issue = webhook_payload.get("issue", {})
        template_vars = TemplateRenderer.extract_variables_from_issue(issue)

        # Post response
        result = self.response_poster.post_response(
            ticket_key=ticket_key,
            canned_response=matched_response,
            issue_reporter=template_vars["issue_reporter"],
            issue_assignee=template_vars["issue_assignee"],
        )

        # Log to audit
        audit_log = AuditLogger.log_ticket_processing(
            db=self.db,
            ticket_id=ticket_id,
            ticket_key=ticket_key,
            ticket_snapshot=webhook_payload,
            confidence_scores=confidence_scores,
            action="auto_respond",
            matched_response_id=matched_response.id,
            comment_id=result["comment_id"],
            comment_posted_at=result["posted_at"],
            config_version=config_version,
            processing_duration_ms=processing_duration_ms,
        )

        logger.info(f"Auto-responded to {ticket_key} with {matched_response.id}")

        return {
            "status": "auto_responded",
            "ticket_key": ticket_key,
            "response_id": matched_response.id,
            "comment_id": result["comment_id"],
            "audit_log_id": str(audit_log.id),
        }

    def _log_shadow_action(
        self,
        ticket_id: str,
        ticket_key: str,
        webhook_payload: Dict[str, Any],
        matched_response: Any,
        confidence_scores: Dict[str, Any],
        config_version: str,
        processing_duration_ms: int,
    ) -> Dict[str, Any]:
        """Log shadow mode action."""
        # Log to audit with action='shadow'
        audit_log = AuditLogger.log_ticket_processing(
            db=self.db,
            ticket_id=ticket_id,
            ticket_key=ticket_key,
            ticket_snapshot=webhook_payload,
            confidence_scores=confidence_scores,
            action="shadow",
            matched_response_id=matched_response.id,
            config_version=config_version,
            processing_duration_ms=processing_duration_ms,
        )

        logger.info(
            f"Shadow mode: Would have responded to {ticket_key} with {matched_response.id}"
        )

        return {
            "status": "shadow",
            "ticket_key": ticket_key,
            "response_id": matched_response.id,
            "audit_log_id": str(audit_log.id),
        }

    def _escalate(
        self,
        ticket_id: str,
        ticket_key: str,
        webhook_payload: Dict[str, Any],
        reason: str,
        confidence_scores: Dict[str, Any],
        processing_duration_ms: Optional[int],
    ) -> Dict[str, Any]:
        """Escalate ticket to human."""
        # Log to audit
        audit_log = AuditLogger.log_ticket_processing(
            db=self.db,
            ticket_id=ticket_id,
            ticket_key=ticket_key,
            ticket_snapshot=webhook_payload,
            confidence_scores=confidence_scores,
            action="escalate",
            escalation_reason=reason,
            processing_duration_ms=processing_duration_ms,
        )

        # Send Slack escalation using EscalationService (with retry logic)
        try:
            issue = webhook_payload.get("issue", {})
            fields = issue.get("fields", {})

            self.escalation_service.escalate_ticket(
                ticket_key=ticket_key,
                ticket_title=fields.get("summary", ""),
                escalation_reason=reason,
                confidence_scores=confidence_scores,
                jira_url=f"{settings.JIRA_BASE_URL}/browse/{ticket_key}",
                dashboard_url=f"{settings.DASHBOARD_URL}/tickets/{ticket_key}",
                reporter=fields.get("reporter", {}).get("displayName", "Unknown"),
                created_at=fields.get("created", ""),
                description_snippet=fields.get("description", "")[:200],
            )
        except Exception as e:
            logger.error(f"Failed to escalate {ticket_key}: {e}")
            # Don't fail the escalation if Slack fails - it's queued for retry

        logger.info(f"Escalated {ticket_key}: {reason}")

        return {
            "status": "escalated",
            "ticket_key": ticket_key,
            "reason": reason,
            "audit_log_id": str(audit_log.id),
        }

    @staticmethod
    def _get_duration_ms(start_time: datetime) -> int:
        """Calculate processing duration in milliseconds.

        Args:
            start_time: Processing start time

        Returns:
            Duration in milliseconds
        """
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        return int(duration)
