"""LLM-based ticket classifier using Anthropic Claude with GPT-4 fallback."""

import json
import logging
from typing import Dict, Any, List, Optional
import anthropic
import openai

from src.config.settings import settings
from src.config.prompts import build_classification_prompt
from src.models.canned_response import CannedResponse

logger = logging.getLogger(__name__)


class ClassificationResult:
    """Result of ticket classification."""

    def __init__(
        self,
        confidence_scores: Dict[str, Dict[str, Any]],
        overall_assessment: str,
        flags: Dict[str, bool],
        raw_response: str,
    ):
        """Initialize classification result.

        Args:
            confidence_scores: Dict mapping response_id to {confidence, reasoning}
            overall_assessment: Overall assessment text
            flags: Dictionary of boolean flags (sensitive_data_detected, etc.)
            raw_response: Raw LLM response for debugging
        """
        self.confidence_scores = confidence_scores
        self.overall_assessment = overall_assessment
        self.flags = flags
        self.raw_response = raw_response

    def get_best_match(self) -> Optional[tuple[str, float]]:
        """Get the highest confidence match.

        Returns:
            Tuple of (response_id, confidence) or None if no matches
        """
        if not self.confidence_scores:
            return None

        best_id = max(
            self.confidence_scores.keys(),
            key=lambda k: self.confidence_scores[k].get("confidence", 0),
        )
        best_confidence = self.confidence_scores[best_id]["confidence"]

        return (best_id, best_confidence)

    def is_ambiguous(self, window: float = 0.10) -> bool:
        """Check if multiple responses are within ambiguity window.

        Args:
            window: Confidence window for ambiguity (default 0.10)

        Returns:
            True if ambiguous
        """
        if len(self.confidence_scores) < 2:
            return False

        # Get top 2 confidence scores
        scores = sorted(
            [data["confidence"] for data in self.confidence_scores.values()],
            reverse=True,
        )

        if len(scores) < 2:
            return False

        return (scores[0] - scores[1]) < window


class LLMClassifier:
    """LLM-based classifier for ticket categorization."""

    def __init__(self) -> None:
        """Initialize LLM classifier with Anthropic and OpenAI clients."""
        self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.has_openai_fallback = True
        else:
            self.has_openai_fallback = False

    def classify_ticket(
        self,
        ticket_key: str,
        summary: str,
        description: str,
        reporter: str,
        canned_responses: List[CannedResponse],
        timeout: int = 30,
    ) -> ClassificationResult:
        """Classify a ticket against canned responses.

        Args:
            ticket_key: Jira ticket key
            summary: Ticket summary/title
            description: Ticket description
            reporter: Reporter display name
            canned_responses: List of active canned responses
            timeout: Timeout in seconds (default 30)

        Returns:
            ClassificationResult

        Raises:
            Exception: If classification fails with both providers
        """
        # Build prompt
        prompts = build_classification_prompt(
            ticket_key=ticket_key,
            summary=summary,
            description=description,
            reporter=reporter,
            canned_responses=canned_responses,
        )

        # Try Anthropic first
        try:
            return self._classify_with_anthropic(prompts, timeout)
        except Exception as e:
            logger.warning(f"Anthropic classification failed: {e}")

            # Fall back to OpenAI if available
            if self.has_openai_fallback:
                try:
                    return self._classify_with_openai(prompts, timeout)
                except Exception as e2:
                    logger.error(f"OpenAI fallback also failed: {e2}")
                    raise Exception("Classification failed with both providers")
            else:
                raise

    def _classify_with_anthropic(
        self, prompts: Dict[str, str], timeout: int
    ) -> ClassificationResult:
        """Classify using Anthropic Claude.

        Args:
            prompts: Dictionary with 'system' and 'user' prompts
            timeout: Timeout in seconds

        Returns:
            ClassificationResult
        """
        if settings.LLM_DEBUG:
            logger.debug(f"Anthropic System Prompt: {prompts['system']}")
            logger.debug(f"Anthropic User Prompt: {prompts['user']}")

        try:
            message = self.anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                system=prompts["system"],
                messages=[{"role": "user", "content": prompts["user"]}],
                timeout=timeout,
            )

            response_text = message.content[0].text

            if settings.LLM_DEBUG:
                logger.debug(f"Anthropic Response: {response_text}")

            return self._parse_classification_response(response_text)

        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API timeout after {timeout}s: {e}")
            raise Exception(f"Classification timeout after {timeout}s")
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def _classify_with_openai(self, prompts: Dict[str, str], timeout: int) -> ClassificationResult:
        """Classify using OpenAI GPT-4.

        Args:
            prompts: Dictionary with 'system' and 'user' prompts
            timeout: Timeout in seconds

        Returns:
            ClassificationResult
        """
        if settings.LLM_DEBUG:
            logger.debug(f"OpenAI System Prompt: {prompts['system']}")
            logger.debug(f"OpenAI User Prompt: {prompts['user']}")

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]},
                ],
                max_tokens=2000,
                timeout=timeout,
            )

            response_text = response.choices[0].message.content

            if settings.LLM_DEBUG:
                logger.debug(f"OpenAI Response: {response_text}")

            return self._parse_classification_response(response_text)

        except openai.error.Timeout as e:
            logger.error(f"OpenAI timeout after {timeout}s: {e}")
            raise Exception(f"Classification timeout after {timeout}s")
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _parse_classification_response(self, response_text: str) -> ClassificationResult:
        """Parse LLM JSON response into ClassificationResult.

        Args:
            response_text: Raw LLM response text

        Returns:
            ClassificationResult

        Raises:
            ValueError: If response is not valid JSON or missing required fields
        """
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            data = json.loads(json_str)

            # Parse classifications into confidence_scores dict
            confidence_scores = {}
            for classification in data.get("classifications", []):
                response_id = classification["response_id"]
                confidence_scores[response_id] = {
                    "confidence": classification["confidence"],
                    "reasoning": classification.get("reasoning", ""),
                }

            return ClassificationResult(
                confidence_scores=confidence_scores,
                overall_assessment=data.get("overall_assessment", ""),
                flags=data.get("flags", {}),
                raw_response=response_text,
            )

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Raw response: {response_text}")
            raise ValueError(f"Invalid LLM response format: {e}")
