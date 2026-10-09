"""Isolated tests for independent service and end-user authorization."""

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

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
    """Exercise validation using test-only credentials and a temporary DB."""

    def setUp(self) -> None:
        self.original_secret = settings.jwt_secret_key
        self.original_tokens = settings.service_tokens
        settings.jwt_secret_key = "request-validation-test-secret"
        self.service_tokens = {
            "nlp-agent": "test-nlp-credential",
            "ir-agent": "test-ir-credential",
            "insight-agent": "test-insight-credential",
            "security-agent": "test-security-credential",
        }
        settings.service_tokens = dict(self.service_tokens)

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
        settings.service_tokens = self.original_tokens

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
            "source_agent": "security-agent",
            "target_agent": "security-agent",
            "operation": "SECURITY_ANALYSIS",
            "authorization_token": create_access_token(str(principal.id), principal.role.name),
            "metadata": {"request_type": "business_query"},
        }
        values.update(overrides)
        return values

    def _post(self, payload: dict[str, object], service: str | None = "security-agent"):
        headers = {}
        if service:
            headers["X-BizIQ-Service-Token"] = self.service_tokens[service]
        return self.client.post("/api/v1/security/validate-request", json=payload, headers=headers)

    def _events(self) -> list[AuditLog]:
        return list(self.db.scalars(select(AuditLog).where(AuditLog.action == "SECURITY_REQUEST_VALIDATED")).all())

    def test_valid_service_credential_and_user_jwt_are_allowed_and_audited(self) -> None:
        response = self._post(self._payload())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["allowed"])
        self.assertNotIn("delegation", response.json())
        self.assertNotIn("assertion", response.json())
        event = self._events()[-1]
        details = json.loads(event.details or "{}")
        self.assertEqual(details["verified_service_identity"], "security-agent")
        self.assertEqual(details["authenticated_user_id"], self.admin.id)
        self.assertEqual(details["request_id"], "req-12345")

    def test_missing_and_invalid_service_credentials_are_denied(self) -> None:
        for credential in (None, "wrong-service-token"):
            headers = {} if credential is None else {"X-BizIQ-Service-Token": credential}
            response = self.client.post("/api/v1/security/validate-request", json=self._payload(), headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertFalse(response.json()["allowed"])
            self.assertEqual(response.json()["security_status"], "INVALID_SERVICE_CREDENTIAL")

    def test_unconfigured_service_auth_fails_closed(self) -> None:
        settings.service_tokens = {name: None for name in self.service_tokens}
        response = self._post(self._payload())
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["allowed"])
        self.assertEqual(response.json()["security_status"], "SERVICE_AUTH_UNAVAILABLE")

    def test_ambiguous_duplicate_service_credential_is_rejected(self) -> None:
        settings.service_tokens["nlp-agent"] = self.service_tokens["security-agent"]
        response = self._post(self._payload())
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["allowed"])

    def test_claimed_source_must_match_verified_service_identity(self) -> None:
        payload = self._payload(source_agent="ir-agent")
        response = self._post(payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["security_status"], "DENIED")
        details = json.loads(self._events()[-1].details or "{}")
        self.assertEqual(details["verified_service_identity"], "security-agent")
        self.assertEqual(details["denial_category"], "SERVICE_IDENTITY_MISMATCH")

    def test_missing_invalid_and_expired_user_jwts_are_denied(self) -> None:
        cases = [
            self._payload(authorization_token=None),
            self._payload(authorization_token="not-a-token"),
            self._payload(authorization_token=create_access_token(str(self.admin.id), "ADMIN", timedelta(seconds=-1))),
        ]
        for payload in cases:
            response = self._post(payload)
            self.assertEqual(response.status_code, 401)
            self.assertFalse(response.json()["allowed"])
            self.assertEqual(response.json()["security_status"], "INVALID_TOKEN")

    def test_inactive_and_nonexistent_end_users_are_denied(self) -> None:
        token = create_access_token(str(self.admin.id), "ADMIN")
        self.admin.is_active = False
        self.db.commit()
        inactive = self._post(self._payload(authorization_token=token))
        self.assertEqual(inactive.status_code, 401)

        nonexistent = create_access_token("987654", "ADMIN")
        missing = self._post(self._payload(user_id=987654, authorization_token=nonexistent))
        self.assertEqual(missing.status_code, 401)

    def test_user_id_mismatch_is_denied(self) -> None:
        response = self._post(self._payload(user_id=self.analyst.id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["security_status"], "DENIED")

    def test_unsupported_target_and_operation_are_rejected_by_schema(self) -> None:
        for field, value in (("target_agent", "unknown"), ("operation", "DELETE_DATA")):
            response = self._post(self._payload(**{field: value}))
            self.assertEqual(response.status_code, 422)

    def test_unmapped_business_operation_remains_denied(self) -> None:
        # Prove this stays denied even if a service is explicitly permitted to
        # request it: the separate end-user permission mapping is still absent.
        with patch.dict(
            "app.services.request_security_service.SERVICE_OPERATION_ALLOWLIST",
            {"security-agent": {"security-agent": {"SECURITY_ANALYSIS", "QUERY_DATA"}}},
        ):
            response = self._post(self._payload(operation="QUERY_DATA"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["allowed"])
        self.assertNotIn("delegation", response.json())
        self.assertNotIn("assertion", response.json())
        self.assertEqual(response.json()["security_status"], "INSUFFICIENT_PERMISSION")

    def test_security_analysis_still_requires_existing_user_permission(self) -> None:
        response = self._post(self._payload(user=self.analyst))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["allowed"])
        self.assertEqual(response.json()["security_status"], "INSUFFICIENT_PERMISSION")

    def test_service_operation_allowlist_is_independent_and_denies_other_agents(self) -> None:
        response = self._post(
            self._payload(source_agent="nlp-agent", target_agent="ir-agent"), service="nlp-agent"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["security_status"], "SERVICE_NOT_AUTHORIZED")

    def test_audit_contains_verified_identity_and_no_credentials_or_metadata(self) -> None:
        user_jwt = self._payload()["authorization_token"]
        service_token = self.service_tokens["security-agent"]
        response = self._post(self._payload(metadata={"password": "private-marker"}))
        self.assertEqual(response.status_code, 200)
        event_text = " ".join(event.details or "" for event in self._events())
        self.assertIn('"verified_service_identity":"security-agent"', event_text)
        for prohibited in (str(user_jwt), service_token, "private-marker", "password_hash"):
            self.assertNotIn(prohibited, response.text)
            self.assertNotIn(prohibited, event_text)

    def test_audit_failures_never_turn_denials_or_allows_into_allow(self) -> None:
        with patch("app.services.request_security_service.record_event", side_effect=RuntimeError("audit down")):
            denied = self._post(self._payload(), service=None)
            self.assertFalse(denied.json()["allowed"])
            self.assertEqual(denied.status_code, 401)

            would_allow = self._post(self._payload())
            self.assertFalse(would_allow.json()["allowed"])
            self.assertEqual(would_allow.status_code, 503)

    def test_validation_never_calls_groq_analysis(self) -> None:
        with patch("app.api.security.analyze_security_evidence") as analyze:
            self._post(self._payload())
        analyze.assert_not_called()


if __name__ == "__main__":
    unittest.main()
