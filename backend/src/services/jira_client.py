"""Jira client wrapper for interacting with Jira Cloud API."""

import logging
from typing import Optional, Dict, Any
from atlassian import Jira

from src.config.settings import settings

logger = logging.getLogger(__name__)


class JiraClient:
    """Wrapper for Jira API operations."""

    def __init__(self) -> None:
        """Initialize Jira client."""
        self.client = Jira(
            url=settings.JIRA_BASE_URL,
            username=settings.JIRA_EMAIL,
            password=settings.JIRA_API_TOKEN,
            cloud=True,
        )

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get issue details by key.

        Args:
            issue_key: Jira issue key (e.g., CASSINI-1234)

        Returns:
            Issue data dictionary

        Raises:
            Exception: If issue not found or API error
        """
        try:
            issue = self.client.issue(issue_key)
            logger.info(f"Retrieved issue {issue_key}")
            return issue
        except Exception as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            raise

    def post_comment(
        self,
        issue_key: str,
        comment_body: str,
        visibility: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Post a comment to a Jira issue.

        Args:
            issue_key: Jira issue key
            comment_body: Comment text (supports Markdown)
            visibility: Optional visibility settings (e.g., {"type": "role", "value": "Administrators"})

        Returns:
            Created comment data

        Raises:
            Exception: If comment posting fails
        """
        try:
            comment = self.client.issue_add_comment(
                issue_key,
                comment_body,
                visibility=visibility,
            )
            logger.info(f"Posted comment to {issue_key}: {comment.get('id')}")
            return comment
        except Exception as e:
            logger.error(f"Failed to post comment to {issue_key}: {e}")
            raise

    def update_comment(
        self,
        issue_key: str,
        comment_id: str,
        new_body: str,
    ) -> Dict[str, Any]:
        """Update an existing comment.

        Args:
            issue_key: Jira issue key
            comment_id: Comment ID to update
            new_body: New comment text

        Returns:
            Updated comment data

        Raises:
            Exception: If comment update fails
        """
        try:
            # Get the comment first to verify it exists
            self.client.comment(issue_key, comment_id)

            # Update the comment
            updated = self.client.update_comment(
                issue_key,
                comment_id,
                new_body,
            )
            logger.info(f"Updated comment {comment_id} on {issue_key}")
            return updated
        except Exception as e:
            logger.error(f"Failed to update comment {comment_id} on {issue_key}: {e}")
            raise

    def add_label(self, issue_key: str, label: str) -> None:
        """Add a label to an issue.

        Args:
            issue_key: Jira issue key
            label: Label to add

        Raises:
            Exception: If label addition fails
        """
        try:
            self.client.update_issue_field(
                issue_key,
                {"update": {"labels": [{"add": label}]}},
            )
            logger.info(f"Added label '{label}' to {issue_key}")
        except Exception as e:
            logger.error(f"Failed to add label to {issue_key}: {e}")
            raise

    def retract_response(
        self,
        issue_key: str,
        comment_id: str,
        original_body: str,
        retracted_by: str,
    ) -> Dict[str, Any]:
        """Retract an automated response by editing the comment.

        Args:
            issue_key: Jira issue key
            comment_id: Comment ID to retract
            original_body: Original comment text
            retracted_by: User who requested retraction

        Returns:
            Updated comment data
        """
        strikethrough_body = f"~~{original_body}~~\n\n_[Response retracted by {retracted_by}]_"

        try:
            updated = self.update_comment(issue_key, comment_id, strikethrough_body)

            # Also post a new comment explaining the retraction
            self.post_comment(
                issue_key,
                f"The automated response above has been retracted by {retracted_by}. "
                f"A Cassini team member will review this ticket manually.",
            )

            logger.info(f"Retracted comment {comment_id} on {issue_key}")
            return updated
        except Exception as e:
            logger.error(f"Failed to retract comment {comment_id} on {issue_key}: {e}")
            raise

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Jira webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature: Signature from X-Hub-Signature-256 header

        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib

        if not signature.startswith("sha256="):
            return False

        expected_signature = hmac.new(
            settings.JIRA_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        provided_signature = signature.replace("sha256=", "")

        return hmac.compare_digest(expected_signature, provided_signature)
