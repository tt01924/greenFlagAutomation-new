"""Prometheus metrics for monitoring and alerting."""
import logging
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

logger = logging.getLogger(__name__)

# Ticket processing metrics
tickets_processed_total = Counter(
    "tickets_processed_total",
    "Total number of tickets processed",
    ["action", "status"],
)

tickets_failed_total = Counter(
    "tickets_failed_total",
    "Total number of tickets that failed processing",
    ["reason"],
)

# Action-specific counters
tickets_auto_responded_total = Counter(
    "tickets_auto_responded_total",
    "Total number of tickets that received automated responses",
)

tickets_escalated_total = Counter(
    "tickets_escalated_total",
    "Total number of tickets escalated to human",
    ["reason"],
)

tickets_shadow_mode_total = Counter(
    "tickets_shadow_mode_total",
    "Total number of tickets processed in shadow mode",
)

tickets_retracted_total = Counter(
    "tickets_retracted_total",
    "Total number of automated responses that were retracted",
)

# System state gauges
automation_enabled = Gauge(
    "automation_enabled",
    "Whether automation is currently enabled (1) or disabled (0)",
)

shadow_mode_active = Gauge(
    "shadow_mode_active",
    "Whether shadow mode is currently active (1) or inactive (0)",
)

shadow_mode_remaining_hours = Gauge(
    "shadow_mode_remaining_hours",
    "Hours remaining in shadow mode window",
)

# Processing duration
ticket_processing_duration_seconds = Histogram(
    "ticket_processing_duration_seconds",
    "Time spent processing each ticket",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# Classification confidence
classification_confidence_score = Histogram(
    "classification_confidence_score",
    "Confidence score of LLM classification",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)

# Escalation queue depth
escalation_queue_depth = Gauge(
    "escalation_queue_depth",
    "Number of unresolved escalations",
)

escalation_overdue_count = Gauge(
    "escalation_overdue_count",
    "Number of escalations older than 4 hours",
)

# External service health
external_service_request_total = Counter(
    "external_service_request_total",
    "Total requests to external services",
    ["service", "status"],
)

external_service_request_duration_seconds = Histogram(
    "external_service_request_duration_seconds",
    "Duration of requests to external services",
    ["service"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)


class MetricsService:
    """Service for recording application metrics."""

    @staticmethod
    def record_ticket_processed(action: str, status: str = "success") -> None:
        """Record a ticket being processed.

        Args:
            action: Action taken (auto_respond, escalate, shadow)
            status: Processing status (success, failure)
        """
        tickets_processed_total.labels(action=action, status=status).inc()

        if action == "auto_respond":
            tickets_auto_responded_total.inc()
        elif action == "escalate":
            tickets_escalated_total.labels(reason="unknown").inc()
        elif action == "shadow":
            tickets_shadow_mode_total.inc()

    @staticmethod
    def record_ticket_failed(reason: str) -> None:
        """Record a ticket processing failure.

        Args:
            reason: Failure reason (classification_error, jira_error, etc.)
        """
        tickets_failed_total.labels(reason=reason).inc()

    @staticmethod
    def record_escalation(reason: str) -> None:
        """Record a ticket escalation.

        Args:
            reason: Escalation reason
        """
        tickets_escalated_total.labels(reason=reason).inc()

    @staticmethod
    def record_retraction() -> None:
        """Record an automated response being retracted."""
        tickets_retracted_total.inc()

    @staticmethod
    def record_processing_duration(duration_seconds: float) -> None:
        """Record ticket processing duration.

        Args:
            duration_seconds: Processing duration in seconds
        """
        ticket_processing_duration_seconds.observe(duration_seconds)

    @staticmethod
    def record_classification_confidence(confidence: float) -> None:
        """Record classification confidence score.

        Args:
            confidence: Confidence score (0-1)
        """
        classification_confidence_score.observe(confidence)

    @staticmethod
    def update_automation_state(enabled: bool) -> None:
        """Update automation enabled gauge.

        Args:
            enabled: Whether automation is enabled
        """
        automation_enabled.set(1 if enabled else 0)

    @staticmethod
    def update_shadow_mode_state(active: bool, remaining_hours: float = 0) -> None:
        """Update shadow mode gauges.

        Args:
            active: Whether shadow mode is active
            remaining_hours: Hours remaining in shadow mode
        """
        shadow_mode_active.set(1 if active else 0)
        shadow_mode_remaining_hours.set(remaining_hours if active else 0)

    @staticmethod
    def update_escalation_metrics(queue_depth: int, overdue_count: int) -> None:
        """Update escalation queue metrics.

        Args:
            queue_depth: Number of unresolved escalations
            overdue_count: Number of overdue escalations (>4 hours)
        """
        escalation_queue_depth.set(queue_depth)
        escalation_overdue_count.set(overdue_count)

    @staticmethod
    def record_external_service_request(
        service: str, status: str, duration_seconds: float
    ) -> None:
        """Record an external service request.

        Args:
            service: Service name (jira, slack, anthropic, openai)
            status: Request status (success, failure, timeout)
            duration_seconds: Request duration
        """
        external_service_request_total.labels(service=service, status=status).inc()
        external_service_request_duration_seconds.labels(service=service).observe(
            duration_seconds
        )

    @staticmethod
    def get_metrics() -> Response:
        """Get Prometheus metrics in text format.

        Returns:
            FastAPI Response with metrics
        """
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Initialize default values
automation_enabled.set(1)  # Default: enabled
shadow_mode_active.set(0)  # Default: not active
