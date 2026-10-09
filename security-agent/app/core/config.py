"""Application configuration sourced from environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()

SERVICE_TOKEN_ENV = {
    "nlp-agent": "BIZIQ_SERVICE_TOKEN_NLP_AGENT",
    "ir-agent": "BIZIQ_SERVICE_TOKEN_IR_AGENT",
    "insight-agent": "BIZIQ_SERVICE_TOKEN_INSIGHT_AGENT",
    "security-agent": "BIZIQ_SERVICE_TOKEN_SECURITY_AGENT",
}


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
    failed_login_threshold: int = field(default_factory=lambda: int(os.getenv("FAILED_LOGIN_THRESHOLD", "5")))
    access_denied_threshold: int = field(default_factory=lambda: int(os.getenv("ACCESS_DENIED_THRESHOLD", "3")))
    unique_ip_threshold: int = field(default_factory=lambda: int(os.getenv("UNIQUE_IP_THRESHOLD", "2")))
    login_frequency_threshold: int = field(default_factory=lambda: int(os.getenv("LOGIN_FREQUENCY_THRESHOLD", "10")))
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))
    service_tokens: dict[str, str | None] = field(
        default_factory=lambda: {
            agent: os.getenv(variable) for agent, variable in SERVICE_TOKEN_ENV.items()
        }
    )


settings = Settings()
