"""Pydantic schemas for protected user-management APIs."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

RoleName = Literal["ADMIN", "ANALYST", "USER"]


class UserCreateRequest(BaseModel):
    """Input for an authorized user creation request."""

    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)
    role: RoleName


class UserUpdateRequest(BaseModel):
    """Fields an authorized user administrator may change."""

    username: str | None = Field(default=None, min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: RoleName | None = None
    is_active: bool | None = None


class ManagedUserResponse(BaseModel):
    """Safe user representation returned by management endpoints."""

    id: int
    username: str
    email: EmailStr
    full_name: str
    role: RoleName
    is_active: bool
    created_at: datetime
    updated_at: datetime
