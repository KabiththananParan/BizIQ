"""Application configuration sourced from environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    """Service settings; authentication secrets are never stored in source."""

    app_name: str = "Security & Compliance Agent"
    service_name: str = "security-compliance-agent"
    database_url: str = "sqlite:///./security.db"
    jwt_secret_key: str | None = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )


settings = Settings()
