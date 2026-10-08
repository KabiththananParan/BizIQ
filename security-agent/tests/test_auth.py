"""Unit tests for authentication services, tokens, and route handlers."""

import asyncio
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.auth import credentials_exception, get_current_user, login, oauth2_scheme, read_current_user, register
from app.core.config import settings
from app.core.security import TokenValidationError, create_access_token, decode_access_token, verify_password
from app.database.database import Base
from app.database.models import User
from app.schemas.auth import LoginRequest, RegistrationRequest
from app.services.auth_service import serialize_user


class AuthenticationTestCase(unittest.TestCase):
    """Test authentication behavior against a disposable SQLite database."""

    def setUp(self) -> None:
        self.original_secret = settings.jwt_secret_key
        self.original_algorithm = settings.jwt_algorithm
        self.original_expiry = settings.access_token_expire_minutes
        settings.jwt_secret_key = "unit-test-secret-that-is-never-used-in-production"
        settings.jwt_algorithm = "HS256"
        settings.access_token_expire_minutes = 60

        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test_auth.db"
        self.engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        self.temp_dir.cleanup()
        settings.jwt_secret_key = self.original_secret
        settings.jwt_algorithm = self.original_algorithm
        settings.access_token_expire_minutes = self.original_expiry

    @staticmethod
    def registration_payload(**overrides: str) -> RegistrationRequest:
        payload = {
            "username": "john",
            "email": "john@example.com",
            "password": "StrongPassword123",
            "full_name": "John Smith",
        }
        payload.update(overrides)
        return RegistrationRequest(**payload)

    def register_default_user(self):
        return register(self.registration_payload(), self.session)

    def test_registration_assigns_user_role_hashes_password_and_hides_hash(self) -> None:
        response = self.register_default_user()
        user = self.session.get(User, response.id)

        self.assertEqual(response.role, "USER")
        self.assertTrue(verify_password("StrongPassword123", user.password_hash))
        self.assertNotEqual(user.password_hash, "StrongPassword123")
        self.assertNotIn("password_hash", response.model_dump())

    def test_registration_rejects_invalid_email_and_weak_password(self) -> None:
        with self.assertRaises(ValidationError):
            self.registration_payload(email="not-an-email")
        with self.assertRaises(ValidationError):
            self.registration_payload(password="short")

    def test_registration_rejects_duplicate_username_and_email(self) -> None:
        self.register_default_user()
        with self.assertRaises(HTTPException) as username_error:
            register(self.registration_payload(email="other@example.com"), self.session)
        self.assertEqual(username_error.exception.status_code, 409)

        with self.assertRaises(HTTPException) as email_error:
            register(self.registration_payload(username="other-user"), self.session)
        self.assertEqual(email_error.exception.status_code, 409)

    def test_login_returns_a_token_with_minimal_expected_claims(self) -> None:
        response = self.register_default_user()
        token_response = login(LoginRequest(email=response.email, password="StrongPassword123"), self.session)
        claims = decode_access_token(token_response.access_token)

        self.assertEqual(token_response.token_type, "bearer")
        self.assertEqual(token_response.expires_in, 3600)
        self.assertEqual(claims["sub"], str(response.id))
        self.assertEqual(claims["role"], "USER")
        self.assertEqual(set(claims), {"sub", "role", "exp"})

    def test_login_uses_generic_error_for_wrong_missing_and_inactive_users(self) -> None:
        response = self.register_default_user()
        attempts = [
            LoginRequest(email=response.email, password="WrongPassword123"),
            LoginRequest(email="unknown@example.com", password="StrongPassword123"),
        ]
        user = self.session.get(User, response.id)
        user.is_active = False
        self.session.commit()
        attempts.append(LoginRequest(email=response.email, password="StrongPassword123"))

        for credentials in attempts:
            with self.assertRaises(HTTPException) as error:
                login(credentials, self.session)
            self.assertEqual(error.exception.status_code, 401)
            self.assertEqual(error.exception.detail, "Invalid credentials.")

    def test_token_validation_rejects_invalid_expired_and_malformed_tokens(self) -> None:
        valid_token = create_access_token("1", "USER")
        self.assertEqual(decode_access_token(valid_token)["sub"], "1")

        expired_token = create_access_token("1", "USER", expires_delta=timedelta(seconds=-1))
        for token in ("not.a.jwt", expired_token):
            with self.assertRaises(TokenValidationError):
                decode_access_token(token)

    def test_current_user_requires_valid_active_user_token(self) -> None:
        response = self.register_default_user()
        token = create_access_token(str(response.id), "USER")
        current_user = get_current_user(token, self.session)
        self.assertEqual(read_current_user(current_user).id, response.id)

        with self.assertRaises(HTTPException) as invalid_error:
            get_current_user("not.a.jwt", self.session)
        self.assertEqual(invalid_error.exception.status_code, 401)

        expired_token = create_access_token(str(response.id), "USER", expires_delta=timedelta(seconds=-1))
        with self.assertRaises(HTTPException) as expired_error:
            get_current_user(expired_token, self.session)
        self.assertEqual(expired_error.exception.status_code, 401)

        user = self.session.get(User, response.id)
        user.is_active = False
        self.session.commit()
        with self.assertRaises(HTTPException) as inactive_error:
            get_current_user(token, self.session)
        self.assertEqual(inactive_error.exception.status_code, 401)

    def test_missing_bearer_token_is_rejected(self) -> None:
        request = Request({"type": "http", "headers": [], "method": "GET", "path": "/api/v1/auth/me"})
        with self.assertRaises(HTTPException) as error:
            asyncio.run(oauth2_scheme(request))
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(credentials_exception().status_code, 401)

    def test_safe_user_serialization_never_exposes_password_hash(self) -> None:
        response = self.register_default_user()
        user = self.session.get(User, response.id)
        self.assertNotIn("password_hash", serialize_user(user).model_dump_json())


if __name__ == "__main__":
    unittest.main()
