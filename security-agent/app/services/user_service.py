"""User-management database operations for authorized callers."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.models import Role, User
from app.schemas.user import ManagedUserResponse, UserCreateRequest, UserUpdateRequest
from app.services.rbac_service import ROLE_NAMES


class UserNotFoundError(ValueError):
    """Raised when a requested user does not exist."""


class UserConflictError(ValueError):
    """Raised when a username or email would not be unique."""


class InvalidRoleError(ValueError):
    """Raised when an unrecognized role is requested."""


def serialize_managed_user(user: User) -> ManagedUserResponse:
    """Build a safe response without credentials or internal fields."""
    return ManagedUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _get_role(db: Session, role_name: str) -> Role:
    if role_name not in ROLE_NAMES:
        raise InvalidRoleError("The requested role is not valid.")
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise InvalidRoleError("The requested role is not available.")
    return role


def _ensure_unique(db: Session, username: str | None, email: str | None, user_id: int | None = None) -> None:
    if username is not None:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is not None and existing.id != user_id:
            raise UserConflictError("A user with this username or email already exists.")
    if email is not None:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None and existing.id != user_id:
            raise UserConflictError("A user with this username or email already exists.")


def create_user(db: Session, payload: UserCreateRequest) -> User:
    """Create a user with a valid existing role and a bcrypt password hash."""
    _ensure_unique(db, payload.username, str(payload.email))
    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=_get_role(db, payload.role),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UserConflictError("A user with this username or email already exists.") from exc
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    """Return users in stable identifier order."""
    return list(db.scalars(select(User).order_by(User.id)).all())


def get_user(db: Session, user_id: int) -> User:
    """Fetch a user or raise a domain-level not-found error."""
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError("User not found.")
    return user


def update_user(db: Session, user_id: int, payload: UserUpdateRequest) -> User:
    """Update supplied safe fields, hashing a replacement password if provided."""
    user = get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    _ensure_unique(db, changes.get("username"), str(changes["email"]) if "email" in changes else None, user.id)

    if "role" in changes:
        user.role = _get_role(db, changes.pop("role"))
    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
    for field_name, value in changes.items():
        setattr(user, field_name, str(value) if field_name == "email" else value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UserConflictError("A user with this username or email already exists.") from exc
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """Delete an existing user."""
    user = get_user(db, user_id)
    db.delete(user)
    db.commit()
