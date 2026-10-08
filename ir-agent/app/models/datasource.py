"""
app/models/datasource.py
Data-access layer for the `datasources` table. Every function is scoped to
an `owner`, so one user can never read or change another user's data.
"""

from datetime import datetime, timezone
from typing import Optional

from database.db import get_connection

PUBLIC_COLUMNS = "id, name, description, source_type, status, uploaded_at"
UPDATABLE = {"name", "description", "content", "source_type", "status"}  # whitelist


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _get(conn, datasource_id: int, owner: str) -> Optional[dict]:
    row = conn.execute(
        f"SELECT {PUBLIC_COLUMNS} FROM datasources WHERE id = ? AND owner = ?",
        (datasource_id, owner),
    ).fetchone()
    return dict(row) if row else None


def create(owner: str, name: str, description: str, content: str, source_type: str) -> dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO datasources (name, description, content, source_type, owner, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, content, source_type, owner, _now()),
        )
        conn.commit()
        return _get(conn, cur.lastrowid, owner)


def list_all(owner: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {PUBLIC_COLUMNS} FROM datasources WHERE owner = ? ORDER BY id DESC",
            (owner,),
        ).fetchall()
    return [dict(r) for r in rows]


def get(datasource_id: int, owner: str) -> Optional[dict]:
    with get_connection() as conn:
        return _get(conn, datasource_id, owner)


def update(datasource_id: int, owner: str, fields: dict) -> Optional[dict]:
    """Apply whitelisted `fields`. Returns the updated row, or None if not found."""
    fields = {k: v for k, v in fields.items() if k in UPDATABLE and v is not None}
    with get_connection() as conn:
        if _get(conn, datasource_id, owner) is None:
            return None
        if fields:
            fields["updated_at"] = _now()
            assignments = ", ".join(f"{k} = ?" for k in fields)  # keys are whitelisted
            conn.execute(
                f"UPDATE datasources SET {assignments} WHERE id = ? AND owner = ?",
                [*fields.values(), datasource_id, owner],
            )
            conn.commit()
        return _get(conn, datasource_id, owner)


def delete(datasource_id: int, owner: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM datasources WHERE id = ? AND owner = ?",
                           (datasource_id, owner))
        conn.commit()
        return cur.rowcount > 0
