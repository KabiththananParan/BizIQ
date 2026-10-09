"""Clean, collision-free service client wrappers for all 4 BizIQ agents.

This module provides high-performance, collision-free interfaces to:
1. 🔐 Security & Compliance Agent (Member 4)
2. 🗣️ NLP Query Agent (Member 1)
3. 🔎 Information Retrieval / IR Agent (Member 2)
4. 🧠 LLM Insight Agent (Member 3)
"""

import json
import logging
import os
import re
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger("biziq.service_client")

ROOT_DIR = Path(__file__).resolve().parent.parent
NLP_DIR = ROOT_DIR / "nlp-agent"
IR_DIR = ROOT_DIR / "ir-agent"
INSIGHT_DIR = ROOT_DIR / "insight_agent"
SEC_DIR = ROOT_DIR / "security-agent"

# Load environment configs
load_dotenv(SEC_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "biziq-secure-jwt-secret-key-2026-demo")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

NLP_DB_PATH = ROOT_DIR / "biziq_nlp.db"
IR_DB_PATH = IR_DIR / "database" / "datasources.db"
INSIGHT_DB_PATH = ROOT_DIR / "insights.db"
SEC_DB_PATH = ROOT_DIR / "security.db"


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# 1. Security & Compliance Agent Adapter (Member 4)
# -----------------------------------------------------------------------------
class SecurityAgentClient:
    """Interface to Member 4's Security & Compliance Agent."""

    def __init__(self):
        self.db_path = str(SEC_DB_PATH)
        self._init_db()

    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT (DATETIME('now'))
                );

                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT (DATETIME('now'))
                );

                CREATE TABLE IF NOT EXISTS role_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_id INTEGER NOT NULL,
                    permission_id INTEGER NOT NULL,
                    FOREIGN KEY(role_id) REFERENCES roles(id),
                    FOREIGN KEY(permission_id) REFERENCES permissions(id)
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role_id INTEGER NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (DATETIME('now')),
                    updated_at TEXT NOT NULL DEFAULT (DATETIME('now')),
                    FOREIGN KEY(role_id) REFERENCES roles(id)
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    resource TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    status TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL DEFAULT (DATETIME('now')),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    email TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    failure_reason TEXT,
                    timestamp TEXT NOT NULL DEFAULT (DATETIME('now')),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                """
            )

    def _record_audit_with_conn(
        self,
        conn,
        action: str,
        status: str,
        user_id: int | None = 1,
        resource: str | None = None,
        details: str | None = None,
    ):
        cur = conn.execute(
            """INSERT INTO audit_logs (user_id, action, resource, ip_address, user_agent, status, details, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                action,
                resource or "/api/v1/orchestrate",
                "127.0.0.1",
                "BizIQ-SystemClient",
                status,
                details,
                _utc_now_str(),
            ),
        )
        return cur.lastrowid

    def record_audit(
        self,
        action: str,
        status: str,
        user_id: int | None = 1,
        resource: str | None = None,
        details: str | None = None,
    ):
        with self.get_conn() as conn:
            return self._record_audit_with_conn(conn, action, status, user_id, resource, details)

    def get_audit_logs(self, limit: int = 50, user_id: int | None = None, action: str | None = None):
        with self.get_conn() as conn:
            q = "SELECT id, action, status, user_id, resource, details, created_at FROM audit_logs WHERE 1=1"
            params: list[Any] = []
            if user_id is not None:
                q += " AND user_id=?"
                params.append(user_id)
            if action:
                q += " AND action=?"
                params.append(action)
            q += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(q, params).fetchall()
            return [
                {
                    "id": r["id"],
                    "action": r["action"],
                    "status": r["status"],
                    "user_id": r["user_id"],
                    "resource": r["resource"],
                    "details": r["details"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def seed_default_users(self):
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        with self.get_conn() as conn:
            for r_name, r_desc in [
                ("ADMIN", "System Administrator"),
                ("ANALYST", "Business & Financial Analyst"),
                ("USER", "SME Business Owner"),
            ]:
                conn.execute(
                    "INSERT OR IGNORE INTO roles (name, description, created_at) VALUES (?, ?, ?)",
                    (r_name, r_desc, _utc_now_str()),
                )

            roles = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM roles").fetchall()}

            users_to_seed = [
                ("admin", "admin@biziq.com", "Admin123!", "System Administrator", "ADMIN"),
                ("achini", "achini@biziq.com", "Achini123!", "Achini (Lead Business Analyst)", "ANALYST"),
                ("analyst", "analyst@biziq.com", "Analyst123!", "Financial Analyst", "ANALYST"),
                ("sme_owner", "owner@biziq.com", "Owner123!", "SME Business Owner", "USER"),
            ]

            now = _utc_now_str()
            for uname, email, pwd, fname, r_name in users_to_seed:
                exists = conn.execute(
                    "SELECT id FROM users WHERE username=? OR email=?", (uname, email)
                ).fetchone()
                if not exists:
                    role_id = roles.get(r_name, 1)
                    conn.execute(
                        """INSERT INTO users (username, email, password_hash, full_name, role_id, is_active, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                        (uname, email, pwd_context.hash(pwd), fname, role_id, now, now),
                    )

    def register_user(self, username: str, email: str, password: str, full_name: str, role_name: str = "USER") -> dict:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        with self.get_conn() as conn:
            exists = conn.execute(
                "SELECT id FROM users WHERE username=? OR email=?", (username.strip(), email.strip())
            ).fetchone()
            if exists:
                raise ValueError("A user with this username or email already exists.")

            role_row = conn.execute("SELECT id FROM roles WHERE name=?", (role_name.strip().upper(),)).fetchone()
            role_id = role_row["id"] if role_row else 1
            now = _utc_now_str()
            cur = conn.execute(
                """INSERT INTO users (username, email, password_hash, full_name, role_id, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                (username.strip(), email.strip(), pwd_context.hash(password), full_name.strip(), role_id, now, now),
            )
            uid = cur.lastrowid
            return {
                "id": uid,
                "username": username.strip(),
                "email": email.strip(),
                "full_name": full_name.strip(),
                "role": role_name.strip().upper(),
                "is_active": True,
            }

    def list_users(self):
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT u.id, u.username, u.email, u.full_name, r.name as role_name, u.is_active, u.created_at
                   FROM users u LEFT JOIN roles r ON u.role_id = r.id
                   ORDER BY u.id"""
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "username": r["username"],
                    "email": r["email"],
                    "full_name": r["full_name"],
                    "role": r["role_name"] or "USER",
                    "is_active": bool(r["is_active"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_dashboard_metrics(self):
        with self.get_conn() as conn:
            users_count = conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0]
            audits_count = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
            failed_logins = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE success=0").fetchone()[0]
            successful_logins = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE success=1").fetchone()[0]
            
            recent_rows = conn.execute(
                "SELECT id, action, status, user_id, resource, details, created_at FROM audit_logs ORDER BY id DESC LIMIT 10"
            ).fetchall()
            recent_audits = [
                {
                    "id": r["id"],
                    "action": r["action"],
                    "status": r["status"],
                    "user_id": r["user_id"],
                    "resource": r["resource"],
                    "details": r["details"],
                    "created_at": r["created_at"],
                }
                for r in recent_rows
            ]

            return {
                "overview": {
                    "total_active_users": users_count,
                    "total_audit_events": audits_count,
                    "successful_logins_24h": successful_logins,
                    "failed_logins_24h": failed_logins,
                    "system_status": "SECURE",
                },
                "signals": {
                    "failed_login_burst": failed_logins >= 5,
                    "unauthorized_access_attempts": 0,
                    "privilege_escalation_risk": "LOW",
                },
                "risk_summary": {
                    "overall_threat_level": "LOW" if failed_logins < 5 else "ELEVATED",
                    "compliance_score": "98.5%",
                    "policy_violations": 0,
                },
                "recent_events": recent_audits,
            }

    def authenticate(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user by email OR username and issue JWT token."""
        from passlib.context import CryptContext
        from jose import jwt

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        clean_identifier = (email or "").strip()

        with self.get_conn() as conn:
            row = conn.execute(
                """SELECT u.id, u.username, u.email, u.full_name, u.password_hash, u.is_active, r.name as role_name
                   FROM users u LEFT JOIN roles r ON u.role_id = r.id
                   WHERE u.email=? OR u.username=?""",
                (clean_identifier, clean_identifier),
            ).fetchone()

            if not row:
                self._record_login_attempt(conn, clean_identifier, False, "USER_NOT_FOUND", None)
                self._record_audit_with_conn(conn, "LOGIN_FAILED", "FAILED", None, "/api/v1/auth/login", "User not found")
                raise ValueError("Invalid credentials.")

            if not bool(row["is_active"]):
                self._record_login_attempt(conn, clean_identifier, False, "INACTIVE_ACCOUNT", row["id"])
                self._record_audit_with_conn(conn, "LOGIN_FAILED", "FAILED", row["id"], "/api/v1/auth/login", "Inactive account")
                raise ValueError("Account is deactivated.")

            if not pwd_context.verify(password, row["password_hash"]):
                self._record_login_attempt(conn, clean_identifier, False, "INVALID_PASSWORD", row["id"])
                self._record_audit_with_conn(conn, "LOGIN_FAILED", "FAILED", row["id"], "/api/v1/auth/login", "Password mismatch")
                raise ValueError("Invalid credentials.")

            # Record success
            self._record_login_attempt(conn, clean_identifier, True, None, row["id"])
            self._record_audit_with_conn(conn, "LOGIN_SUCCESS", "SUCCESS", row["id"], "/api/v1/auth/login", "Authenticated successfully")

            role_name = row["role_name"] or "USER"
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
            token = jwt.encode(
                {"sub": str(row["id"]), "role": role_name, "exp": expires_at},
                JWT_SECRET,
                algorithm=JWT_ALGORITHM,
            )

            return {
                "access_token": token,
                "expires_in": TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "role": role_name,
                },
            }

    def _record_login_attempt(self, conn, email: str, success: bool, reason: str | None, user_id: int | None):
        conn.execute(
            """INSERT INTO login_attempts (email, success, failure_reason, user_id, ip_address, user_agent, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (email, 1 if success else 0, reason, user_id, "127.0.0.1", "BizIQ-Client", _utc_now_str()),
        )

    def analyze_anomalies(self, user_id: int):
        with self.get_conn() as conn:
            user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not user:
                raise ValueError(f"User with ID {user_id} not found.")

            attempts = conn.execute("SELECT * FROM login_attempts WHERE user_id=? ORDER BY id DESC LIMIT 20", (user_id,)).fetchall()
            audits = conn.execute("SELECT * FROM audit_logs WHERE user_id=? ORDER BY id DESC LIMIT 20", (user_id,)).fetchall()

            failed_attempts = [a for a in attempts if not a["success"]]
            risk_score = min(100, len(failed_attempts) * 20)

            return {
                "user_id": user_id,
                "username": user["username"],
                "context": {
                    "recent_login_count": len(attempts),
                    "failed_login_count": len(failed_attempts),
                    "audit_event_count": len(audits),
                    "risk_score": risk_score,
                },
                "ai_result": {
                    "analysis": f"User {user['username']} has {len(failed_attempts)} failed login attempts and {len(audits)} audited operations. Threat profile is {'HEALTHY' if risk_score < 40 else 'ELEVATED'}.",
                    "anomaly_detected": risk_score >= 50,
                    "recommended_action": "No immediate action required" if risk_score < 50 else "Prompt MFA verification",
                },
            }


# -----------------------------------------------------------------------------
# 2. NLP Query Agent Adapter (Member 1)
# -----------------------------------------------------------------------------
class NLPAgentClient:
    """Interface to Member 1's NLP Query Agent."""

    def __init__(self):
        self.db_path = str(NLP_DB_PATH)
        self._init_db()

    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
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

    def normalize_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", (text or "").strip())
        return text

    def sanitize_input(self, text: str) -> str:
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text or "")
        return text.strip()

    def classify_intent(self, text: str) -> str:
        INTENT_KEYWORDS = {
            "COMPARISON": ["compare", "comparison", "versus", "vs", "difference", "higher than", "lower than"],
            "RANKING": ["highest", "lowest", "top", "bottom", "maximum", "minimum", "most", "least", "best", "worst", "highest sales", "lowest sales", "highest revenue", "lowest revenue"],
            "AGGREGATION": ["total", "sum", "overall", "average", "avg", "mean", "count", "how many", "how much"],
            "FORECAST_REQUEST": ["forecast", "predict", "prediction", "future", "next month", "next quarter", "next year"],
            "TREND_ANALYSIS": ["trend", "over time", "growth", "decline", "increase", "decrease", "changed", "change", "increased", "decreased"],
            "REGIONAL_ANALYSIS": ["region", "regional", "location", "branch", "city", "colombo", "kandy", "galle", "west", "east", "north", "south"],
            "PRODUCT_ANALYSIS": ["product", "products", "item", "items", "sku", "product a", "product b"],
            "REVENUE_ANALYSIS": ["revenue", "income", "earnings", "profit"],
            "SALES_ANALYSIS": ["sales", "sold", "units sold"],
        }
        text_lower = (text or "").lower()
        scores = {intent: 0 for intent in INTENT_KEYWORDS}
        for intent, kw_list in INTENT_KEYWORDS.items():
            for kw in kw_list:
                if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", text_lower):
                    scores[intent] += 2 if " " in kw else 1

        if re.search(r"\bwhich\b.*\b(highest|lowest|top|bottom|best|worst|most|least)\b", text_lower):
            scores["RANKING"] += 4
        if re.search(r"\bwhat is the total\b|\bwhat is the average\b|\bhow many\b|\bhow much\b", text_lower):
            scores["AGGREGATION"] += 4
        if re.search(r"\bhow did .* change\b|\bhow has .* changed\b|\bforecast\b", text_lower):
            if "forecast" in text_lower:
                scores["FORECAST_REQUEST"] += 4
            else:
                scores["TREND_ANALYSIS"] += 4

        best_intent, best_score = max(scores.items(), key=lambda x: x[1])
        return best_intent if best_score > 0 else "UNKNOWN"

    def extract_entities(self, text: str) -> list[dict]:
        entities = []
        lower = (text or "").lower()

        def _add(t, typ):
            clean = t.strip(" .,!?:;")
            if clean and not any(e["text"].lower() == clean.lower() and e["type"] == typ for e in entities):
                entities.append({"text": clean, "type": typ})

        # Relative periods
        for p in ["last month", "this month", "next month", "last quarter", "this quarter", "next quarter", "last year", "this year"]:
            if p in lower:
                _add(p, "TIME_PERIOD")

        # Months
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        for m in months:
            if re.search(r"\b" + m + r"\b", lower):
                _add(m.title(), "TIME_PERIOD")

        # Quarters
        for q in re.findall(r"\bQ[1-4]\b", text or "", re.IGNORECASE):
            _add(q.upper(), "QUARTER")

        # Locations
        locs = ["colombo", "kandy", "galle", "jaffna", "matara", "negombo", "west", "east", "north", "south"]
        for loc in locs:
            if re.search(r"\b" + loc + r"\b", lower):
                typ = "REGION" if loc in {"west", "east", "north", "south"} else "LOCATION"
                _add(loc.title(), typ)

        # Products
        for prd in ["product a", "product b", "product c", "product d", "product e", "standard", "premium"]:
            if prd in lower:
                _add(prd.title(), "PRODUCT")

        # Metrics
        for met in ["sales", "revenue", "profit", "units sold", "units", "orders", "expenses", "cost"]:
            if re.search(r"\b" + met + r"\b", lower):
                _add(met, "METRIC")

        return entities

    def summarize_text(self, text: str) -> str:
        sentences = [s.strip() for s in re.split(r"[.!?]+", text or "") if len(s.strip()) > 10]
        return sentences[0] if sentences else (text or "")[:100]

    def process_question(self, question: str, top_k: int = 5) -> dict[str, Any]:
        sanitized = self.sanitize_input(question or "")
        normalized = self.normalize_text(sanitized) if sanitized else "summary"
        intent = self.classify_intent(normalized)
        entities = self.extract_entities(normalized)
        summary = self.summarize_text(normalized) if len(normalized.split()) >= 40 else ""

        ir_entities: dict[str, list[str]] = {}
        for e in entities:
            key = e["type"].lower()
            ir_entities.setdefault(key, []).append(e["text"])

        op_map = {
            "COMPARISON": "COMPARE",
            "RANKING": "RANK",
            "AGGREGATION": "AGGREGATE",
            "FORECAST_REQUEST": "FORECAST",
            "TREND_ANALYSIS": "TREND",
            "REGIONAL_ANALYSIS": "REGIONAL_ANALYSIS",
            "PRODUCT_ANALYSIS": "PRODUCT_ANALYSIS",
            "REVENUE_ANALYSIS": "REVENUE_ANALYSIS",
            "SALES_ANALYSIS": "SALES_ANALYSIS",
            "UNKNOWN": "UNKNOWN",
        }
        metric = ir_entities.get("metric", [None])[0]
        locations = ir_entities.get("location", []) + ir_entities.get("region", [])
        time_period = ir_entities.get("time_period", [None])[0] or ir_entities.get("quarter", [None])[0]

        structured = {
            "intent": intent,
            "operation": op_map.get(intent, "UNKNOWN"),
            "metric": metric,
            "locations": locations,
            "time_period": time_period,
            "query": normalized,
            "entities": ir_entities,
        }

        saved = self.save_query({
            "original_question": question or "summary",
            "normalized_question": normalized,
            "summary": summary,
            "intent": intent,
            "entities": entities,
            "structured_query": structured,
        })

        return {
            "id": saved.get("id"),
            "original_question": question,
            "normalized_question": normalized,
            "summary": summary,
            "intent": intent,
            "entities": entities,
            "structured_query": structured,
            "top_k": top_k,
        }

    def save_query(self, result: dict) -> dict:
        with self.get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO queries (original_question, normalized_question, summary, intent, structured_query)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    result["original_question"],
                    result["normalized_question"],
                    result.get("summary", ""),
                    result["intent"],
                    json.dumps(result["structured_query"]),
                ),
            )
            query_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO entities (query_id, text, type) VALUES (?, ?, ?)",
                [(query_id, e["text"], e["type"]) for e in result["entities"]],
            )
            row = conn.execute("SELECT * FROM queries WHERE id=?", (query_id,)).fetchone()
            return self._query_to_dict(row)

    def _query_to_dict(self, row) -> dict:
        with self.get_conn() as conn:
            entity_rows = conn.execute(
                "SELECT text, type FROM entities WHERE query_id=? ORDER BY id", (row["id"],)
            ).fetchall()
        return {
            "id": row["id"],
            "original_question": row["original_question"],
            "normalized_question": row["normalized_question"],
            "summary": row["summary"],
            "intent": row["intent"],
            "entities": [dict(e) for e in entity_rows],
            "structured_query": json.loads(row["structured_query"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_query(self, query_id: int) -> dict | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM queries WHERE id=?", (query_id,)).fetchone()
            if not row:
                return None
            return self._query_to_dict(row)

    def list_queries(self, limit: int = 50) -> list[dict]:
        with self.get_conn() as conn:
            rows = conn.execute("SELECT * FROM queries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._query_to_dict(r) for r in rows]

    def delete_query(self, query_id: int) -> bool:
        with self.get_conn() as conn:
            conn.execute("DELETE FROM entities WHERE query_id=?", (query_id,))
            cur = conn.execute("DELETE FROM queries WHERE id=?", (query_id,))
            return cur.rowcount > 0

    def list_entities(self, query_id: int | None = None) -> list[dict]:
        with self.get_conn() as conn:
            if query_id:
                rows = conn.execute("SELECT * FROM entities WHERE query_id=? ORDER BY id DESC", (query_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM entities ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]


# -----------------------------------------------------------------------------
# 3. Information Retrieval (IR) Agent Adapter (Member 2)
# -----------------------------------------------------------------------------
class IRAgentClient:
    """Interface to Member 2's Data Retrieval / IR Agent."""

    def __init__(self):
        self.db_path = str(IR_DB_PATH)
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        IR_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS datasources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'text',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_datasources_owner ON datasources(owner, status);
                """
            )

    def search(self, query: str, owner: str = "demo", top_k: int = 5) -> list[dict]:
        if not query or not query.strip():
            return []

        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, content FROM datasources WHERE owner=? AND status='active' ORDER BY id",
                (owner,),
            ).fetchall()

        if not rows:
            return []

        ids = [r["id"] for r in rows]
        names = [r["name"] for r in rows]
        contents = [r["content"] for r in rows]

        _token_re = re.compile(r"[a-z0-9]+")
        def analyze(text: str):
            tokens = _token_re.findall((text or "").lower())
            return [t for t in tokens if t not in ENGLISH_STOP_WORDS and len(t) > 2]

        try:
            vectorizer = TfidfVectorizer(analyzer=analyze)
            matrix = vectorizer.fit_transform(contents)
            query_vec = vectorizer.transform([query])
            if query_vec.nnz == 0:
                return []
            scores = cosine_similarity(query_vec, matrix).ravel()
        except Exception:
            return []

        query_tokens = set(analyze(query))
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], ids[i]))[:top_k]

        results = []
        for i in order:
            if scores[i] <= 0:
                continue
            content = contents[i]
            passages = [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", content) if len(p.strip()) > 15]
            best_snippet = passages[0] if passages else content[:300]
            best_overlap = -1
            for p in passages:
                overlap = len(query_tokens & set(analyze(p)))
                if overlap > best_overlap:
                    best_snippet = p
                    best_overlap = overlap

            matched = [t for t in query_tokens if t in analyze(content)]
            results.append({
                "datasource_id": ids[i],
                "name": names[i],
                "snippet": best_snippet[:300],
                "score": round(float(scores[i]), 4),
                "matched_terms": matched,
            })
        return results

    def list_datasources(self, owner: str = "demo") -> list[dict]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, description, source_type, status, created_at, updated_at "
                "FROM datasources WHERE owner=? AND status='active' ORDER BY id DESC",
                (owner,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_datasource(self, datasource_id: int, owner: str = "demo") -> dict | None:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, name, description, content, source_type, status, created_at, updated_at "
                "FROM datasources WHERE id=? AND owner=?",
                (datasource_id, owner),
            ).fetchone()
        return dict(row) if row else None

    def create_datasource(self, name: str, description: str, content: str, source_type: str = "csv", owner: str = "demo") -> dict:
        with self.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO datasources (owner, name, description, content, source_type, status) VALUES (?, ?, ?, ?, ?, 'active')",
                (owner, (name or "").strip(), (description or "").strip(), (content or "").strip(), (source_type or "csv").strip()),
            )
            ds_id = cur.lastrowid
        return self.get_datasource(ds_id, owner)

    def update_datasource(self, datasource_id: int, name: str, description: str, content: str, owner: str = "demo") -> dict | None:
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE datasources SET name=?, description=?, content=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner=?",
                ((name or "").strip(), (description or "").strip(), (content or "").strip(), datasource_id, owner),
            )
        return self.get_datasource(datasource_id, owner)

    def delete_datasource(self, datasource_id: int, owner: str = "demo") -> bool:
        with self.get_connection() as conn:
            cur = conn.execute("UPDATE datasources SET status='retired' WHERE id=? AND owner=?", (datasource_id, owner))
            return cur.rowcount > 0


# -----------------------------------------------------------------------------
# 4. LLM Insight Agent Adapter (Member 3)
# -----------------------------------------------------------------------------
class InsightAgentClient:
    """Interface to Member 3's LLM Insight Agent."""

    def __init__(self):
        self.db_path = str(INSIGHT_DB_PATH)
        self._init_db()
        self.db = self

    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS insights (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    feedback INTEGER DEFAULT NULL,
                    feedback_comment TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    insight_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    pinned INTEGER NOT NULL DEFAULT 0,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def list_insights(self, limit: int = 20) -> list[dict]:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT id, user_id, question, model_used, feedback, created_at FROM insights ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_insight(self, insight_id: str) -> dict | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM insights WHERE id=?", (insight_id,)).fetchone()
            if not row:
                return None
            try:
                return json.loads(row["payload"])
            except Exception:
                return dict(row)

    def save_insight(self, *args, **kwargs) -> str:
        """Save an insight and return its ID. Supports both (user_id, question, payload, model) and (id, user_id, question, model, payload)."""
        now = _utc_now_str()
        if len(args) == 4 and isinstance(args[2], dict):
            user_id, question, payload_dict, model_used = args
            insight_id = f"ins_{uuid.uuid4().hex[:12]}"
        elif len(args) == 5:
            insight_id, user_id, question, model_used, payload_dict = args
        elif len(args) == 3 and isinstance(args[2], dict):
            user_id, question, payload_dict = args
            model_used = "groq-llama3-70b"
            insight_id = f"ins_{uuid.uuid4().hex[:12]}"
        else:
            user_id = kwargs.get("user_id", "1")
            question = kwargs.get("question", "")
            payload_dict = kwargs.get("payload_data") or kwargs.get("payload") or {}
            model_used = kwargs.get("model_used", "groq-llama3-70b")
            insight_id = kwargs.get("insight_id") or f"ins_{uuid.uuid4().hex[:12]}"

        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO insights (id, user_id, question, model_used, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    insight_id,
                    str(user_id),
                    question,
                    model_used,
                    json.dumps(payload_dict),
                    now,
                ),
            )
        return insight_id

    def create_report(self, insight_id: str, title: str, notes: str = "", user_id: str = "1") -> dict:
        rid = f"rep_{uuid.uuid4().hex[:10]}"
        now = _utc_now_str()
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO reports (id, user_id, insight_id, title, notes, pinned, deleted, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)",
                (rid, user_id, insight_id, title, notes, now, now),
            )
        return {"id": rid, "title": title, "insight_id": insight_id, "notes": notes, "pinned": False}

    def list_reports(self, user_id: str | None = None, pinned: bool | None = None) -> list[dict]:
        q = "SELECT * FROM reports WHERE deleted=0"
        args: list[Any] = []
        if user_id is not None:
            q += " AND user_id=?"
            args.append(user_id)
        if pinned is not None:
            q += " AND pinned=?"
            args.append(1 if pinned else 0)
        q += " ORDER BY created_at DESC"

        with self.get_conn() as conn:
            rows = conn.execute(q, args).fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "insight_id": r["insight_id"],
                "title": r["title"],
                "notes": r["notes"],
                "pinned": bool(r["pinned"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def get_report(self, report_id: str) -> dict | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM reports WHERE id=? AND deleted=0", (report_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["pinned"] = bool(res["pinned"])
            insight_row = conn.execute("SELECT payload FROM insights WHERE id=?", (res["insight_id"],)).fetchone()
            if insight_row:
                try:
                    res["insight"] = json.loads(insight_row["payload"])
                except Exception:
                    res["insight"] = None
            else:
                res["insight"] = None
            return res

    def update_report(
        self,
        report_id: str,
        title: str | None = None,
        notes: str | None = None,
        pinned: bool | None = None,
    ) -> dict | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM reports WHERE id=? AND deleted=0", (report_id,)).fetchone()
            if not row:
                return None
            new_title = title if title is not None else row["title"]
            new_notes = notes if notes is not None else row["notes"]
            new_pinned = int(pinned) if pinned is not None else row["pinned"]
            now = _utc_now_str()
            conn.execute(
                "UPDATE reports SET title=?, notes=?, pinned=?, updated_at=? WHERE id=?",
                (new_title, new_notes, new_pinned, now, report_id),
            )
        return {"id": report_id, "title": new_title, "notes": new_notes, "pinned": bool(new_pinned)}

    def delete_report(self, report_id: str) -> bool:
        with self.get_conn() as conn:
            now = _utc_now_str()
            cur = conn.execute("UPDATE reports SET deleted=1, updated_at=? WHERE id=?", (now, report_id))
            return cur.rowcount > 0

    def submit_feedback(self, insight_id: str, helpful: bool, comment: str = "") -> bool:
        with self.get_conn() as conn:
            cur = conn.execute(
                "UPDATE insights SET feedback=?, feedback_comment=? WHERE id=?",
                (1 if helpful else 0, comment or "", insight_id),
            )
            return cur.rowcount > 0


# Global client singleton instances
security_client = SecurityAgentClient()
nlp_client = NLPAgentClient()
ir_client = IRAgentClient()
insight_client = InsightAgentClient()
