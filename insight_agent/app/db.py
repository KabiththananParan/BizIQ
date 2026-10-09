import json
import sqlite3
import uuid
from datetime import datetime, timezone
from .config import DB_PATH


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS insights(
            id TEXT PRIMARY KEY, user_id TEXT, question TEXT, payload TEXT,
            model_used TEXT, feedback INTEGER, feedback_comment TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS reports(
            id TEXT PRIMARY KEY, user_id TEXT, insight_id TEXT, title TEXT, notes TEXT,
            pinned INTEGER DEFAULT 0, deleted INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT);
        """)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def save_insight(user_id: str, question: str, payload: dict, model: str) -> str:
    iid = new_id()
    payload = {**payload, "id": iid, "created_at": now()}
    with conn() as c:
        c.execute("INSERT INTO insights VALUES(?,?,?,?,?,NULL,NULL,?)",
                  (iid, user_id, question, json.dumps(payload), model, payload["created_at"]))
    return iid


def get_insight(iid: str):
    with conn() as c:
        return c.execute("SELECT * FROM insights WHERE id=?", (iid,)).fetchone()
