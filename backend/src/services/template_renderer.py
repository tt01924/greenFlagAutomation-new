"""Template renderer for substituting variables in canned responses."""
import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Renders canned response templates with variable substitution."""

    # Supported template variables
    SUPPORTED_VARIABLES = [
        "issueReporter",
        "issueAssignee",
    ]

    @staticmethod
    def render(
        template: str,
        issue_reporter: str,
        issue_assignee: str = None,
    ) -> str:
        """Render template with variable substitution.

        Args:
            template: Template string with {{variable}} placeholders
            issue_reporter: Reporter display name or email
            issue_assignee: Assignee display name or email (optional)

        Returns:
            Rendered template string
        """
        rendered = template

        # Substitute issueReporter
        rendered = rendered.replace("{{issueReporter}}", issue_reporter)

        # Substitute issueAssignee
        if issue_assignee:
            rendered = rendered.replace("{{issueAssignee}}", issue_assignee)
        else:
            # Default value if no assignee
            rendered = rendered.replace("{{issueAssignee}}", "the assignee")

        # Check for any remaining unsubstituted variables
        remaining_vars = re.findall(r"\{\{(\w+)\}\}", rendered)
        if remaining_vars:
            logger.warning(
                f"Template contains unrecognized variables: {remaining_vars}"
            )

        logger.debug(f"Rendered template with reporter={issue_reporter}")

        return rendered

    @staticmethod
    def extract_variables_from_issue(issue_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract template variables from issue data.

        Args:
            issue_data: Jira issue data from webhook

        Returns:
            Dictionary of template variables
        """
        fields = issue_data.get("fields", {})

        # Get reporter info
        reporter = fields.get("reporter", {})
        issue_reporter = (
            reporter.get("displayName")
            or reporter.get("emailAddress")
            or "the reporter"
        )

        # Get assignee info (may be None)
        assignee = fields.get("assignee")
        issue_assignee = None
        if assignee:
            issue_assignee = (
                assignee.get("displayName")
                or assignee.get("emailAddress")
                or None
            )

        return {
            "issue_reporter": issue_reporter,
            "issue_assignee": issue_assignee,
        }

    @staticmethod
    def validate_template(template: str) -> bool:
        """Validate template for correct variable syntax.

        Args:
            template: Template string to validate

        Returns:
            True if template is valid
        """
        # Find all variables in template
        variables = re.findall(r"\{\{(\w+)\}\}", template)

        # Check if all variables are supported
        unsupported = [v for v in variables if v not in TemplateRenderer.SUPPORTED_VARIABLES]

        if unsupported:
            logger.error(f"Template contains unsupported variables: {unsupported}")
            return False

        # Check for malformed variables (e.g., single braces, missing closing)
        if re.search(r"\{[^{]|\}[^}]", template):
            logger.error("Template contains malformed variable syntax")
            return False

        return True
