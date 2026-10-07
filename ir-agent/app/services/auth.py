
"""
auth.py
Token authentication + per-user rate limiting, shared by all agents.

Tokens are read from the IR_API_TOKENS env var as comma-separated
`token:user_id` pairs, e.g. IR_API_TOKENS="abc123:alice,xyz789:bob"

If unset, a single demo token is used:
demo-token-123 -> user "demo"

Swap `_lookup_user` for a call to the Security & Compliance Agent's
/auth/validate endpoint when Member 4's service is ready.

Security features:
- Constant-time token comparison
- Generic authentication error messages
- Sliding-window rate limit
  (IR_RATE_LIMIT requests / 60s per user, default 60)
"""

import os
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

DEMO_TOKENS = "demo-token-123:demo"
_WINDOW_SECONDS = 60

# FastAPI security scheme.
# This also makes the Bearer authentication appear in Swagger UI.
security = HTTPBearer()


# -------------------------------------------------------------------
# Rate limiting state
# -------------------------------------------------------------------

_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


# -------------------------------------------------------------------
# Auth user
# -------------------------------------------------------------------

@dataclass(frozen=True)
class AuthUser:
    user_id: str


# -------------------------------------------------------------------
# Token loading
# -------------------------------------------------------------------

def _load_tokens() -> dict[str, str]:
    """
    Load API tokens from the IR_API_TOKENS environment variable.

    Expected format:
        token:user_id,token:user_id

    Example:
        abc123:alice,xyz789:bob

    If IR_API_TOKENS is not set, use the demo token.
    """

    raw = os.environ.get("IR_API_TOKENS", DEMO_TOKENS)

    tokens: dict[str, str] = {}

    for pair in raw.split(","):
        pair = pair.strip()

        if not pair or ":" not in pair:
            continue

        token, user = pair.split(":", 1)

        token = token.strip()
        user = user.strip()

        if token and user:
            tokens[token] = user

    return tokens


# -------------------------------------------------------------------
# Token validation
# -------------------------------------------------------------------

def _lookup_user(token: str) -> str | None:
    """
    Perform a constant-time comparison of the supplied token
    against every known token.
    """

    found = None

    for known, user in _load_tokens().items():
        if secrets.compare_digest(
            token.encode(),
            known.encode(),
        ):
            found = user

        # Keep checking all tokens so the timing does not reveal
        # which token matched.

    return found


# -------------------------------------------------------------------
# Rate limiting
# -------------------------------------------------------------------

def _rate_limit(user_id: str) -> None:
    """
    Apply a sliding-window rate limit per user.

    Default:
        60 requests per 60 seconds
    """

    limit = int(os.environ.get("IR_RATE_LIMIT", "60"))

    now = time.monotonic()

    with _lock:
        q = _hits[user_id]

        # Remove requests outside the current time window.
        while q and now - q[0] > _WINDOW_SECONDS:
            q.popleft()

        # Reject if the user has reached the limit.
        if len(q) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again shortly.",
            )

        q.append(now)


# -------------------------------------------------------------------
# Testing helper
# -------------------------------------------------------------------

def reset_rate_limits() -> None:
    """
    Clear all rate-limit counters.

    Used by tests.
    """

    with _lock:
        _hits.clear()


# -------------------------------------------------------------------
# FastAPI authentication dependency
# -------------------------------------------------------------------

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """
    FastAPI dependency.

    Expects:

        Authorization: Bearer <token>

    Example:

        Authorization: Bearer demo-token-123
    """

    token = credentials.credentials

    user_id = _lookup_user(token) if token else None

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _rate_limit(user_id)

    return AuthUser(user_id=user_id)

