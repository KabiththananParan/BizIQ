"""Isolated SQLite tests for the security database schema."""

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.database import Base
from app.database.models import AuditLog, LoginAttempt, Permission, Role, RolePermission, User


class SecurityModelsTestCase(unittest.TestCase):
    """Exercise the mapped schema without touching the development database."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test_security.db"
        self.engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def create_role_and_user(self) -> tuple[Role, User]:
        role = Role(name="TEST_ROLE")
        user = User(
            username="test-user",
            email="test@example.com",
            password_hash="not-a-password",
            full_name="Test User",
            role=role,
        )
        self.session.add(user)
        self.session.commit()
        return role, user

    def test_schema_creates_all_six_tables(self) -> None:
        table_names = set(inspect(self.engine).get_table_names())
        self.assertEqual(
            table_names,
            {"roles", "users", "permissions", "role_permissions", "audit_logs", "login_attempts"},
        )

    def test_role_user_permission_and_relationships(self) -> None:
        role, user = self.create_role_and_user()
        permission = Permission(name="TEST_PERMISSION")
        role.permissions.append(permission)
        self.session.commit()

        self.assertEqual(user.role_id, role.id)
        self.assertEqual(role.users, [user])
        self.assertEqual(role.permissions, [permission])
        self.assertEqual(permission.roles, [role])

    def test_audit_log_and_login_attempt_can_reference_user(self) -> None:
        _, user = self.create_role_and_user()
        user_email = user.email
        audit_log = AuditLog(user=user, action="TEST_ACTION", status="SUCCESS")
        login_attempt = LoginAttempt(user=user, email=user_email, success=True)
        self.session.add_all([audit_log, login_attempt])
        self.session.commit()

        self.assertEqual(audit_log.user_id, user.id)
        self.assertEqual(login_attempt.user_id, user.id)

    def test_login_attempt_user_can_be_null(self) -> None:
        attempt = LoginAttempt(email="unknown@example.com", success=False, failure_reason="Unknown user")
        self.session.add(attempt)
        self.session.commit()

        self.assertIsNone(attempt.user_id)

    def test_duplicate_usernames_and_emails_are_rejected(self) -> None:
        role, _ = self.create_role_and_user()
        self.session.add(
            User(
                username="test-user",
                email="other@example.com",
                password_hash="not-a-password",
                full_name="Another User",
                role=role,
            )
        )
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        self.session.add(
            User(
                username="other-user",
                email="test@example.com",
                password_hash="not-a-password",
                full_name="Another User",
                role=role,
            )
        )
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_duplicate_role_permission_combinations_are_rejected(self) -> None:
        role = Role(name="TEST_ROLE")
        permission = Permission(name="TEST_PERMISSION")
        self.session.add_all([role, permission])
        self.session.commit()

        self.session.add_all(
            [
                RolePermission(role_id=role.id, permission_id=permission.id),
                RolePermission(role_id=role.id, permission_id=permission.id),
            ]
        )
        with self.assertRaises(IntegrityError):
            self.session.commit()


if __name__ == "__main__":
    unittest.main()
