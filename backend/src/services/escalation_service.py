"""Escalation service for handling ticket escalations with retry logic."""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from src.services.slack_client import SlackClient
from src.services.queue import TicketQueue
from src.config.settings import settings

logger = logging.getLogger(__name__)


class EscalationService:
    """Handles ticket escalations to Green Flag holder via Slack with retry logic."""

    ESCALATION_RETRY_QUEUE = "green_flag_escalations_retry"
    MAX_RETRIES = 3

    def __init__(self, slack_client: SlackClient = None):
        """Initialize escalation service.

        Args:
            slack_client: SlackClient instance (creates new one if not provided)
        """
        self.slack_client = slack_client or SlackClient()

    def escalate_ticket(
        self,
        ticket_key: str,
        ticket_title: str,
        escalation_reason: str,
        confidence_scores: Dict[str, Any],
        jira_url: str,
        dashboard_url: str,
        reporter: str,
        created_at: str,
        description_snippet: str = "",
        channel_or_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Escalate ticket to Green Flag holder via Slack.

        Args:
            ticket_key: Jira ticket key
            ticket_title: Ticket summary
            escalation_reason: Reason for escalation
            confidence_scores: Classification confidence scores
            jira_url: URL to Jira ticket
            dashboard_url: URL to dashboard ticket view
            reporter: Ticket reporter name
            created_at: Ticket creation timestamp
            description_snippet: Brief description excerpt
            channel_or_user_id: Slack channel or user ID (uses default if None)

        Returns:
            Result dictionary with status and message_id or error

        Raises:
            Exception: If escalation fails after retries
        """
        # Use configured channel if not specified
        if not channel_or_user_id:
            channel_or_user_id = self._get_default_escalation_channel()

        try:
            response = self.slack_client.send_escalation_message(
                channel_or_user_id=channel_or_user_id,
                ticket_key=ticket_key,
                ticket_title=ticket_title,
                escalation_reason=escalation_reason,
                confidence_scores=confidence_scores,
                jira_url=jira_url,
                dashboard_url=dashboard_url,
                reporter=reporter,
                created_at=created_at,
                description_snippet=description_snippet,
            )

            message_ts = response.get("ts")
            logger.info(
                f"Successfully escalated {ticket_key} to {channel_or_user_id} "
                f"(message_ts: {message_ts})"
            )

            return {
                "status": "sent",
                "channel": channel_or_user_id,
                "message_ts": message_ts,
            }

        except Exception as e:
            logger.error(f"Failed to escalate {ticket_key} to Slack: {e}")

            # Queue for retry
            self._queue_for_retry(
                ticket_key=ticket_key,
                ticket_title=ticket_title,
                escalation_reason=escalation_reason,
                confidence_scores=confidence_scores,
                jira_url=jira_url,
                dashboard_url=dashboard_url,
                reporter=reporter,
                created_at=created_at,
                description_snippet=description_snippet,
                channel_or_user_id=channel_or_user_id,
                retry_count=0,
            )

            return {
                "status": "queued_for_retry",
                "error": str(e),
            }

    def _queue_for_retry(
        self,
        ticket_key: str,
        ticket_title: str,
        escalation_reason: str,
        confidence_scores: Dict[str, Any],
        jira_url: str,
        dashboard_url: str,
        reporter: str,
        created_at: str,
        description_snippet: str,
        channel_or_user_id: str,
        retry_count: int,
    ) -> None:
        """Queue escalation for retry.

        Args:
            ticket_key: Jira ticket key
            ticket_title: Ticket summary
            escalation_reason: Reason for escalation
            confidence_scores: Classification confidence scores
            jira_url: URL to Jira ticket
            dashboard_url: URL to dashboard ticket view
            reporter: Ticket reporter name
            created_at: Ticket creation timestamp
            description_snippet: Brief description excerpt
            channel_or_user_id: Slack channel or user ID
            retry_count: Current retry attempt count
        """
        if retry_count >= self.MAX_RETRIES:
            logger.error(
                f"Max retries ({self.MAX_RETRIES}) reached for escalation of {ticket_key}"
            )
            return

        retry_data = {
            "ticket_key": ticket_key,
            "ticket_title": ticket_title,
            "escalation_reason": escalation_reason,
            "confidence_scores": confidence_scores,
            "jira_url": jira_url,
            "dashboard_url": dashboard_url,
            "reporter": reporter,
            "created_at": created_at,
            "description_snippet": description_snippet,
            "channel_or_user_id": channel_or_user_id,
            "retry_count": retry_count + 1,
            "queued_at": datetime.utcnow().isoformat(),
        }

        try:
            queue = TicketQueue()
            # Use Redis to queue retry (could use a separate retry queue)
            queue.redis_client.lpush(
                self.ESCALATION_RETRY_QUEUE,
                json.dumps(retry_data),
            )
            logger.info(
                f"Queued {ticket_key} for escalation retry "
                f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
            )
        except Exception as e:
            logger.error(f"Failed to queue escalation retry for {ticket_key}: {e}")

    def process_retry_queue(self, batch_size: int = 10) -> int:
        """Process escalation retry queue.

        Args:
            batch_size: Number of retries to process

        Returns:
            Number of escalations successfully sent
        """
        queue = TicketQueue()
        sent_count = 0

        for _ in range(batch_size):
            try:
                # Pop from retry queue
                result = queue.redis_client.rpop(self.ESCALATION_RETRY_QUEUE)

                if not result:
                    # Queue empty
                    break

                retry_data = json.loads(result)

                # Attempt to send escalation again
                try:
                    response = self.slack_client.send_escalation_message(
                        channel_or_user_id=retry_data["channel_or_user_id"],
                        ticket_key=retry_data["ticket_key"],
                        ticket_title=retry_data["ticket_title"],
                        escalation_reason=retry_data["escalation_reason"],
                        confidence_scores=retry_data["confidence_scores"],
                        jira_url=retry_data["jira_url"],
                        dashboard_url=retry_data["dashboard_url"],
                        reporter=retry_data["reporter"],
                        created_at=retry_data["created_at"],
                        description_snippet=retry_data["description_snippet"],
                    )

                    logger.info(
                        f"Retry successful for {retry_data['ticket_key']} "
                        f"(attempt {retry_data['retry_count']})"
                    )
                    sent_count += 1

                except Exception as e:
                    logger.error(
                        f"Retry failed for {retry_data['ticket_key']}: {e}"
                    )

                    # Re-queue if not max retries
                    if retry_data["retry_count"] < self.MAX_RETRIES:
                        self._queue_for_retry(
                            ticket_key=retry_data["ticket_key"],
                            ticket_title=retry_data["ticket_title"],
                            escalation_reason=retry_data["escalation_reason"],
                            confidence_scores=retry_data["confidence_scores"],
                            jira_url=retry_data["jira_url"],
                            dashboard_url=retry_data["dashboard_url"],
                            reporter=retry_data["reporter"],
                            created_at=retry_data["created_at"],
                            description_snippet=retry_data["description_snippet"],
                            channel_or_user_id=retry_data["channel_or_user_id"],
                            retry_count=retry_data["retry_count"],
                        )

            except Exception as e:
                logger.error(f"Error processing retry queue: {e}")
                continue

        if sent_count > 0:
            logger.info(f"Processed escalation retries: {sent_count} sent")

        return sent_count

    def _get_default_escalation_channel(self) -> str:
        """Get default escalation channel/user.

        Returns:
            Slack channel ID or user ID

        TODO: Implement Green Flag holder lookup from database or config
        For now, returns a default channel
        """
        # Default to a configured channel
        # In production, this should look up the current Green Flag holder
        return "#cassini-squad"

    def get_retry_queue_length(self) -> int:
        """Get current retry queue length.

        Returns:
            Number of escalations waiting for retry
        """
        try:
            queue = TicketQueue()
            return queue.redis_client.llen(self.ESCALATION_RETRY_QUEUE)
        except Exception as e:
            logger.error(f"Failed to get retry queue length: {e}")
            return 0
