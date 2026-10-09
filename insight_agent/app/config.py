import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv()
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "security-agent" / ".env")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or ""
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("GROQ_MODEL") or "openai/gpt-oss-20b"
DB_PATH = os.getenv("DB_PATH", "insights.db")
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY", "biziq-prod-sec-jwt-094fa8291b8d273a0e628174fb1c9d2e")
DEV_AUTH = os.getenv("DEV_AUTH", "true").lower() == "true"
