"""Unit and integration tests for the Security Dashboard API and aggregation service."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database.database import Base, get_db
from app.database.models import AuditLog, LoginAttempt, Role, User
from app.main import app
from app.services.rbac_service import seed_access_control
from app.services.security_dashboard_service import get_security_dashboard


class SecurityDashboardTestCase(unittest.TestCase):
    """Test suite for Security Dashboard API authorization, aggregation, and safety."""

    def setUp(self) -> None:
        self.original_secret = settings.jwt_secret_key
        settings.jwt_secret_key = "dashboard-test-secret-key"

        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test_dashboard.db"
        self.engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        seed_access_control(self.session)

        def override_get_db():
            try:
                yield self.session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.now = datetime.now(timezone.utc)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()
        self.temp_dir.cleanup()
        settings.jwt_secret_key = self.original_secret

    def create_user(self, role_name: str, username: str, email: str, is_active: bool = True) -> User:
        role = self.session.query(Role).filter(Role.name == role_name).one()
        user = User(
            username=username,
            email=email,
            password_hash=hash_password("SafePassword123!"),
            full_name=f"{username.capitalize()} User",
            role=role,
            is_active=is_active,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def auth_headers(self, user: User) -> dict[str, str]:
        token = create_access_token(str(user.id), user.role.name)
        return {"Authorization": f"Bearer {token}"}

    # 1. Unauthenticated request -> 401
    def test_unauthenticated_request_returns_401(self) -> None:
        response = self.client.get("/api/v1/security/dashboard")
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())

    # 2. USER -> 403
    def test_user_role_returns_403(self) -> None:
        user = self.create_user("USER", "regular", "regular@example.com")
        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(user))
        self.assertEqual(response.status_code, 403)
        self.assertIn("permission", response.json()["detail"].lower())

    # 3. ANALYST -> 200
    def test_analyst_role_returns_200(self) -> None:
        analyst = self.create_user("ANALYST", "analyst", "analyst@example.com")
        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("overview", data)
        self.assertIn("signals", data)
        self.assertIn("risk_summary", data)
        self.assertIn("recent_events", data)

    # 4. ADMIN -> 200
    def test_admin_role_returns_200(self) -> None:
        admin = self.create_user("ADMIN", "admin", "admin@example.com")
        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(admin))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("overview", data)
        self.assertIn("signals", data)
        self.assertIn("risk_summary", data)
        self.assertIn("recent_events", data)

    # 5. Correct total users
    def test_correct_total_users(self) -> None:
        analyst = self.create_user("ANALYST", "analyst1", "analyst1@example.com")
        self.create_user("USER", "user1", "user1@example.com")
        self.create_user("USER", "user2", "user2@example.com", is_active=False)

        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["overview"]["total_users"], 3)

    # 6. Correct active users
    def test_correct_active_users(self) -> None:
        analyst = self.create_user("ANALYST", "analyst2", "analyst2@example.com")
        self.create_user("USER", "active1", "active1@example.com", is_active=True)
        self.create_user("USER", "inactive1", "inactive1@example.com", is_active=False)
        self.create_user("USER", "inactive2", "inactive2@example.com", is_active=False)

        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        overview = response.json()["overview"]
        self.assertEqual(overview["total_users"], 4)
        self.assertEqual(overview["active_users"], 2)  # analyst + active1

    # 7. Correct login totals
    def test_correct_login_totals(self) -> None:
        analyst = self.create_user("ANALYST", "analyst3", "analyst3@example.com")
        user = self.create_user("USER", "target", "target@example.com")

        # 3 successful logins, 2 failed logins
        for _ in range(3):
            self.session.add(LoginAttempt(email=user.email, user_id=user.id, success=True, timestamp=self.now))
        for _ in range(2):
            self.session.add(LoginAttempt(email=user.email, user_id=user.id, success=False, timestamp=self.now))
        self.session.commit()

        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        overview = response.json()["overview"]
        self.assertEqual(overview["total_login_attempts"], 5)
        self.assertEqual(overview["successful_logins"], 3)
        self.assertEqual(overview["failed_logins"], 2)

    # 8. Correct failed login count
    def test_correct_failed_login_count(self) -> None:
        analyst = self.create_user("ANALYST", "analyst4", "analyst4@example.com")
        user = self.create_user("USER", "target4", "target4@example.com")

        for _ in range(7):
            self.session.add(LoginAttempt(email=user.email, user_id=user.id, success=False, timestamp=self.now))
        self.session.commit()

        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        overview = response.json()["overview"]
        self.assertEqual(overview["failed_logins"], 7)
        self.assertEqual(overview["total_login_attempts"], 7)
        self.assertEqual(overview["successful_logins"], 0)

    # 9. Correct security event counts and signals
    def test_correct_security_event_counts_and_signals(self) -> None:
        analyst = self.create_user("ANALYST", "analyst5", "analyst5@example.com")
        user = self.create_user("USER", "target5", "target5@example.com")

        # Create 5 failed logins from 2 different IPs -> triggers REPEATED_FAILED_LOGINS and MULTIPLE_IP_ADDRESSES
        for _ in range(3):
            self.session.add(
                LoginAttempt(
                    email=user.email, user_id=user.id, success=False, ip_address="192.168.1.1", timestamp=self.now
                )
            )
        for _ in range(2):
            self.session.add(
                LoginAttempt(
                    email=user.email, user_id=user.id, success=False, ip_address="192.168.1.2", timestamp=self.now
                )
            )

        # Create 3 ACCESS_DENIED events -> triggers REPEATED_ACCESS_DENIED
        for _ in range(3):
            self.session.add(
                AuditLog(
                    user_id=user.id,
                    action="ACCESS_DENIED",
                    status="FAILED",
                    ip_address="192.168.1.1",
                    created_at=self.now,
                )
            )

        # Create 2 INVALID_TOKEN events -> triggers INVALID_TOKEN_ACTIVITY
        for _ in range(2):
            self.session.add(
                AuditLog(
                    user_id=user.id,
                    action="INVALID_TOKEN",
                    status="FAILED",
                    ip_address="192.168.1.1",
                    created_at=self.now,
                )
            )

        # Create 1 EXPIRED_TOKEN event -> triggers EXPIRED_TOKEN_ACTIVITY
        self.session.add(
            AuditLog(
                user_id=user.id,
                action="EXPIRED_TOKEN",
                status="FAILED",
                ip_address="192.168.1.1",
                created_at=self.now,
            )
        )
        self.session.commit()

        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Overview verification
        overview = data["overview"]
        self.assertEqual(overview["access_denied_events"], 3)
        self.assertEqual(overview["invalid_token_events"], 2)
        self.assertEqual(overview["expired_token_events"], 1)

        # Signals verification
        signals = data["signals"]
        self.assertEqual(signals["repeated_failed_logins"], 1)
        self.assertEqual(signals["multiple_ip_addresses"], 1)
        self.assertEqual(signals["repeated_access_denied"], 1)
        self.assertEqual(signals["invalid_token_activity"], 1)
        self.assertEqual(signals["expired_token_activity"], 1)
        self.assertEqual(signals["unusual_login_frequency"], 0)  # 5 attempts < threshold of 10

    # 10. Recent events are returned
    def test_recent_events_are_returned(self) -> None:
        analyst = self.create_user("ANALYST", "analyst6", "analyst6@example.com")
        user = self.create_user("USER", "target6", "target6@example.com")

        self.session.add(
            AuditLog(
                user_id=user.id,
                action="LOGIN_FAILED",
                status="FAILED",
                ip_address="10.0.0.1",
                details="invalid_credentials",
                created_at=self.now - timedelta(minutes=5),
            )
        )
        self.session.add(
            AuditLog(
                user_id=user.id,
                action="ACCESS_DENIED",
                status="FAILED",
                ip_address="10.0.0.1",
                details="missing_permission",
                created_at=self.now - timedelta(minutes=2),
            )
        )
        self.session.commit()

        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        recent_events = response.json()["recent_events"]
        self.assertGreaterEqual(len(recent_events), 2)

        # Verify event fields
        first_event = recent_events[0]
        self.assertIn("event", first_event)
        self.assertIn("user_id", first_event)
        self.assertIn("status", first_event)
        self.assertIn("ip_address", first_event)
        self.assertIn("timestamp", first_event)
        self.assertIn("details", first_event)
        self.assertEqual(first_event["event"], "ACCESS_DENIED")
        self.assertEqual(first_event["user_id"], user.id)

    # 11. Sensitive information is absent
    def test_sensitive_information_is_absent(self) -> None:
        analyst = self.create_user("ANALYST", "analyst7", "analyst7@example.com")
        user = self.create_user("USER", "target7", "target7@example.com")

        self.session.add(
            AuditLog(
                user_id=user.id,
                action="LOGIN_SUCCESS",
                status="SUCCESS",
                ip_address="127.0.0.1",
                details="user_authenticated",
                created_at=self.now,
            )
        )
        self.session.commit()

        response = self.client.get("/api/v1/security/dashboard", headers=self.auth_headers(analyst))
        self.assertEqual(response.status_code, 200)
        raw_text = response.text.lower()

        self.assertNotIn("password_hash", raw_text)
        self.assertNotIn("safepassword", raw_text)
        self.assertNotIn("secret", raw_text)
        self.assertNotIn("api_key", raw_text)
        self.assertNotIn("bearer", raw_text)

    # 12. Start/end filtering works
    def test_start_end_filtering_works(self) -> None:
        analyst = self.create_user("ANALYST", "analyst8", "analyst8@example.com")
        user = self.create_user("USER", "target8", "target8@example.com")

        past_time = self.now - timedelta(days=5)
        current_time = self.now - timedelta(minutes=10)

        # Add event 5 days ago
        self.session.add(
            LoginAttempt(email=user.email, user_id=user.id, success=False, timestamp=past_time)
        )
        self.session.add(
            AuditLog(user_id=user.id, action="ACCESS_DENIED", status="FAILED", created_at=past_time)
        )

        # Add event today
        self.session.add(
            LoginAttempt(email=user.email, user_id=user.id, success=True, timestamp=current_time)
        )
        self.session.add(
            AuditLog(user_id=user.id, action="LOGIN_SUCCESS", status="SUCCESS", created_at=current_time)
        )
        self.session.commit()

        # Query only the last 24 hours
        start_param = (self.now - timedelta(hours=24)).isoformat()
        end_param = self.now.isoformat()

        response = self.client.get(
            "/api/v1/security/dashboard",
            params={"start": start_param, "end": end_param},
            headers=self.auth_headers(analyst),
        )
        self.assertEqual(response.status_code, 200)
        overview = response.json()["overview"]
        self.assertEqual(overview["total_login_attempts"], 1)
        self.assertEqual(overview["successful_logins"], 1)
        self.assertEqual(overview["failed_logins"], 0)
        self.assertEqual(overview["access_denied_events"], 0)

        # Test invalid range where start > end returns 422
        invalid_start = self.now.isoformat()
        invalid_end = (self.now - timedelta(hours=2)).isoformat()
        bad_response = self.client.get(
            "/api/v1/security/dashboard",
            params={"start": invalid_start, "end": invalid_end},
            headers=self.auth_headers(analyst),
        )
        self.assertEqual(bad_response.status_code, 422)

    # 13. Empty database produces safe zero values
    def test_empty_database_produces_safe_zero_values(self) -> None:
        analyst = self.create_user("ANALYST", "analyst9", "analyst9@example.com")

        result = get_security_dashboard(self.session, self.now - timedelta(hours=24), self.now)
        self.assertEqual(result.overview.total_users, 1)  # only analyst
        self.assertEqual(result.overview.active_users, 1)
        self.assertEqual(result.overview.total_login_attempts, 0)
        self.assertEqual(result.overview.successful_logins, 0)
        self.assertEqual(result.overview.failed_logins, 0)
        self.assertEqual(result.overview.access_denied_events, 0)
        self.assertEqual(result.overview.invalid_token_events, 0)
        self.assertEqual(result.overview.expired_token_events, 0)

        self.assertEqual(result.signals.repeated_failed_logins, 0)
        self.assertEqual(result.signals.multiple_ip_addresses, 0)
        self.assertEqual(result.signals.repeated_access_denied, 0)
        self.assertEqual(result.signals.invalid_token_activity, 0)
        self.assertEqual(result.signals.expired_token_activity, 0)
        self.assertEqual(result.signals.unusual_login_frequency, 0)

        self.assertEqual(result.risk_summary.high, 0)
        self.assertEqual(result.risk_summary.medium, 0)
        self.assertEqual(result.risk_summary.low, 0)
        self.assertEqual(result.risk_summary.unknown, 0)
        self.assertEqual(result.recent_events, [])


if __name__ == "__main__":
    unittest.main()
