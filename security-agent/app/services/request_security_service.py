"""Independent service authentication and end-user authorization."""

import json
import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenValidationError, decode_access_token
from app.database.models import User
from app.schemas.security import SecurityValidationRequest, SecurityValidationResponse
from app.services.audit_service import record_event
from app.services.auth_service import InvalidCredentialsError, get_active_user_by_id


# User authorization remains tied to current database-backed role permissions.
OPERATION_PERMISSION: dict[str, str] = {
    "SECURITY_ANALYSIS": "RUN_SECURITY_ANALYSIS",
}

# Service authorization is a separate, explicit allowlist. No business operation
# is enabled here; those grants require a later policy decision.
SERVICE_OPERATION_ALLOWLIST: dict[str, dict[str, set[str]]] = {
    "security-agent": {"security-agent": {"SECURITY_ANALYSIS"}},
}


@dataclass(frozen=True)
class RequestValidationDecision:
    response: SecurityValidationResponse
    status_code: int


def _authenticate_service(service_token: str | None) -> tuple[str | None, str | None]:
    """Return verified identity, or a safe failure status; compare every token."""
    configured = {
        name: token
        for name, token in settings.service_tokens.items()
        if isinstance(token, str) and token.strip()
    }
    if not configured:
        return None, "SERVICE_AUTH_UNAVAILABLE"
    if not service_token:
        return None, "INVALID_SERVICE_CREDENTIAL"

    matches: list[str] = []
    supplied = service_token.encode("utf-8")
    for name, expected in configured.items():
        if secrets.compare_digest(supplied, expected.encode("utf-8")):
            matches.append(name)
    # Duplicate credentials are ambiguous and therefore never authenticate.
    return (matches[0], None) if len(matches) == 1 else (None, "INVALID_SERVICE_CREDENTIAL")


def _audit(
    db: Session,
    payload: SecurityValidationRequest,
    authenticated_user_id: int | None,
    verified_service_identity: str | None,
    target_service: str,
    operation: str,
    outcome: str,
    denial_category: str | None,
) -> bool:
    """Write allowlisted metadata only; never persist tokens or arbitrary metadata."""
    details = json.dumps(
        {
            "request_id": payload.request_id,
            "verified_service_identity": verified_service_identity,
            "authenticated_user_id": authenticated_user_id,
            "target_service": target_service,
            "operation": operation,
            "validation_outcome": outcome,
            "denial_category": denial_category,
        },
        separators=(",", ":"),
    )
    try:
        record_event(
            db,
            "SECURITY_REQUEST_VALIDATED",
            "SUCCESS" if outcome == "ALLOWED" else "FAILED",
            authenticated_user_id,
            "/api/v1/security/validate-request",
            details=details,
        )
        return True
    except Exception:
        # Audit outages fail closed. A denial remains a denial; a would-be allow
        # is converted to a safe 503 and is never returned as authorized.
        db.rollback()
        return False


def _decision(
    payload: SecurityValidationRequest,
    allowed: bool,
    reason: str,
    security_status: str,
    http_status: int,
) -> RequestValidationDecision:
    return RequestValidationDecision(
        SecurityValidationResponse(
            allowed=allowed,
            request_id=payload.request_id,
            reason=reason,
            security_status=security_status,
            requires_ai_analysis=allowed and payload.operation == "SECURITY_ANALYSIS",
        ),
        http_status,
    )


def _deny(
    db: Session,
    payload: SecurityValidationRequest,
    authenticated_user_id: int | None,
    verified_service_identity: str | None,
    reason: str,
    security_status: str,
    http_status: int,
    denial_category: str,
) -> RequestValidationDecision:
    _audit(
        db,
        payload,
        authenticated_user_id,
        verified_service_identity,
        payload.target_agent,
        payload.operation,
        "DENIED",
        denial_category,
    )
    return _decision(payload, False, reason, security_status, http_status)


def _token_value(value: str | None) -> str:
    """Accept the existing raw JWT or conventional Bearer-prefixed body value."""
    if not value:
        return ""
    prefix = "Bearer "
    return value[len(prefix):].strip() if value.startswith(prefix) else value.strip()


def validate_agent_request(
    db: Session,
    payload: SecurityValidationRequest,
    service_token: str | None,
) -> RequestValidationDecision:
    """Require verified service identity and existing user RBAC to both pass."""
    service_identity, service_auth_error = _authenticate_service(service_token)
    if service_auth_error:
        unavailable = service_auth_error == "SERVICE_AUTH_UNAVAILABLE"
        return _deny(
            db, payload, None, None,
            "Service authentication is not configured." if unavailable else "Service authentication failed.",
            service_auth_error,
            503 if unavailable else 401,
            service_auth_error,
        )

    authenticated_user: User | None = None
    try:
        claims = decode_access_token(_token_value(payload.authorization_token))
        authenticated_user = get_active_user_by_id(db, int(claims["sub"]))
    except (KeyError, TypeError, ValueError, TokenValidationError, InvalidCredentialsError):
        return _deny(
            db, payload, None, service_identity, "Request authentication failed.",
            "INVALID_TOKEN", 401, "INVALID_USER_TOKEN",
        )

    if service_identity != payload.source_agent:
        return _deny(
            db, payload, authenticated_user.id, service_identity,
            "Claimed source does not match the authenticated service.",
            "DENIED", 403, "SERVICE_IDENTITY_MISMATCH",
        )

    requested_user = db.get(User, payload.user_id)
    if requested_user is None:
        return _deny(
            db, payload, authenticated_user.id, service_identity,
            "Requested user was not found.", "INVALID_REQUEST", 404, "USER_NOT_FOUND",
        )
    if authenticated_user.id != payload.user_id:
        return _deny(
            db, payload, authenticated_user.id, service_identity,
            "Authenticated user does not match the request user.",
            "DENIED", 403, "USER_ID_MISMATCH",
        )

    allowed_targets = SERVICE_OPERATION_ALLOWLIST.get(service_identity, {})
    allowed_operations = allowed_targets.get(payload.target_agent, set())
    if payload.operation not in allowed_operations:
        return _deny(
            db, payload, authenticated_user.id, service_identity,
            "Authenticated service is not authorized for this target and operation.",
            "SERVICE_NOT_AUTHORIZED", 403, "SERVICE_OPERATION_NOT_ALLOWED",
        )

    required_permission = OPERATION_PERMISSION.get(payload.operation)
    permissions = {permission.name for permission in authenticated_user.role.permissions}
    if required_permission is None:
        return _deny(
            db, payload, authenticated_user.id, service_identity,
            "No permission mapping is configured for this operation.",
            "INSUFFICIENT_PERMISSION", 403, "UNMAPPED_USER_OPERATION",
        )
    if required_permission not in permissions:
        return _deny(
            db, payload, authenticated_user.id, service_identity,
            "Authenticated user lacks permission for this operation.",
            "INSUFFICIENT_PERMISSION", 403, "USER_PERMISSION_DENIED",
        )

    audited = _audit(
        db, payload, authenticated_user.id, service_identity, payload.target_agent,
        payload.operation, "ALLOWED", None,
    )
    if not audited:
        return _decision(
            payload, False, "Request could not be validated.", "DENIED", 503
        )
    return _decision(payload, True, "Request authenticated and authorized.", "VALID", 200)
