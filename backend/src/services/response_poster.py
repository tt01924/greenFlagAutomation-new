"""Response poster for posting canned responses to Jira."""
import logging
from typing import Dict, Any
from datetime import datetime

from src.services.jira_client import JiraClient
from src.services.template_renderer import TemplateRenderer
from src.models.canned_response import CannedResponse

logger = logging.getLogger(__name__)


class ResponsePoster:
    """Posts rendered canned responses to Jira tickets."""

    def __init__(self, jira_client: JiraClient = None):
        """Initialize response poster.

        Args:
            jira_client: JiraClient instance (creates new one if not provided)
        """
        self.jira_client = jira_client or JiraClient()

    def post_response(
        self,
        ticket_key: str,
        canned_response: CannedResponse,
        issue_reporter: str,
        issue_assignee: str = None,
    ) -> Dict[str, Any]:
        """Post canned response to Jira ticket.

        Args:
            ticket_key: Jira ticket key (e.g., CASSINI-1234)
            canned_response: CannedResponse to post
            issue_reporter: Reporter display name
            issue_assignee: Assignee display name (optional)

        Returns:
            Dictionary with comment_id and posted_at

        Raises:
            Exception: If posting fails
        """
        # Render template
        rendered_response = TemplateRenderer.render(
            template=canned_response.response,
            issue_reporter=issue_reporter,
            issue_assignee=issue_assignee,
        )

        logger.info(
            f"Posting canned response '{canned_response.id}' to {ticket_key}"
        )

        try:
            # Post comment to Jira
            comment = self.jira_client.post_comment(
                issue_key=ticket_key,
                comment_body=rendered_response,
            )

            # Add auto-responded label
            self.jira_client.add_label(ticket_key, "auto-responded")

            comment_id = comment.get("id")
            posted_at = datetime.utcnow()

            logger.info(
                f"Successfully posted response to {ticket_key} (comment_id: {comment_id})"
            )

            return {
                "comment_id": comment_id,
                "posted_at": posted_at,
                "response_id": canned_response.id,
            }

        except Exception as e:
            logger.error(f"Failed to post response to {ticket_key}: {e}")
            raise

    def post_shadow_mode_comment(
        self,
        ticket_key: str,
        canned_response: CannedResponse,
    ) -> None:
        """Post shadow mode notification comment (for testing).

        This is OPTIONAL and only used during shadow mode testing.
        In production shadow mode, no comments are posted at all.

        Args:
            ticket_key: Jira ticket key
            canned_response: Canned response that would have been posted
        """
        shadow_comment = (
            f"_[Shadow Mode] This ticket would have received an automated response: "
            f"**{canned_response.name}**. "
            f"Shadow mode is active - responses are logged but not posted._"
        )

        try:
            self.jira_client.post_comment(
                issue_key=ticket_key,
                comment_body=shadow_comment,
            )

            logger.info(f"Posted shadow mode notification to {ticket_key}")

        except Exception as e:
            logger.warning(
                f"Failed to post shadow mode comment to {ticket_key}: {e}"
            )
            # Don't raise - shadow mode comments are non-critical
