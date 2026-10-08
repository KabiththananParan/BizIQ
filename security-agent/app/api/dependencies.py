"""Reusable authentication and deterministic authorization dependencies."""

from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.database import get_db
from app.database.models import User
from app.services.audit_service import record_event

DatabaseSession = Annotated[Session, Depends(get_db)]


def require_permission(permission_name: str) -> Callable[..., User]:
    """Return a dependency that permits only users whose role has a permission."""

    def permission_dependency(
        current_user: Annotated[User, Depends(get_current_user)], db: DatabaseSession, request: Request = None
    ) -> User:
        db.refresh(current_user, attribute_names=["role"])
        if permission_name not in {permission.name for permission in current_user.role.permissions}:
            try:
                record_event(db, "ACCESS_DENIED", "FAILED", current_user.id, request.url.path if request else None)
            except Exception:
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return permission_dependency
