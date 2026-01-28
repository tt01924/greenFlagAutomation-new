"""E2E test for auto-response flow.

This test simulates the full workflow:
1. Jira webhook received
2. Ticket queued in Redis
3. Worker processes ticket
4. LLM classifies ticket
5. Confidence evaluated (high confidence)
6. Response posted to Jira
7. Audit log created
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.services.processor import TicketProcessor
from src.services.classifier import ClassificationResult
from tests.fixtures.jira_fixtures import (
    get_mock_jira_webhook_payload,
    get_mock_jira_comment_response,
)
from tests.fixtures.llm_fixtures import get_mock_classification_response_high_confidence
from tests.helpers.db import create_test_db, drop_test_db


@pytest.mark.e2e
def test_auto_response_flow_success():
    """Test successful auto-response flow end-to-end."""
    # Setup test database
    db = create_test_db()

    try:
        # Create mock webhook payload
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-1234",
            summary="Need IAM permissions for my project",
            description="Can someone help me get IAM permissions? I need access to S3 and DynamoDB.",
            reporter_name="John Doe",
        )

        # Mock external services
        with (
            patch("src.services.classifier.LLMClassifier") as mock_classifier_class,
            patch("src.services.jira_client.JiraClient") as mock_jira_class,
            patch("src.services.slack_client.SlackClient"),
        ):

            # Configure mock LLM classifier
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier

            # Mock classification result (high confidence)
            mock_result = MagicMock(spec=ClassificationResult)
            mock_result.confidence_scores = {
                "iam-request": {"confidence": 0.92, "reasoning": "Clear IAM request"},
                "access-request": {"confidence": 0.45, "reasoning": "General access"},
            }
            mock_result.overall_assessment = "Clear IAM request"
            mock_result.flags = {
                "sensitive_data_detected": False,
                "multiple_questions": False,
                "urgent_tone": False,
            }
            mock_result.get_best_match.return_value = ("iam-request", 0.92)
            mock_result.is_ambiguous.return_value = False

            mock_classifier.classify_ticket.return_value = mock_result

            # Configure mock Jira client
            mock_jira = Mock()
            mock_jira_class.return_value = mock_jira
            mock_jira.post_comment.return_value = get_mock_jira_comment_response(comment_id="67890")

            # Process ticket
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "auto_responded"
            assert result["ticket_key"] == "CASSINI-1234"
            assert result["response_id"] == "iam-request"
            assert "audit_log_id" in result

            # Verify LLM classifier was called
            mock_classifier.classify_ticket.assert_called_once()

            # Verify Jira comment was posted
            mock_jira.post_comment.assert_called_once()
            posted_comment = mock_jira.post_comment.call_args[1]["comment_body"]
            assert "John Doe" in posted_comment  # Reporter name substituted

            # Verify label was added
            mock_jira.add_label.assert_called_once_with("CASSINI-1234", "auto-responded")

            # Verify audit log was created
            from src.models.audit_log import AuditLog

            audit_log = db.query(AuditLog).filter(AuditLog.ticket_key == "CASSINI-1234").first()

            assert audit_log is not None
            assert audit_log.action == "auto_respond"
            assert audit_log.matched_response_id == "iam-request"
            assert audit_log.comment_id == "67890"

    finally:
        drop_test_db(db)


@pytest.mark.e2e
def test_auto_response_flow_with_shadow_mode():
    """Test auto-response flow in shadow mode (logs but doesn't post)."""
    db = create_test_db()

    try:
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-5678",
            summary="Need IAM permissions",
        )

        # Mock shadow mode active
        with (
            patch("src.services.classifier.LLMClassifier") as mock_classifier_class,
            patch("src.services.shadow_mode.ShadowModeManager.check_shadow_mode") as mock_shadow,
            patch("src.services.jira_client.JiraClient"),
        ):

            # Shadow mode active
            mock_shadow.return_value = (True, datetime.utcnow())

            # High confidence classification
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier

            mock_result = MagicMock(spec=ClassificationResult)
            mock_result.confidence_scores = {
                "iam-request": {"confidence": 0.88, "reasoning": "IAM request"},
            }
            mock_result.flags = {
                "sensitive_data_detected": False,
                "multiple_questions": False,
                "urgent_tone": False,
            }
            mock_result.get_best_match.return_value = ("iam-request", 0.88)
            mock_result.is_ambiguous.return_value = False
            mock_classifier.classify_ticket.return_value = mock_result

            # Process ticket
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "shadow"
            assert result["response_id"] == "iam-request"

            # Verify audit log action is 'shadow'
            from src.models.audit_log import AuditLog

            audit_log = db.query(AuditLog).filter(AuditLog.ticket_key == "CASSINI-5678").first()

            assert audit_log is not None
            assert audit_log.action == "shadow"
            assert audit_log.matched_response_id == "iam-request"
            assert audit_log.comment_id is None  # No comment posted in shadow mode

    finally:
        drop_test_db(db)


@pytest.mark.e2e
def test_auto_response_follow_up_detection():
    """Test that follow-ups are detected and escalated."""
    db = create_test_db()

    try:
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-9999",
            ticket_id="99999",
        )

        # Mark ticket as already processed
        from src.models.processed_ticket import ProcessedTicket

        processed = ProcessedTicket(
            ticket_id="99999",
            ticket_key="CASSINI-9999",
        )
        db.add(processed)
        db.commit()

        # Process ticket (should escalate as follow-up)
        with patch("src.services.escalation_service.EscalationService.escalate_ticket"):
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "escalated"
            assert "follow-up" in result["reason"].lower()

    finally:
        drop_test_db(db)
