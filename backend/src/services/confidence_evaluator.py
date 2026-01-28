"""Confidence evaluator for determining if classification should trigger auto-response."""

import logging
from typing import Dict, Any, Optional, Tuple

from src.config.settings import settings
from src.services.classifier import ClassificationResult

logger = logging.getLogger(__name__)


class ConfidenceEvaluator:
    """Evaluates classification confidence to determine action."""

    def __init__(
        self,
        auto_respond_threshold: float = None,
        ambiguity_window: float = None,
    ):
        """Initialize confidence evaluator.

        Args:
            auto_respond_threshold: Minimum confidence for auto-response (default from settings)
            ambiguity_window: Window for considering matches ambiguous (default from settings)
        """
        self.auto_respond_threshold = auto_respond_threshold or settings.AUTO_RESPOND_THRESHOLD
        self.ambiguity_window = ambiguity_window or settings.AMBIGUITY_WINDOW

    def evaluate(
        self, classification: ClassificationResult
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Evaluate classification result and determine action.

        Args:
            classification: Classification result from LLM

        Returns:
            Tuple of (action, response_id, escalation_reason)
            - action: 'auto_respond' or 'escalate'
            - response_id: Matched response ID if auto_respond, else None
            - escalation_reason: Reason for escalation if escalate, else None
        """
        # Check for sensitive data flag
        if classification.flags.get("sensitive_data_detected", False):
            logger.warning("Sensitive data detected, escalating")
            return (
                "escalate",
                None,
                "Sensitive data detected in ticket content",
            )

        # Check for multiple questions flag
        if classification.flags.get("multiple_questions", False):
            logger.info("Multiple questions detected, may escalate if confidence low")
            # Continue evaluation but this is a red flag

        # Check for urgent tone flag
        if classification.flags.get("urgent_tone", False):
            logger.info("Urgent tone detected, considering escalation")
            # Urgent tickets should be reviewed by humans
            return (
                "escalate",
                None,
                "Ticket tone suggests urgency - requires human review",
            )

        # Get best match
        best_match = classification.get_best_match()

        if not best_match:
            logger.warning("No classification matches found")
            return (
                "escalate",
                None,
                "No canned response matches found",
            )

        response_id, confidence = best_match

        # Check if confidence meets threshold
        if confidence < self.auto_respond_threshold:
            logger.info(
                f"Confidence {confidence:.2%} below threshold {self.auto_respond_threshold:.2%}"
            )
            return (
                "escalate",
                None,
                f"Low confidence - highest match: {response_id} ({confidence:.0%})",
            )

        # Check for ambiguous matches
        if classification.is_ambiguous(self.ambiguity_window):
            # Get top 2 matches for escalation message
            top_matches = sorted(
                classification.confidence_scores.items(),
                key=lambda x: x[1]["confidence"],
                reverse=True,
            )[:2]

            match_str = ", ".join(
                [f"{rid} ({data['confidence']:.0%})" for rid, data in top_matches]
            )

            logger.info(f"Ambiguous matches detected: {match_str}")
            return (
                "escalate",
                None,
                f"Ambiguous match - top candidates within {self.ambiguity_window:.0%}: {match_str}",
            )

        # All checks passed - auto-respond
        logger.info(f"Classification passed all checks: {response_id} ({confidence:.2%})")
        return ("auto_respond", response_id, None)

    def get_top_matches_summary(
        self, confidence_scores: Dict[str, Dict[str, Any]], top_n: int = 3
    ) -> str:
        """Get formatted summary of top matches.

        Args:
            confidence_scores: Classification confidence scores
            top_n: Number of top matches to include

        Returns:
            Formatted string of top matches
        """
        sorted_matches = sorted(
            confidence_scores.items(),
            key=lambda x: x[1]["confidence"],
            reverse=True,
        )[:top_n]

        lines = []
        for i, (response_id, data) in enumerate(sorted_matches, 1):
            confidence = data["confidence"]
            reasoning = data.get("reasoning", "No reasoning provided")
            lines.append(f"{i}. {response_id} ({confidence:.0%}) - {reasoning[:100]}")

        return "\n".join(lines)
