"""Test fixtures for Jira webhook payloads and responses."""
from datetime import datetime
from typing import Dict, Any


def get_mock_jira_webhook_payload(
    ticket_key: str = "CASSINI-1234",
    ticket_id: str = "12345678",
    summary: str = "Need IAM permissions for my project",
    description: str = "Can someone help me get IAM permissions? I need access to S3 and DynamoDB.",
    reporter_name: str = "John Doe",
    reporter_email: str = "john.doe@skyscanner.net",
) -> Dict[str, Any]:
    """Create mock Jira webhook payload.

    Args:
        ticket_key: Jira ticket key
        ticket_id: Jira ticket ID
        summary: Ticket summary
        description: Ticket description
        reporter_name: Reporter display name
        reporter_email: Reporter email

    Returns:
        Mock webhook payload
    """
    return {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "webhookEvent": "jira:issue_created",
        "issue_event_type_name": "issue_created",
        "user": {
            "accountId": "5b10ac8d82e05b22cc7d4ef5",
            "displayName": reporter_name,
            "emailAddress": reporter_email,
            "active": True,
            "timeZone": "Europe/London",
        },
        "issue": {
            "id": ticket_id,
            "key": ticket_key,
            "self": f"https://skyscanner.atlassian.net/rest/api/2/issue/{ticket_id}",
            "fields": {
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task", "subtask": False},
                "project": {"key": "CASSINI", "name": "Cassini Squad"},
                "reporter": {
                    "accountId": "5b10ac8d82e05b22cc7d4ef5",
                    "displayName": reporter_name,
                    "emailAddress": reporter_email,
                },
                "assignee": None,
                "priority": {"name": "Medium"},
                "status": {"name": "Open"},
                "labels": ["Green-Flag"],
                "created": datetime.now().isoformat() + "+0000",
                "updated": datetime.now().isoformat() + "+0000",
                "comment": {"comments": [], "total": 0},
            },
        },
    }


def get_mock_jira_comment_response(
    comment_id: str = "67890",
    comment_body: str = "Test response",
) -> Dict[str, Any]:
    """Create mock Jira comment response.

    Args:
        comment_id: Comment ID
        comment_body: Comment text

    Returns:
        Mock comment response
    """
    return {
        "id": comment_id,
        "body": comment_body,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "author": {
            "accountId": "bot-account-id",
            "displayName": "Green Flag Bot",
            "emailAddress": "green-flag-bot@skyscanner.net",
        },
    }
