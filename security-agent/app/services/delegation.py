"""Cryptographic primitives for the future BizIQ delegation profile.

This module does not authorize requests, issue tokens from an API, or consume
replay identifiers. Callers must first obtain an authorization decision and
must use a durable, atomic replay store before executing protected work.
"""

from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass
from typing import Literal

from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, ValidationError


ISSUER = "urn:biziq:security-agent"
AUDIENCES = frozenset(
    {
        "urn:biziq:agent:nlp-agent",
        "urn:biziq:agent:ir-agent",
        "urn:biziq:agent:insight-agent",
    }
)
ALGORITHM = "RS256"
TOKEN_TYPE = "biziq-delegation+jwt"
PROFILE_VERSION = 1
MAX_LIFETIME_SECONDS = 120
CLOCK_SKEW_SECONDS = 30
_SUBJECT_PATTERN = re.compile(r"^urn:biziq:security-user:[1-9][0-9]{0,18}$")


class DelegationError(ValueError):
    """Base class for safe delegation validation failures."""


class DelegationConfigurationError(DelegationError):
    """Required signing or verification configuration is missing or invalid."""


class DelegationValidationError(DelegationError):
    """An assertion failed structural or cryptographic validation."""


class DelegationClaims(BaseModel):
    """Strict v1 assertion claims. This schema conveys no authorization by itself."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    iss: Literal["urn:biziq:security-agent"]
    aud: StrictStr
    sub: StrictStr = Field(pattern=_SUBJECT_PATTERN.pattern, max_length=60)
    op: Literal[
        "QUERY_DATA",
        "RETRIEVE_DATA",
        "GENERATE_INSIGHT",
        "SECURITY_ANALYSIS",
    ]
    rid: StrictStr = Field(min_length=1, max_length=100)
    iat: StrictInt = Field(ge=0)
    nbf: StrictInt = Field(ge=0)
    exp: StrictInt = Field(gt=0)
    jti: StrictStr = Field(min_length=32, max_length=128)
    ver: Literal[1]
    scope: StrictStr | None = Field(default=None, min_length=1, max_length=200)


@dataclass(frozen=True)
class DelegationKeyRing:
    """Security-owned private key and target verification keys, indexed by kid."""

    active_kid: str | None
    private_key_pem: str | bytes | None
    public_keys: dict[str, str | bytes]


def _validate_key_ring(key_ring: DelegationKeyRing, *, signing: bool) -> None:
    if not isinstance(key_ring, DelegationKeyRing):
        raise DelegationConfigurationError("Delegation key configuration is unavailable.")
    if signing:
        if not key_ring.active_kid or not key_ring.private_key_pem:
            raise DelegationConfigurationError("Delegation signing configuration is unavailable.")
        if key_ring.active_kid not in key_ring.public_keys:
            raise DelegationConfigurationError("Active delegation key has no verification key.")
    if not key_ring.public_keys or any(not k or not key for k, key in key_ring.public_keys.items()):
        raise DelegationConfigurationError("Delegation verification keys are unavailable.")


def _validate_header(header: dict[str, object], key_ring: DelegationKeyRing) -> tuple[str, str | bytes]:
    if set(header) != {"alg", "typ", "kid"} or header.get("alg") != ALGORITHM or header.get("typ") != TOKEN_TYPE:
        raise DelegationValidationError("Unsupported delegation token profile.")
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise DelegationValidationError("Delegation key identifier is missing.")
    key = key_ring.public_keys.get(kid)
    if key is None:
        raise DelegationValidationError("Delegation key identifier is unknown.")
    return kid, key


def _sign_assertion(claims: DelegationClaims, key_ring: DelegationKeyRing) -> str:
    """Low-level signer for Security-owned code and isolated crypto tests only.

    This is deliberately not called by the request validator or any API route.
    It does not establish user identity, policy authorization, or data scope.
    """
    _validate_key_ring(key_ring, signing=True)
    assert key_ring.active_kid is not None and key_ring.private_key_pem is not None
    _validate_claim_shape(claims, expected_audience=claims.aud, expected_operation=claims.op,
                          expected_subject=claims.sub, expected_request_id=claims.rid,
                          now=int(time.time()))
    try:
        return jwt.encode(
            claims.model_dump(exclude_none=True),
            key_ring.private_key_pem,
            algorithm=ALGORITHM,
            headers={"typ": TOKEN_TYPE, "kid": key_ring.active_kid},
        )
    except Exception as exc:
        raise DelegationConfigurationError("Delegation signing failed.") from exc


def _validate_claim_shape(
    claims: DelegationClaims,
    *,
    expected_audience: str,
    expected_operation: str | None,
    expected_subject: str | None,
    expected_request_id: str | None,
    now: int,
) -> None:
    if claims.iss != ISSUER or claims.aud not in AUDIENCES or claims.aud != expected_audience:
        raise DelegationValidationError("Delegation issuer or audience is invalid.")
    if expected_operation is not None and claims.op != expected_operation:
        raise DelegationValidationError("Delegation operation does not match the request.")
    if expected_subject is not None and claims.sub != expected_subject:
        raise DelegationValidationError("Delegation subject does not match the request.")
    if expected_request_id is not None and claims.rid != expected_request_id:
        raise DelegationValidationError("Delegation request ID does not match the request.")
    if claims.nbf > claims.exp or claims.iat > claims.exp:
        raise DelegationValidationError("Delegation time claims are invalid.")
    if claims.exp - claims.iat > MAX_LIFETIME_SECONDS:
        raise DelegationValidationError("Delegation lifetime exceeds the allowed maximum.")
    if claims.iat > now + CLOCK_SKEW_SECONDS:
        raise DelegationValidationError("Delegation was issued in the future.")
    if claims.nbf > now + CLOCK_SKEW_SECONDS:
        raise DelegationValidationError("Delegation is not yet valid.")
    if claims.exp < now - CLOCK_SKEW_SECONDS:
        raise DelegationValidationError("Delegation has expired.")


def _verify_assertion(
    token: str,
    key_ring: DelegationKeyRing,
    *,
    expected_audience: str,
    expected_operation: str | None = None,
    expected_subject: str | None = None,
    expected_request_id: str | None = None,
    now: int | None = None,
) -> DelegationClaims:
    """Verify a v1 assertion. Replay consumption remains a required caller step."""
    _validate_key_ring(key_ring, signing=False)
    if expected_audience not in AUDIENCES:
        raise DelegationValidationError("Expected delegation audience is invalid.")
    try:
        header = jwt.get_unverified_header(token)
        _kid, public_key = _validate_header(header, key_ring)
        # Audience is checked as an exact single string below, after signature
        # verification; disable python-jose's broader list-audience matching.
        raw_claims = jwt.decode(
            token,
            public_key,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={
                "verify_aud": False,
                "verify_iat": False,
                "leeway": CLOCK_SKEW_SECONDS,
                "require_iss": True,
                "require_nbf": True,
                "require_exp": True,
            },
        )
        claims = DelegationClaims.model_validate(raw_claims)
    except DelegationError:
        raise
    except (JWTError, ValidationError, TypeError, ValueError) as exc:
        raise DelegationValidationError("Delegation assertion is invalid.") from exc

    # Pydantic's string field plus explicit membership rejects list audiences.
    _validate_claim_shape(
        claims,
        expected_audience=expected_audience,
        expected_operation=expected_operation,
        expected_subject=expected_subject,
        expected_request_id=expected_request_id,
        now=int(time.time()) if now is None else now,
    )
    return claims


def _new_jti() -> str:
    """Generate an unpredictable v1 replay identifier for future issuer code."""
    return secrets.token_urlsafe(32)
