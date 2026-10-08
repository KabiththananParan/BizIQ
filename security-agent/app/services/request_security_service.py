"""Deterministic validation for requests exchanged between BizIQ agents."""

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.security import TokenValidationError, decode_access_token
from app.database.models import User
from app.schemas.security import SecurityValidationRequest, SecurityValidationResponse
from app.services.audit_service import record_event
from app.services.auth_service import InvalidCredentialsError, get_active_user_by_id


# Only SECURITY_ANALYSIS has an equivalent permission in the current security model.
# Other operations remain denied until their owning agents define a permission contract.
OPERATION_PERMISSION: dict[str, str] = {
    "SECURITY_ANALYSIS": "RUN_SECURITY_ANALYSIS",
}


@dataclass(frozen=True)
class RequestValidationDecision:
    """A response body paired with its HTTP status for the API layer."""

    response: SecurityValidationResponse
    status_code: int


def _audit(
    db: Session,
    payload: SecurityValidationRequest,
    authenticated_user_id: int | None,
    allowed: bool,
    reason: str,
) -> None:
    """Persist safe validation context; deliberately exclude tokens and metadata."""
    details = json.dumps(
        {
            "request_id": payload.request_id,
            "authenticated_user_id": authenticated_user_id,
            "source_agent": payload.source_agent,
            "target_agent": payload.target_agent,
            "operation": payload.operation,
            "validation_result": "ALLOWED" if allowed else "DENIED",
            "reason": reason,
        },
        separators=(",", ":"),
    )
    record_event(
        db,
        "SECURITY_REQUEST_VALIDATED",
        "SUCCESS" if allowed else "FAILED",
        authenticated_user_id,
        "/api/v1/security/validate-request",
        details=details,
    )


def _deny(
    db: Session,
    payload: SecurityValidationRequest,
    authenticated_user_id: int | None,
    reason: str,
    security_status: str,
    http_status: int,
) -> RequestValidationDecision:
    _audit(db, payload, authenticated_user_id, False, reason)
    return RequestValidationDecision(
        SecurityValidationResponse(
            allowed=False,
            request_id=payload.request_id,
            reason=reason,
            security_status=security_status,
        ),
        http_status,
    )


def _token_value(value: str | None) -> str:
    """Accept either a raw JWT or the conventional Bearer-prefixed value."""
    if not value:
        return ""
    prefix = "Bearer "
    return value[len(prefix):].strip() if value.startswith(prefix) else value.strip()


def validate_agent_request(db: Session, payload: SecurityValidationRequest) -> RequestValidationDecision:
    """Authenticate, authorize, validate integrity, and audit an inter-agent request."""
    authenticated_user: User | None = None
    try:
        claims = decode_access_token(_token_value(payload.authorization_token))
        authenticated_user = get_active_user_by_id(db, int(claims["sub"]))
    except (KeyError, TypeError, ValueError, TokenValidationError, InvalidCredentialsError):
        return _deny(
            db,
            payload,
            None,
            "Request authentication failed.",
            "INVALID_TOKEN",
            401,
        )

    requested_user = db.get(User, payload.user_id)
    if requested_user is None:
        return _deny(
            db,
            payload,
            authenticated_user.id,
            "Requested user was not found.",
            "INVALID_REQUEST",
            404,
        )
    if authenticated_user.id != payload.user_id:
        return _deny(
            db,
            payload,
            authenticated_user.id,
            "Authenticated user does not match the request user.",
            "DENIED",
            403,
        )

    required_permission = OPERATION_PERMISSION.get(payload.operation)
    permissions = {permission.name for permission in authenticated_user.role.permissions}
    if required_permission is None or required_permission not in permissions:
        reason = (
            "No permission mapping is configured for this operation."
            if required_permission is None
            else "Authenticated user lacks permission for this operation."
        )
        return _deny(
            db,
            payload,
            authenticated_user.id,
            reason,
            "INSUFFICIENT_PERMISSION",
            403,
        )

    reason = "Request authenticated and authorized."
    _audit(db, payload, authenticated_user.id, True, reason)
    return RequestValidationDecision(
        SecurityValidationResponse(
            allowed=True,
            request_id=payload.request_id,
            reason=reason,
            security_status="VALID",
            requires_ai_analysis=payload.operation == "SECURITY_ANALYSIS",
        ),
        200,
    )
