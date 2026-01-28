"""Sensitive data scanner for detecting sensitive information in tickets."""
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Sensitive keywords that trigger escalation
SENSITIVE_KEYWORDS = [
    # Credentials
    "password",
    "passwd",
    "pwd",
    "secret",
    "api key",
    "api_key",
    "apikey",
    "access key",
    "access_key",
    "private key",
    "private_key",
    "token",
    "bearer",
    "credentials",
    "credential",
    # Personal data
    "ssn",
    "social security",
    "credit card",
    "card number",
    "cvv",
    "passport",
    # Sensitive patterns
    "sk-",  # API keys often start with sk-
    "xoxb-",  # Slack bot tokens
    "ghp_",  # GitHub personal access tokens
]

# Regex patterns for sensitive data
SENSITIVE_PATTERNS = [
    # AWS Access Key ID format
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    # Generic API key patterns (alphanumeric strings in common formats)
    (r"\b[0-9a-f]{32,64}\b", "Hex token (possible API key)"),
    # Email addresses with passwords nearby
    (r"(password|pwd|secret)[:\s=]+[\w@.-]+", "Password mention"),
    # Credit card numbers (basic pattern)
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "Credit card number"),
    # SSH private key markers
    (r"-----BEGIN .*PRIVATE KEY-----", "Private key"),
    # Bearer tokens
    (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer token"),
]


class SensitiveDataScanner:
    """Scanner for detecting sensitive information in ticket content."""

    @staticmethod
    def scan_ticket(
        summary: str,
        description: str,
    ) -> Tuple[bool, List[str]]:
        """Scan ticket for sensitive data.

        Args:
            summary: Ticket summary/title
            description: Ticket description

        Returns:
            Tuple of (has_sensitive_data, list_of_detected_items)
        """
        detected_items = []

        # Combine all text for scanning
        full_text = f"{summary}\n{description or ''}"
        full_text_lower = full_text.lower()

        # Check for sensitive keywords
        for keyword in SENSITIVE_KEYWORDS:
            if keyword.lower() in full_text_lower:
                detected_items.append(f"Keyword: '{keyword}'")
                logger.info(f"Detected sensitive keyword: {keyword}")

        # Check for sensitive patterns
        for pattern, description_text in SENSITIVE_PATTERNS:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                # Don't log the actual match for security
                detected_items.append(f"Pattern: {description_text}")
                logger.info(f"Detected sensitive pattern: {description_text}")

        has_sensitive_data = len(detected_items) > 0

        if has_sensitive_data:
            logger.warning(
                f"Sensitive data detected: {len(detected_items)} items found"
            )

        return has_sensitive_data, detected_items

    @staticmethod
    def get_escalation_reason(detected_items: List[str]) -> str:
        """Generate escalation reason for sensitive data detection.

        Args:
            detected_items: List of detected sensitive items

        Returns:
            Human-readable escalation reason
        """
        if len(detected_items) == 1:
            return f"Sensitive data detected: {detected_items[0]}"
        else:
            items_str = ", ".join(detected_items[:3])  # Show first 3
            remaining = len(detected_items) - 3
            if remaining > 0:
                items_str += f" and {remaining} more"
            return f"Sensitive data detected: {items_str}"
