"""Application settings loaded from environment variables."""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Jira API
    JIRA_BASE_URL: str
    JIRA_EMAIL: str
    JIRA_API_TOKEN: str
    JIRA_WEBHOOK_SECRET: str

    # Slack API
    SLACK_BOT_TOKEN: str
    SLACK_SIGNING_SECRET: str

    # LLM Providers
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None

    # Email Configuration
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 1025
    EMAIL_FROM: str = "green-flag-bot@skyscanner.net"

    # Application Settings
    ENVIRONMENT: str = "development"
    AUTOMATION_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"
    LLM_DEBUG: bool = False

    # Dashboard URL
    DASHBOARD_URL: str = "http://localhost:3000"

    # SSO Configuration (optional)
    OIDC_ISSUER: Optional[str] = None
    OIDC_CLIENT_ID: Optional[str] = None
    OIDC_CLIENT_SECRET: Optional[str] = None

    # Configuration
    CANNED_RESPONSES_PATH: str = "src/config/canned_responses.yaml"
    CONFIG_VERSION: str = "1.0.0"  # Increment when canned responses change

    # Confidence thresholds
    AUTO_RESPOND_THRESHOLD: float = 0.80
    AMBIGUITY_WINDOW: float = 0.10

    # Retraction window (in minutes)
    RETRACTION_WINDOW_MINUTES: int = 5

    # Shadow mode duration (in hours)
    SHADOW_MODE_DURATION_HOURS: int = 48

    # Audit log retention (in days)
    AUDIT_LOG_RETENTION_DAYS: int = 90

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
