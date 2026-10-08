"""Authentication HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenValidationError, create_access_token, decode_access_token
from app.database.database import get_db
from app.database.models import User
from app.schemas.auth import LoginRequest, RegistrationRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    DuplicateUserError,
    InvalidCredentialsError,
    authenticate_user,
    get_active_user_by_id,
    register_user,
    serialize_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DatabaseSession = Annotated[Session, Depends(get_db)]


def credentials_exception() -> HTTPException:
    """Return the same response for every token validation failure."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DatabaseSession) -> User:
    """Resolve the active user represented by a validated bearer token."""
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        return get_active_user_by_id(db, user_id)
    except (KeyError, TypeError, ValueError, TokenValidationError):
        raise credentials_exception()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(registration: RegistrationRequest, db: DatabaseSession) -> UserResponse:
    """Create a user with the default USER role."""
    try:
        return serialize_user(register_user(db, registration))
    except DuplicateUserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: DatabaseSession) -> TokenResponse:
    """Validate credentials and issue a time-limited bearer token."""
    try:
        user = authenticate_user(db, str(credentials.email), credentials.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.") from exc

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.name),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """Return safe information about the active bearer-token user."""
    return serialize_user(current_user)
