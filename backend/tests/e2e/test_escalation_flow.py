"""E2E test for escalation flow.

This test simulates escalation scenarios:
1. Low confidence classification
2. Ambiguous matches
3. Sensitive data detection
4. Kill switch activated
5. Classification errors
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.processor import TicketProcessor
from src.services.classifier import ClassificationResult
from tests.fixtures.jira_fixtures import get_mock_jira_webhook_payload
from tests.fixtures.llm_fixtures import (
    get_mock_classification_response_low_confidence,
    get_mock_classification_response_ambiguous,
    get_mock_classification_response_sensitive_data,
)
from tests.helpers.db import create_test_db, drop_test_db


@pytest.mark.e2e
def test_escalation_low_confidence():
    """Test escalation due to low confidence classification."""
    db = create_test_db()

    try:
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-2001",
            summary="Something is broken",
            description="Help!",
        )

        with (
            patch("src.services.classifier.LLMClassifier") as mock_classifier_class,
            patch(
                "src.services.escalation_service.EscalationService.escalate_ticket"
            ) as mock_escalate,
        ):

            # Low confidence classification
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier

            mock_result = MagicMock(spec=ClassificationResult)
            mock_result.confidence_scores = {
                "cortex-bug": {"confidence": 0.55, "reasoning": "Unclear system"},
                "documentation-request": {"confidence": 0.48, "reasoning": "Could be docs"},
            }
            mock_result.flags = {
                "sensitive_data_detected": False,
                "multiple_questions": True,
                "urgent_tone": False,
            }
            mock_result.get_best_match.return_value = ("cortex-bug", 0.55)
            mock_result.is_ambiguous.return_value = False
            mock_classifier.classify_ticket.return_value = mock_result

            # Process ticket
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "escalated"
            assert "low confidence" in result["reason"].lower()

            # Verify Slack escalation was called
            mock_escalate.assert_called_once()
            call_args = mock_escalate.call_args[1]
            assert call_args["ticket_key"] == "CASSINI-2001"
            assert "low confidence" in call_args["escalation_reason"].lower()

            # Verify audit log
            from src.models.audit_log import AuditLog

            audit_log = db.query(AuditLog).filter(AuditLog.ticket_key == "CASSINI-2001").first()

            assert audit_log is not None
            assert audit_log.action == "escalate"
            assert audit_log.matched_response_id is None

    finally:
        drop_test_db(db)


@pytest.mark.e2e
def test_escalation_ambiguous_match():
    """Test escalation due to ambiguous classification."""
    db = create_test_db()

    try:
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-2002",
            summary="Cortex issue",
            description="Cortex is not working as expected",
        )

        with (
            patch("src.services.classifier.LLMClassifier") as mock_classifier_class,
            patch(
                "src.services.escalation_service.EscalationService.escalate_ticket"
            ) as mock_escalate,
        ):

            # Ambiguous classification (two high scores within 10%)
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier

            mock_result = MagicMock(spec=ClassificationResult)
            mock_result.confidence_scores = {
                "cortex-bug": {"confidence": 0.78, "reasoning": "Bug mention"},
                "cortex-feature-request": {"confidence": 0.76, "reasoning": "Could be feature"},
            }
            mock_result.flags = {
                "sensitive_data_detected": False,
                "multiple_questions": False,
                "urgent_tone": False,
            }
            mock_result.get_best_match.return_value = ("cortex-bug", 0.78)
            mock_result.is_ambiguous.return_value = True  # Within 10% window
            mock_classifier.classify_ticket.return_value = mock_result

            # Process ticket
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "escalated"
            assert "ambiguous" in result["reason"].lower()

            # Verify escalation message includes both matches
            mock_escalate.assert_called_once()
            call_args = mock_escalate.call_args[1]
            escalation_reason = call_args["escalation_reason"]
            assert "cortex-bug" in escalation_reason
            assert "cortex-feature-request" in escalation_reason

    finally:
        drop_test_db(db)


@pytest.mark.e2e
def test_escalation_sensitive_data():
    """Test escalation due to sensitive data detection."""
    db = create_test_db()

    try:
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-2003",
            summary="Need access",
            description="My password is hunter2 and my API key is sk-abc123",
        )

        with patch(
            "src.services.escalation_service.EscalationService.escalate_ticket"
        ) as mock_escalate:

            # Process ticket (should escalate before classification)
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "escalated"
            assert "sensitive data" in result["reason"].lower()

            # Verify escalation
            mock_escalate.assert_called_once()
            call_args = mock_escalate.call_args[1]
            assert (
                "password" in call_args["escalation_reason"].lower()
                or "api key" in call_args["escalation_reason"].lower()
            )

    finally:
        drop_test_db(db)


@pytest.mark.e2e
def test_escalation_kill_switch():
    """Test escalation when kill switch is activated."""
    db = create_test_db()

    try:
        # Set kill switch to disabled
        from src.models.system_config import SystemConfig

        system_config = SystemConfig(
            id=1,
            automation_enabled=False,
            disable_reason="Testing kill switch",
        )
        db.add(system_config)
        db.commit()

        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-2004",
            summary="Regular ticket",
        )

        with patch(
            "src.services.escalation_service.EscalationService.escalate_ticket"
        ) as mock_escalate:

            # Process ticket
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "escalated"
            assert (
                "kill switch" in result["reason"].lower()
                or "automation disabled" in result["reason"].lower()
            )

            # Verify escalation
            mock_escalate.assert_called_once()

    finally:
        drop_test_db(db)


@pytest.mark.e2e
def test_escalation_classification_error():
    """Test escalation when classification fails."""
    db = create_test_db()

    try:
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-2005",
            summary="Test ticket",
        )

        with (
            patch("src.services.classifier.LLMClassifier") as mock_classifier_class,
            patch(
                "src.services.escalation_service.EscalationService.escalate_ticket"
            ) as mock_escalate,
        ):

            # Classification raises exception
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            mock_classifier.classify_ticket.side_effect = Exception("LLM timeout")

            # Process ticket (should escalate on error)
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "escalated"
            assert "timeout" in result["reason"].lower() or "error" in result["reason"].lower()

            # Verify escalation
            mock_escalate.assert_called_once()

    finally:
        drop_test_db(db)


@pytest.mark.e2e
def test_escalation_urgent_tone():
    """Test escalation when urgent tone is detected."""
    db = create_test_db()

    try:
        webhook_payload = get_mock_jira_webhook_payload(
            ticket_key="CASSINI-2006",
            summary="URGENT: Production is down",
            description="CRITICAL issue, needs immediate attention!",
        )

        with (
            patch("src.services.classifier.LLMClassifier") as mock_classifier_class,
            patch(
                "src.services.escalation_service.EscalationService.escalate_ticket"
            ) as mock_escalate,
        ):

            # Classification with urgent flag
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier

            mock_result = MagicMock(spec=ClassificationResult)
            mock_result.confidence_scores = {
                "on-call-escalation": {"confidence": 0.85, "reasoning": "Urgent"},
            }
            mock_result.flags = {
                "sensitive_data_detected": False,
                "multiple_questions": False,
                "urgent_tone": True,  # Urgent tone detected
            }
            mock_result.get_best_match.return_value = ("on-call-escalation", 0.85)
            mock_result.is_ambiguous.return_value = False
            mock_classifier.classify_ticket.return_value = mock_result

            # Process ticket
            processor = TicketProcessor(db)
            result = processor.process_ticket(webhook_payload)

            # Assertions
            assert result["status"] == "escalated"
            assert "urgent" in result["reason"].lower()

            # Verify escalation
            mock_escalate.assert_called_once()

    finally:
        drop_test_db(db)
