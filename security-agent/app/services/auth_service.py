"""Authentication service operations separated from API route handling."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.database.models import Role, User
from app.schemas.auth import RegistrationRequest, UserResponse
from app.services.audit_service import record_event
from app.services.login_attempt_service import record_login_attempt

DEFAULT_REGISTRATION_ROLE = "USER"


class DuplicateUserError(ValueError):
    """Raised when a username or email is already registered."""


class InvalidCredentialsError(ValueError):
    """Raised for all unsuccessful authentication attempts."""


def serialize_user(user: User) -> UserResponse:
    """Convert a mapped user into the safe public response shape."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        is_active=user.is_active,
    )


def _default_user_role(db: Session) -> Role:
    """Find or create the minimal role required for public registration."""
    role = db.scalar(select(Role).where(Role.name == DEFAULT_REGISTRATION_ROLE))
    if role is None:
        role = Role(name=DEFAULT_REGISTRATION_ROLE, description="Default registered user role")
        db.add(role)
        db.flush()
    return role


def register_user(db: Session, registration: RegistrationRequest) -> User:
    """Register a user with the fixed default USER role."""
    if db.scalar(select(User.id).where(User.username == registration.username)) is not None:
        raise DuplicateUserError("A user with this username or email already exists.")
    if db.scalar(select(User.id).where(User.email == str(registration.email))) is not None:
        raise DuplicateUserError("A user with this username or email already exists.")

    user = User(
        username=registration.username,
        email=str(registration.email),
        password_hash=hash_password(registration.password),
        full_name=registration.full_name,
        role=_default_user_role(db),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateUserError("A user with this username or email already exists.") from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str, ip_address: str | None = None, user_agent: str | None = None) -> User:
    """Authenticate an active user without revealing whether an email exists."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash) or not user.is_active:
        reason = "INACTIVE_ACCOUNT" if user is not None and not user.is_active else "INVALID_CREDENTIALS"
        record_login_attempt(db, email, False, user.id if user else None, ip_address, user_agent, reason)
        record_event(db, "LOGIN_FAILED", "FAILED", user.id if user else None, "/api/v1/auth/login", ip_address, user_agent, reason)
        raise InvalidCredentialsError("Invalid credentials.")
    record_login_attempt(db, email, True, user.id, ip_address, user_agent)
    record_event(db, "LOGIN_SUCCESS", "SUCCESS", user.id, "/api/v1/auth/login", ip_address, user_agent)
    return user


def get_active_user_by_id(db: Session, user_id: int) -> User:
    """Retrieve an active user identified by a validated token subject."""
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise InvalidCredentialsError("Invalid credentials.")
    return user
