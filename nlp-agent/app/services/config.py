import os

# -----------------------------------------------------------------------------
# Basic configuration
# -----------------------------------------------------------------------------

DB_PATH = os.getenv("NLP_DB_PATH", "biziq_nlp.db")
IR_AGENT_URL = os.getenv("IR_AGENT_URL", "http://127.0.0.1:8002")
IR_AGENT_TOKEN = os.getenv("IR_AGENT_TOKEN", "demo-analyst-token")
REQUEST_TIMEOUT = float(os.getenv("IR_REQUEST_TIMEOUT", "30"))

MAX_QUERY_CHARS = int(os.getenv("MAX_QUERY_CHARS", "1000"))
SUMMARY_THRESHOLD_WORDS = int(os.getenv("SUMMARY_THRESHOLD_WORDS", "40"))
SUMMARY_SENTENCES = int(os.getenv("SUMMARY_SENTENCES", "2"))
