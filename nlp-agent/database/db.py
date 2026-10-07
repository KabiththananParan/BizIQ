import sqlite3
from contextlib import contextmanager
from app.services import config


@contextmanager
def get_conn():
    """Open a SQLite connection and automatically commit/rollback."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the NLP agent's local tables if they do not exist."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_question TEXT NOT NULL,
                normalized_question TEXT NOT NULL,
                summary TEXT DEFAULT '',
                intent TEXT NOT NULL,
                structured_query TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER,
                text TEXT NOT NULL,
                type TEXT NOT NULL,
                FOREIGN KEY(query_id) REFERENCES queries(id) ON DELETE CASCADE
            );
            """
        )
