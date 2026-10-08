"""Reusable authentication and deterministic authorization dependencies."""

from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.database import get_db
from app.database.models import User

DatabaseSession = Annotated[Session, Depends(get_db)]


def require_permission(permission_name: str) -> Callable[..., User]:
    """Return a dependency that permits only users whose role has a permission."""

    def permission_dependency(
        current_user: Annotated[User, Depends(get_current_user)], db: DatabaseSession
    ) -> User:
        db.refresh(current_user, attribute_names=["role"])
        if permission_name not in {permission.name for permission in current_user.role.permissions}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return permission_dependency
