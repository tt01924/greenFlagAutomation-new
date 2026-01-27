# Green Flag Automation Constitution
**Cassini Squad - Skyscanner Production Platform**

## Purpose

This system automates responses to Green Flag support tickets by matching customer requests to pre-approved canned responses. It exists to reduce manual triage burden on Cassini squad members while maintaining high-quality customer support.

## System Authority

### The system MUST:
- Only send responses that exactly match pre-approved canned response templates
- Escalate any ticket to a human if confidence in the match is not high
- Escalate immediately if no canned response applies to the request
- Log every ticket processed and every decision made with full context
- Preserve the complete original ticket content in all logs and escalations
- Notify the Green Flag holder immediately when escalating a ticket
- Include its confidence reasoning when escalating unclear tickets

### The system MUST NOT:
- Compose custom or modified responses beyond the approved canned response set
- Send any response without explicit confirmation the ticket matches a known category
- Make judgment calls on ambiguous requests - escalate instead
- Process tickets that contain sensitive data (credentials, tokens, PII) - escalate immediately
- Operate if any integration (Slack, Jira) is unavailable - fail safe and alert
- Auto-respond to follow-up comments on tickets it has already handled
- Learn or adapt its matching behavior without human approval of new patterns

### The system MUST escalate when:
- The ticket request does not clearly match any canned response category
- Multiple canned responses could apply (ambiguous intent)
- The ticket tone suggests urgency, frustration, or escalation
- The ticket contains questions in addition to the main request
- Any system component (classifier, integration) reports an error or uncertainty
- The ticket is a reply to a previous automated response

## Safety & Governance

### Auditability
- Every automated response MUST be logged with: ticket ID, timestamp, matched canned response, confidence score, and full ticket text
- Audit logs MUST be retained for minimum 90 days
- The Green Flag holder MUST receive a daily summary of all automated actions

### Reversibility
- Automated responses MUST be clearly labeled as automated (e.g., signature or tag)
- Customers MUST have clear instructions on how to reach a human if the response was inadequate
- The system MUST provide a one-click "undo" mechanism for the Green Flag holder to retract automated responses within 5 minutes of sending

### Operational Safety
- The system MUST have a manual kill switch accessible to any Cassini squad member
- Any change to the canned response set MUST be human-approved before the system uses it
- The system MUST run in shadow mode (log decisions but don't send) for 48 hours after any configuration change

## Human Oversight

### A human MUST review:
- All escalated tickets within 4 business hours
- Weekly accuracy reports showing automated vs escalated ratios
- Any customer complaints about automated responses within 24 hours
- System behavior after every update to canned responses or matching logic

## Non-Functional Requirements

**Performance**: The system MUST process tickets within 5 minutes of receipt
**Availability**: The system MUST NOT become a single point of failure - manual workflow must remain functional if automation is down
**Accuracy**: False positive rate (wrong canned response) MUST remain below 2%
**Transparency**: Every customer response MUST clearly indicate it was automated
**Data Privacy**: The system MUST NOT store ticket content beyond audit retention period

## Governance

This constitution defines the behavioral boundaries of the Green Flag automation system. All implementation decisions, feature additions, and operational changes must comply with these requirements.

The constitution may only be amended with approval from the Cassini squad lead and documentation of the rationale.

**Version**: 1.0.0 | **Ratified**: 2026-01-27 | **Last Amended**: 2026-01-27
