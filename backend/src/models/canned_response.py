"""CannedResponse model - loaded from YAML configuration."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import yaml


@dataclass
class CannedResponse:
    """Pre-approved response template with metadata for classification."""

    id: str
    name: str
    category: str
    response: str
    keywords: List[str]
    active: bool = True

    def render(self, issue_reporter: str, issue_assignee: Optional[str] = None) -> str:
        """Render response template with variables substituted.

        Args:
            issue_reporter: Display name of ticket reporter
            issue_assignee: Display name of ticket assignee (optional)

        Returns:
            Rendered response text
        """
        rendered = self.response
        rendered = rendered.replace("{{issueReporter}}", issue_reporter)
        if issue_assignee:
            rendered = rendered.replace("{{issueAssignee}}", issue_assignee)
        else:
            rendered = rendered.replace("{{issueAssignee}}", "the assignee")
        return rendered


@dataclass
class CannedResponseConfig:
    """Configuration file containing all canned responses."""

    version: str
    activated_at: datetime
    shadow_mode_hours: int
    canned_responses: List[CannedResponse]

    @property
    def is_shadow_mode_active(self) -> bool:
        """Check if shadow mode is currently active.

        Returns:
            True if within shadow mode window
        """
        from datetime import timezone

        now = datetime.now(timezone.utc)
        shadow_mode_end = self.activated_at.replace(tzinfo=timezone.utc) + datetime.timedelta(
            hours=self.shadow_mode_hours
        )
        return now < shadow_mode_end

    @classmethod
    def load_from_yaml(cls, file_path: str) -> "CannedResponseConfig":
        """Load canned responses from YAML file.

        Args:
            file_path: Path to canned_responses.yaml

        Returns:
            CannedResponseConfig instance

        Raises:
            FileNotFoundError: If YAML file not found
            ValueError: If YAML is invalid
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Parse datetime
        activated_at = datetime.fromisoformat(data["activated_at"].replace("Z", "+00:00"))

        # Parse canned responses
        responses = [
            CannedResponse(
                id=r["id"],
                name=r["name"],
                category=r.get("category", "General"),
                response=r["response"],
                keywords=r["keywords"],
                active=r.get("active", True),
            )
            for r in data["canned_responses"]
        ]

        return cls(
            version=data["version"],
            activated_at=activated_at,
            shadow_mode_hours=data.get("shadow_mode_hours", 48),
            canned_responses=responses,
        )

    def get_active_responses(self) -> List[CannedResponse]:
        """Get list of active canned responses.

        Returns:
            List of active CannedResponse objects
        """
        return [r for r in self.canned_responses if r.active]
