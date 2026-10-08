"""Password and JWT primitives used by authentication services."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenValidationError(ValueError):
    """Raised when a JWT cannot be decoded into a valid access token."""


def hash_password(password: str) -> str:
    """Return a bcrypt hash for a password that passed request validation."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Safely compare a candidate password with its stored bcrypt hash."""
    return pwd_context.verify(plain_password, password_hash)


def _jwt_secret() -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be configured before authentication is used.")
    if settings.jwt_algorithm != "HS256":
        raise RuntimeError("JWT_ALGORITHM must be HS256.")
    return settings.jwt_secret_key


def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed access token containing only subject, role, and expiry."""
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    return jwt.encode(
        {"sub": subject, "role": role, "exp": expires_at},
        _jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate a signed access token and return its minimal claims."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenValidationError("Invalid or expired access token.") from exc

    subject = payload.get("sub")
    role = payload.get("role")
    if not isinstance(subject, str) or not isinstance(role, str):
        raise TokenValidationError("Access token has invalid claims.")
    return payload
