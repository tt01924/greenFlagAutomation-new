"""Ticket processor worker - consumes tickets from Redis queue and processes them."""

import logging
import signal
import sys
import time

from src.models.base import SessionLocal
from src.services.queue import TicketQueue
from src.services.processor import TicketProcessor
from src.config.logging import setup_logging

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global shutdown_requested
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown_requested = True


def process_single_ticket(queue: TicketQueue) -> bool:
    """Process a single ticket from the queue.

    Args:
        queue: TicketQueue instance

    Returns:
        True if ticket was processed, False if queue was empty
    """
    # Dequeue ticket (blocking with timeout)
    job_data = queue.dequeue_ticket(timeout=5)

    if not job_data:
        return False

    ticket_id = job_data["ticket_id"]
    ticket_key = job_data["ticket_key"]
    webhook_payload = job_data["webhook_payload"]

    logger.info(f"Processing ticket {ticket_key} (ID: {ticket_id})")

    # Create database session
    db = SessionLocal()

    try:
        # Acquire processing lock to prevent duplicate processing
        if not queue.set_processing_lock(ticket_id, worker_id="worker-1"):
            logger.warning(f"Ticket {ticket_id} already being processed, skipping")
            return True

        # Process ticket
        processor = TicketProcessor(db)
        result = processor.process_ticket(webhook_payload)

        logger.info(f"Processed {ticket_key}: status={result.get('status')}")

        # Release processing lock
        queue.release_processing_lock(ticket_id)

        return True

    except Exception as e:
        logger.error(f"Failed to process ticket {ticket_key}: {e}", exc_info=True)

        # Release lock even on failure
        try:
            queue.release_processing_lock(ticket_id)
        except Exception:
            pass

        # Ticket failed but we continue processing other tickets
        return True

    finally:
        db.close()


def run_worker(
    worker_id: str = "worker-1",
    batch_size: int = 10,
    idle_sleep: int = 10,
) -> None:
    """Run ticket processor worker.

    Args:
        worker_id: Unique worker identifier
        batch_size: Number of tickets to process before checking shutdown
        idle_sleep: Seconds to sleep when queue is empty
    """
    setup_logging()

    logger.info(f"Starting ticket processor worker: {worker_id}")
    logger.info(f"Batch size: {batch_size}, idle sleep: {idle_sleep}s")

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create queue instance
    queue = TicketQueue()

    # Check queue health
    if not queue.health_check():
        logger.error("Redis health check failed, exiting")
        sys.exit(1)

    logger.info("Worker ready to process tickets")

    tickets_processed = 0
    consecutive_empty = 0

    while not shutdown_requested:
        try:
            # Process batch of tickets
            batch_count = 0
            for _ in range(batch_size):
                if shutdown_requested:
                    break

                processed = process_single_ticket(queue)

                if processed:
                    batch_count += 1
                    tickets_processed += 1
                    consecutive_empty = 0
                else:
                    # Queue was empty
                    consecutive_empty += 1
                    break

            # Log progress
            if batch_count > 0:
                queue_length = queue.get_queue_length()
                logger.info(
                    f"Processed {batch_count} tickets in batch "
                    f"(total: {tickets_processed}, queue: {queue_length})"
                )

            # If queue is empty, sleep before next check
            if batch_count == 0:
                if consecutive_empty == 1:
                    logger.debug(f"Queue empty, sleeping {idle_sleep}s")
                time.sleep(idle_sleep)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            break

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            # Sleep and continue on unexpected errors
            time.sleep(5)

    logger.info(f"Worker shutting down. Processed {tickets_processed} tickets total.")


def main():
    """Main entry point for worker.

    Starts the ticket processor worker with default configuration.
    Worker runs continuously, consuming tickets from Redis queue and
    processing them through the full classification and response workflow.

    This is typically run as a long-running process (e.g., via systemd).
    """
    run_worker(
        worker_id="worker-1",
        batch_size=10,
        idle_sleep=10,
    )


if __name__ == "__main__":
    main()
