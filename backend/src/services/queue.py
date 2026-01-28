"""Redis queue wrapper for async ticket processing."""

import json
import logging
from typing import Dict, Any, Optional
import redis
from redis import Redis

from src.config.settings import settings

logger = logging.getLogger(__name__)


class TicketQueue:
    """Redis-based queue for ticket processing."""

    QUEUE_NAME = "green_flag_tickets"

    def __init__(self) -> None:
        """Initialize Redis client."""
        self.redis_client: Redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

    def enqueue_ticket(
        self,
        ticket_id: str,
        ticket_key: str,
        webhook_payload: Dict[str, Any],
        priority: str = "normal",
    ) -> bool:
        """Add ticket to processing queue.

        Args:
            ticket_id: Jira ticket ID
            ticket_key: Jira ticket key (e.g., CASSINI-1234)
            webhook_payload: Full webhook payload
            priority: Priority level ('high', 'normal', 'low')

        Returns:
            True if enqueued successfully

        Raises:
            redis.RedisError: If Redis operation fails
        """
        job_data = {
            "ticket_id": ticket_id,
            "ticket_key": ticket_key,
            "webhook_payload": webhook_payload,
            "priority": priority,
        }

        try:
            # Use LPUSH for FIFO queue (worker uses BRPOP)
            self.redis_client.lpush(self.QUEUE_NAME, json.dumps(job_data))
            logger.info(f"Enqueued ticket {ticket_key} (priority: {priority})")
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to enqueue ticket {ticket_key}: {e}")
            raise

    def dequeue_ticket(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Dequeue next ticket for processing (blocking).

        Args:
            timeout: Blocking timeout in seconds

        Returns:
            Job data dictionary or None if timeout

        Raises:
            redis.RedisError: If Redis operation fails
        """
        try:
            # BRPOP blocks until item available or timeout
            result = self.redis_client.brpop(self.QUEUE_NAME, timeout=timeout)

            if result is None:
                return None

            # result is tuple: (queue_name, value)
            _, job_json = result
            job_data = json.loads(job_json)

            logger.info(f"Dequeued ticket {job_data['ticket_key']}")
            return job_data

        except redis.RedisError as e:
            logger.error(f"Failed to dequeue ticket: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse job data: {e}")
            return None

    def get_queue_length(self) -> int:
        """Get current queue length.

        Returns:
            Number of tickets in queue
        """
        try:
            return self.redis_client.llen(self.QUEUE_NAME)
        except redis.RedisError as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0

    def clear_queue(self) -> int:
        """Clear all items from queue (use with caution).

        Returns:
            Number of items removed
        """
        try:
            count = self.redis_client.delete(self.QUEUE_NAME)
            logger.warning(f"Cleared queue, removed {count} items")
            return count
        except redis.RedisError as e:
            logger.error(f"Failed to clear queue: {e}")
            return 0

    def health_check(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            True if Redis is responding
        """
        try:
            self.redis_client.ping()
            return True
        except redis.RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def set_processing_lock(self, ticket_id: str, worker_id: str, ttl: int = 300) -> bool:
        """Set a processing lock to prevent duplicate processing.

        Args:
            ticket_id: Ticket ID
            worker_id: Worker identifier
            ttl: Lock TTL in seconds (default 5 minutes)

        Returns:
            True if lock acquired, False if already locked
        """
        lock_key = f"processing_lock:{ticket_id}"
        try:
            # NX = only set if not exists, EX = expiry in seconds
            result = self.redis_client.set(lock_key, worker_id, nx=True, ex=ttl)
            if result:
                logger.debug(f"Acquired processing lock for {ticket_id}")
            else:
                logger.warning(f"Ticket {ticket_id} already being processed")
            return bool(result)
        except redis.RedisError as e:
            logger.error(f"Failed to set processing lock: {e}")
            return False

    def release_processing_lock(self, ticket_id: str) -> bool:
        """Release processing lock.

        Args:
            ticket_id: Ticket ID

        Returns:
            True if lock released
        """
        lock_key = f"processing_lock:{ticket_id}"
        try:
            result = self.redis_client.delete(lock_key)
            logger.debug(f"Released processing lock for {ticket_id}")
            return bool(result)
        except redis.RedisError as e:
            logger.error(f"Failed to release processing lock: {e}")
            return False
