"""Application configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Non-secret service settings for the initial application foundation."""

    app_name: str = "Security & Compliance Agent"
    service_name: str = "security-compliance-agent"
    database_url: str = "sqlite:///./security.db"


settings = Settings()
