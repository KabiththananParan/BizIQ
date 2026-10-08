"""Pydantic request and safe response schemas for authentication."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegistrationRequest(BaseModel):
    """Public registration input; role selection is intentionally excluded."""

    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Credentials accepted by the login endpoint."""

    # Login must also support development accounts such as ``admin@biziq.local``.
    # ``EmailStr`` deliberately rejects reserved domains (including ``.local``),
    # even though these addresses are valid identifiers in a local-only deployment.
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1, max_length=72)


class UserResponse(BaseModel):
    """The safe, non-sensitive representation of an authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    # See LoginRequest: development users may use a local-only email domain.
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: str
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    """Bearer token response returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
