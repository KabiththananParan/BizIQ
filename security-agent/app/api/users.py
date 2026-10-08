"""Permission-protected Users & Access Control endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.database.database import get_db
from app.database.models import User
from app.schemas.user import ManagedUserResponse, UserCreateRequest, UserUpdateRequest
from app.services.user_service import (
    InvalidRoleError,
    UserConflictError,
    UserNotFoundError,
    create_user,
    delete_user,
    get_user,
    list_users,
    serialize_managed_user,
    update_user,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def conflict_response(error: UserConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def not_found_response(error: UserNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.post("", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED)
def create_managed_user(
    payload: UserCreateRequest,
    db: DatabaseSession,
    current_user: Annotated[User, Depends(require_permission("CREATE_USERS"))],
) -> ManagedUserResponse:
    try:
        return serialize_managed_user(create_user(db, payload, current_user.id))
    except UserConflictError as exc:
        raise conflict_response(exc) from exc
    except InvalidRoleError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("", response_model=list[ManagedUserResponse])
def read_users(
    db: DatabaseSession,
    _: Annotated[User, Depends(require_permission("VIEW_USERS"))],
) -> list[ManagedUserResponse]:
    return [serialize_managed_user(user) for user in list_users(db)]


@router.get("/{user_id}", response_model=ManagedUserResponse)
def read_user(
    user_id: int,
    db: DatabaseSession,
    _: Annotated[User, Depends(require_permission("VIEW_USERS"))],
) -> ManagedUserResponse:
    try:
        return serialize_managed_user(get_user(db, user_id))
    except UserNotFoundError as exc:
        raise not_found_response(exc) from exc


@router.put("/{user_id}", response_model=ManagedUserResponse)
def update_managed_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: DatabaseSession,
    current_user: Annotated[User, Depends(require_permission("UPDATE_USERS"))],
) -> ManagedUserResponse:
    try:
        return serialize_managed_user(update_user(db, user_id, payload, current_user.id, f"/api/v1/users/{user_id}"))
    except UserNotFoundError as exc:
        raise not_found_response(exc) from exc
    except UserConflictError as exc:
        raise conflict_response(exc) from exc
    except InvalidRoleError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_managed_user(
    user_id: int,
    db: DatabaseSession,
    current_user: Annotated[User, Depends(require_permission("DELETE_USERS"))],
) -> Response:
    try:
        delete_user(db, user_id, current_user.id, f"/api/v1/users/{user_id}")
    except UserNotFoundError as exc:
        raise not_found_response(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
