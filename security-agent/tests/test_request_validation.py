"""Integration tests for the service-to-service request validation contract."""

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.security import router
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database.database import Base, get_db
from app.database.models import AuditLog, Role, User
from app.services.rbac_service import seed_access_control


class RequestValidationTestCase(unittest.TestCase):
    """Exercise gateway decisions against an isolated SQLite database."""

    def setUp(self) -> None:
        self.original_secret = settings.jwt_secret_key
        settings.jwt_secret_key = "request-validation-test-secret"
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "request_validation.db"
        self.engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        seed_access_control(self.db)
        self.admin = self._user("ADMIN", "admin")
        self.analyst = self._user("ANALYST", "analyst")

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()
        settings.jwt_secret_key = self.original_secret

    def _user(self, role_name: str, name: str) -> User:
        role = self.db.scalar(select(Role).where(Role.name == role_name))
        user = User(
            username=name,
            email=f"{name}@example.com",
            password_hash=hash_password("StrongPassword123"),
            full_name=name.title(),
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        return user

    def _payload(self, user: User | None = None, **overrides: object) -> dict[str, object]:
        principal = user or self.admin
        values: dict[str, object] = {
            "request_id": "req-12345",
            "user_id": principal.id,
            "source_agent": "nlp-agent",
            "target_agent": "ir-agent",
            "operation": "SECURITY_ANALYSIS",
            "authorization_token": create_access_token(str(principal.id), principal.role.name),
            "metadata": {"request_type": "business_query"},
        }
        values.update(overrides)
        return values

    def _events(self) -> list[AuditLog]:
        return list(self.db.scalars(select(AuditLog).where(AuditLog.action == "SECURITY_REQUEST_VALIDATED")).all())

    def test_valid_admin_security_analysis_request_is_allowed_and_audited(self) -> None:
        response = self.client.post("/api/v1/security/validate-request", json=self._payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["security_status"], "VALID")
        self.assertTrue(response.json()["allowed"])
        event = self._events()[-1]
        self.assertEqual(event.user_id, self.admin.id)
        self.assertNotIn(self._payload()["authorization_token"], event.details or "")

    def test_missing_invalid_and_expired_tokens_are_denied_and_audited(self) -> None:
        cases = [
            self._payload(authorization_token=None),
            self._payload(authorization_token="not-a-token"),
            self._payload(authorization_token=create_access_token(str(self.admin.id), "ADMIN", timedelta(seconds=-1))),
        ]
        for payload in cases:
            response = self.client.post("/api/v1/security/validate-request", json=payload)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["security_status"], "INVALID_TOKEN")
        self.assertEqual(len(self._events()), 3)

    def test_user_mismatch_and_missing_user_are_denied(self) -> None:
        mismatch = self._payload(user=self.admin, user_id=self.analyst.id)
        response = self.client.post("/api/v1/security/validate-request", json=mismatch)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["security_status"], "DENIED")

        nonexistent = self._payload(user_id=99999)
        response = self.client.post("/api/v1/security/validate-request", json=nonexistent)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["security_status"], "INVALID_REQUEST")

    def test_invalid_controlled_values_are_rejected_by_schema(self) -> None:
        for field, value in (("source_agent", "unknown"), ("target_agent", "unknown"), ("operation", "DELETE_DATA")):
            response = self.client.post("/api/v1/security/validate-request", json=self._payload(**{field: value}))
            self.assertEqual(response.status_code, 422)

    def test_security_analysis_requires_existing_run_security_analysis_permission(self) -> None:
        response = self.client.post("/api/v1/security/validate-request", json=self._payload(user=self.analyst))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["security_status"], "INSUFFICIENT_PERMISSION")

    def test_unmapped_operations_are_not_silently_granted(self) -> None:
        response = self.client.post(
            "/api/v1/security/validate-request", json=self._payload(operation="QUERY_DATA")
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["security_status"], "INSUFFICIENT_PERMISSION")

    def test_audit_and_response_never_include_token_or_password_material(self) -> None:
        token = create_access_token(str(self.admin.id), "ADMIN")
        response = self.client.post(
            "/api/v1/security/validate-request",
            json=self._payload(authorization_token=token, metadata={"password": "secret"}),
        )
        body = response.text
        event_text = " ".join((event.details or "") for event in self._events())
        for prohibited in (token, "secret", "password_hash"):
            self.assertNotIn(prohibited, body)
            self.assertNotIn(prohibited, event_text)


if __name__ == "__main__":
    unittest.main()
