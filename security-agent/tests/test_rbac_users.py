"""RBAC seeding, authorization, and protected user-management tests."""

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.users import (
    create_managed_user,
    delete_managed_user,
    read_user,
    read_users,
    update_managed_user,
)
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.database.database import Base
from app.database.models import Permission, Role, RolePermission, User
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.services.rbac_service import ROLE_PERMISSIONS, seed_access_control


class RbacAndUsersTestCase(unittest.TestCase):
    """Exercise RBAC behavior against a disposable database."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test_rbac.db"
        self.engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        seed_access_control(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def user_for_role(self, role_name: str, suffix: str | None = None) -> User:
        unique_suffix = suffix or role_name.lower()
        role = self.session.scalar(select(Role).where(Role.name == role_name))
        user = User(
            username=f"{unique_suffix}-user",
            email=f"{unique_suffix}@example.com",
            password_hash=hash_password("StrongPassword123"),
            full_name=f"{role_name} User",
            role=role,
        )
        self.session.add(user)
        self.session.commit()
        return user

    @staticmethod
    def create_payload(**overrides: str) -> UserCreateRequest:
        values = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPassword123",
            "full_name": "Alice Smith",
            "role": "ANALYST",
        }
        values.update(overrides)
        return UserCreateRequest(**values)

    def test_roles_permissions_and_mappings_are_seeded_idempotently(self) -> None:
        self.assertEqual({role.name for role in self.session.scalars(select(Role)).all()}, set(ROLE_PERMISSIONS))
        self.assertEqual(
            {permission.name for permission in self.session.scalars(select(Permission)).all()},
            set().union(*ROLE_PERMISSIONS.values()),
        )
        for role_name, expected_permissions in ROLE_PERMISSIONS.items():
            role = self.session.scalar(select(Role).where(Role.name == role_name))
            self.assertEqual({permission.name for permission in role.permissions}, expected_permissions)

        counts_before = (
            self.session.scalar(select(func.count()).select_from(Role)),
            self.session.scalar(select(func.count()).select_from(Permission)),
            self.session.scalar(select(func.count()).select_from(RolePermission)),
        )
        seed_access_control(self.session)
        counts_after = (
            self.session.scalar(select(func.count()).select_from(Role)),
            self.session.scalar(select(func.count()).select_from(Permission)),
            self.session.scalar(select(func.count()).select_from(RolePermission)),
        )
        self.assertEqual(counts_before, counts_after)

    def test_permission_dependency_returns_403_for_user_and_analyst_restrictions(self) -> None:
        user = self.user_for_role("USER")
        analyst = self.user_for_role("ANALYST")

        with self.assertRaises(HTTPException) as user_error:
            require_permission("CREATE_USERS")(user, self.session)
        self.assertEqual(user_error.exception.status_code, 403)

        with self.assertRaises(HTTPException) as analyst_error:
            require_permission("DELETE_USERS")(analyst, self.session)
        self.assertEqual(analyst_error.exception.status_code, 403)

    def test_admin_permission_dependency_allows_user_management(self) -> None:
        admin = self.user_for_role("ADMIN")
        self.assertEqual(require_permission("MANAGE_USERS")(admin, self.session).id, admin.id)
        self.assertEqual(require_permission("DELETE_USERS")(admin, self.session).id, admin.id)

    def test_admin_can_create_list_get_update_and_delete_users(self) -> None:
        admin = self.user_for_role("ADMIN")
        created = create_managed_user(self.create_payload(), self.session, admin)
        stored = self.session.get(User, created.id)
        self.assertTrue(verify_password("StrongPassword123", stored.password_hash))
        self.assertNotIn("password_hash", created.model_dump())

        listed = read_users(self.session, admin)
        self.assertIn(created.id, [user.id for user in listed])
        self.assertEqual(read_user(created.id, self.session, admin).email, "alice@example.com")

        updated = update_managed_user(
            created.id,
            UserUpdateRequest(full_name="Alice Updated", role="USER", is_active=False),
            self.session,
            admin,
        )
        self.assertEqual(updated.full_name, "Alice Updated")
        self.assertEqual(updated.role, "USER")
        self.assertFalse(updated.is_active)

        response = delete_managed_user(created.id, self.session, admin)
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.session.get(User, created.id))

    def test_user_creation_rejects_duplicate_username_email_and_invalid_role(self) -> None:
        admin = self.user_for_role("ADMIN")
        create_managed_user(self.create_payload(), self.session, admin)

        with self.assertRaises(HTTPException) as username_error:
            create_managed_user(self.create_payload(email="other@example.com"), self.session, admin)
        self.assertEqual(username_error.exception.status_code, 409)

        with self.assertRaises(HTTPException) as email_error:
            create_managed_user(self.create_payload(username="other-user"), self.session, admin)
        self.assertEqual(email_error.exception.status_code, 409)

        with self.assertRaises(ValidationError):
            self.create_payload(role="UNTRUSTED")

    def test_nonexistent_user_is_not_found(self) -> None:
        admin = self.user_for_role("ADMIN")
        with self.assertRaises(HTTPException) as error:
            read_user(9999, self.session, admin)
        self.assertEqual(error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
