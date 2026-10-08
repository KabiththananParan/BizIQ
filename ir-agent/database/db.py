"""
database/db.py
SQLite persistence layer for the IR Agent.

- DB path comes from the IR_DB_PATH env var (default: database/datasources.db).
- Every data source has an `owner` so users can only see their own data.
- init_db() also migrates older databases that lack the `owner` column.
"""

import os
import sqlite3
from contextlib import contextmanager


def get_db_path() -> str:
    return os.environ.get("IR_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasources.db"))


@contextmanager
def get_connection():
    """Context-managed SQLite connection that is always closed."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create the table if needed and migrate older schemas. Safe to call repeatedly."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datasources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'text',
                status TEXT NOT NULL DEFAULT 'active',
                owner TEXT NOT NULL DEFAULT 'demo',
                uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        # Migration for databases created by the earlier version (no owner column)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(datasources)")}
        if "owner" not in cols:
            conn.execute("ALTER TABLE datasources ADD COLUMN owner TEXT NOT NULL DEFAULT 'demo'")
        if "updated_at" not in cols:
            conn.execute("ALTER TABLE datasources ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ds_owner_status ON datasources(owner, status)")
        conn.commit()
