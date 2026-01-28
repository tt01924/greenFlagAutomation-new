"""Slack client wrapper for sending messages and notifications."""

import logging
from typing import Dict, Any, List, Optional
from slack_bolt import App
from slack_sdk.errors import SlackApiError

from src.config.settings import settings

logger = logging.getLogger(__name__)


class SlackClient:
    """Wrapper for Slack API operations."""

    def __init__(self) -> None:
        """Initialize Slack client."""
        self.app = App(
            token=settings.SLACK_BOT_TOKEN,
            signing_secret=settings.SLACK_SIGNING_SECRET,
        )
        self.client = self.app.client

    def get_user_by_email(self, email: str) -> Optional[str]:
        """Get Slack user ID by email address.

        Args:
            email: User email address

        Returns:
            Slack user ID or None if not found
        """
        try:
            response = self.client.users_lookupByEmail(email=email)
            user_id = response["user"]["id"]
            logger.info(f"Found Slack user {user_id} for email {email}")
            return user_id
        except SlackApiError as e:
            if e.response["error"] == "users_not_found":
                logger.warning(f"No Slack user found for email {email}")
                return None
            logger.error(f"Failed to lookup user by email {email}: {e}")
            raise

    def send_escalation_message(
        self,
        channel_or_user_id: str,
        ticket_key: str,
        ticket_title: str,
        escalation_reason: str,
        confidence_scores: Dict[str, Any],
        jira_url: str,
        dashboard_url: str,
        reporter: str,
        created_at: str,
        description_snippet: str = "",
    ) -> Dict[str, Any]:
        """Send escalation message to Slack channel or user.

        Args:
            channel_or_user_id: Slack channel ID or user ID
            ticket_key: Jira ticket key
            ticket_title: Ticket summary
            escalation_reason: Reason for escalation
            confidence_scores: Classification confidence scores
            jira_url: URL to Jira ticket
            dashboard_url: URL to dashboard ticket view
            reporter: Ticket reporter name
            created_at: Ticket creation timestamp
            description_snippet: Brief description excerpt

        Returns:
            Slack API response

        Raises:
            SlackApiError: If message sending fails
        """
        # Format top matches for display
        top_matches = self._format_top_matches(confidence_scores)

        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Green Flag Ticket Needs Review",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Ticket:*\n<{jira_url}|{ticket_key}>",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Reason:*\n{escalation_reason}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Title:* {ticket_title}",
                },
            },
        ]

        # Add description snippet if provided
        if description_snippet:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{description_snippet[:200]}...",
                    },
                }
            )

        # Add top matches
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top Matches:*\n{top_matches}",
                },
            }
        )

        # Add action buttons
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Dashboard",
                        },
                        "url": dashboard_url,
                        "action_id": "view_dashboard",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Jira",
                        },
                        "url": jira_url,
                        "action_id": "view_jira",
                        "style": "primary",
                    },
                ],
            }
        )

        # Add context footer
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Reporter: {reporter} | Created: {created_at}",
                    }
                ],
            }
        )

        try:
            response = self.client.chat_postMessage(
                channel=channel_or_user_id,
                text=f"🚨 Green Flag Ticket Needs Review: {ticket_key}",
                blocks=blocks,
                unfurl_links=False,
                unfurl_media=False,
            )
            logger.info(f"Sent escalation message for {ticket_key} to {channel_or_user_id}")
            return response
        except SlackApiError as e:
            logger.error(f"Failed to send Slack message: {e}")
            raise

    def send_daily_summary(
        self,
        channel_id: str,
        date: str,
        total_tickets: int,
        auto_responded: int,
        escalated: int,
        retracted: int,
        top_categories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send daily summary message.

        Args:
            channel_id: Slack channel ID
            date: Date string (e.g., "2026-01-28")
            total_tickets: Total tickets processed
            auto_responded: Number of auto-responded tickets
            escalated: Number of escalated tickets
            retracted: Number of retracted responses
            top_categories: List of top canned response categories

        Returns:
            Slack API response
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Green Flag Daily Summary - {date}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Total Tickets:*\n{total_tickets}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Auto-Responded:*\n{auto_responded} ({auto_responded/total_tickets*100:.1f}%)",
                    },
                    {"type": "mrkdwn", "text": f"*Escalated:*\n{escalated}"},
                    {"type": "mrkdwn", "text": f"*Retracted:*\n{retracted}"},
                ],
            },
        ]

        if top_categories:
            category_text = "\n".join(
                [
                    f"{i+1}. {cat['name']}: {cat['count']}"
                    for i, cat in enumerate(top_categories[:5])
                ]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top Categories:*\n{category_text}",
                    },
                }
            )

        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Dashboard"},
                        "url": f"{settings.DASHBOARD_URL}/reports",
                        "action_id": "view_dashboard",
                    }
                ],
            }
        )

        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=f"📊 Green Flag Daily Summary - {date}",
                blocks=blocks,
            )
            logger.info(f"Sent daily summary for {date} to {channel_id}")
            return response
        except SlackApiError as e:
            logger.error(f"Failed to send daily summary: {e}")
            raise

    def _format_top_matches(self, confidence_scores: Dict[str, Any]) -> str:
        """Format confidence scores for display.

        Args:
            confidence_scores: Dictionary of response_id -> {confidence, reasoning}

        Returns:
            Formatted string
        """
        # Sort by confidence descending
        sorted_scores = sorted(
            confidence_scores.items(),
            key=lambda x: x[1].get("confidence", 0),
            reverse=True,
        )

        # Take top 3
        top_3 = sorted_scores[:3]

        lines = []
        for i, (response_id, data) in enumerate(top_3, 1):
            confidence = data.get("confidence", 0)
            reasoning = data.get("reasoning", "No reasoning provided")
            lines.append(f"{i}. `{response_id}` ({confidence*100:.0f}%) - {reasoning}")

        return "\n".join(lines)
