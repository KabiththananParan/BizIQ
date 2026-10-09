"""Auth stub. Member 4 issues JWTs; we only validate them (shared secret) and read id + role.
In DEV_AUTH mode you can fake a user with X-User-Id / X-User-Role headers."""
import jwt
from dataclasses import dataclass
from fastapi import Header, HTTPException
from .config import JWT_SECRET, DEV_AUTH


@dataclass
class User:
    id: str
    role: str  # admin | manager | analyst | viewer


def get_current_user(authorization: str | None = Header(None),
                     x_user_id: str | None = Header(None),
                     x_user_role: str | None = Header(None)) -> User:
    if JWT_SECRET and authorization and authorization.startswith("Bearer "):
        try:
            data = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
            return User(id=str(data["sub"]), role=data.get("role", "viewer"))
        except jwt.PyJWTError:
            raise HTTPException(401, "Invalid or expired token")
    if DEV_AUTH:
        return User(id=x_user_id or "dev-user", role=x_user_role or "analyst")
    raise HTTPException(401, "Authentication required")


def require_role(user: User, allowed: set[str]):
    if user.role not in allowed:
        raise HTTPException(403, f"Role '{user.role}' is not allowed to do this")


def can_access(user: User, owner_id: str) -> bool:
    return user.id == owner_id or user.role in {"admin", "manager"}
