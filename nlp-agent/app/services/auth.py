"""Development authentication adapter.

Member 4 owns final authentication/authorization. This adapter matches the
IR Agent's current demo tokens so Member 1 can communicate with Member 2 now.
In final integration, replace/extend this with Member 4's JWT validation.
"""
from dataclasses import dataclass
from fastapi import Header, HTTPException


DEMO_USERS = {
    "demo-admin-token": ("u-admin", "admin", "admin"),
    "demo-analyst-token": ("u-analyst", "analyst", "analyst"),
    "demo-viewer-token": ("u-viewer", "viewer", "viewer"),
    "demo-token-123": ("u-analyst", "analyst", "analyst"),
}


@dataclass
class User:
    user_id: str
    username: str
    role: str


def current_user(authorization: str | None = Header(default=None)) -> User:
    """Validate the same development Bearer tokens used by Member 2."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    info = DEMO_USERS.get(token)
    if not info:
        raise HTTPException(401, "Invalid or expired token")
    return User(*info)
