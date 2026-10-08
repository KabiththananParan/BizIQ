"""Frontend configuration helper sourcing API connection settings."""

import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8003").rstrip("/")
DEFAULT_TIMEOUT_SECONDS: int = 20
