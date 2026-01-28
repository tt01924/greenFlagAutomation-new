"""LLM prompt templates for ticket classification."""

CLASSIFICATION_SYSTEM_PROMPT = """You are a ticket classification assistant for Skyscanner's Cassini squad. Your job is to match incoming Jira tickets to pre-approved canned responses.

You will be given:
1. A Jira ticket (summary + description)
2. A list of canned response categories with keywords

Your task is to:
1. Analyze the ticket content semantically (not just keyword matching)
2. Assign a confidence score (0.0 to 1.0) for EACH canned response
3. Provide brief reasoning for each score

Guidelines:
- Focus on the ticket's intent, not just keywords
- Consider context and tone
- Be conservative with high confidence scores (>0.80)
- A ticket can have multiple potential matches
- If truly ambiguous, all scores should be moderate (0.5-0.7 range)

Constitutional requirements:
- NEVER generate a custom response
- ONLY classify against provided categories
- If uncertain, err on the side of escalation (lower scores)
"""

CLASSIFICATION_USER_PROMPT_TEMPLATE = """Ticket to classify:
**Ticket Key**: {ticket_key}
**Summary**: {summary}
**Description**: {description}
**Reporter**: {reporter}

Available canned responses:
{canned_responses_list}

Provide your classification as a JSON object with this structure:
{{
  "classifications": [
    {{
      "response_id": "iam-request",
      "confidence": 0.85,
      "reasoning": "Clear mention of IAM permissions needed for AWS account"
    }},
    ...
  ],
  "overall_assessment": "Brief overall assessment of the ticket",
  "flags": {{
    "sensitive_data_detected": false,
    "multiple_questions": false,
    "urgent_tone": false
  }}
}}

Important:
- Include ALL canned responses with their scores (even low ones)
- Scores must sum to approximately 1.0
- Set sensitive_data_detected=true if ticket contains passwords, tokens, keys, or PII
- Set urgent_tone=true if ticket uses language like "URGENT", "ASAP", "CRITICAL"
"""

ESCALATION_SLACK_MESSAGE_TEMPLATE = """🚨 **Green Flag Ticket Needs Review**

**Ticket**: [{ticket_key}]({jira_url})
**Reporter**: {reporter}
**Created**: {created_at}

**Reason for Escalation**: {escalation_reason}

**Ticket Summary**: {summary}

{description_snippet}

**Top Classification Matches**:
{top_matches}

**Actions**:
- [View Full Ticket in Jira]({jira_url})
- [View in Dashboard]({dashboard_url})

Please review and respond manually to this ticket.
"""


def format_canned_responses_for_prompt(canned_responses: list) -> str:
    """Format canned responses for LLM prompt.

    Args:
        canned_responses: List of CannedResponse objects

    Returns:
        Formatted string for prompt
    """
    formatted = []
    for i, response in enumerate(canned_responses, 1):
        formatted.append(
            f"{i}. **{response.id}** ({response.name})\n"
            f"   Category: {response.category}\n"
            f"   Keywords: {', '.join(response.keywords)}\n"
            f"   Response preview: {response.response[:100]}...\n"
        )
    return "\n".join(formatted)


def build_classification_prompt(
    ticket_key: str,
    summary: str,
    description: str,
    reporter: str,
    canned_responses: list,
) -> dict:
    """Build classification prompt for LLM.

    Args:
        ticket_key: Jira ticket key (e.g., CASSINI-1234)
        summary: Ticket summary/title
        description: Ticket description
        reporter: Reporter display name
        canned_responses: List of CannedResponse objects

    Returns:
        Dictionary with 'system' and 'user' prompts
    """
    canned_responses_list = format_canned_responses_for_prompt(canned_responses)

    user_prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
        ticket_key=ticket_key,
        summary=summary,
        description=description or "(No description provided)",
        reporter=reporter,
        canned_responses_list=canned_responses_list,
    )

    return {
        "system": CLASSIFICATION_SYSTEM_PROMPT,
        "user": user_prompt,
    }
