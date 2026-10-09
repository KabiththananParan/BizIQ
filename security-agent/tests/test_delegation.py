"""Isolated tests for the v1 delegation cryptographic profile."""

import base64
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from app.services.delegation import (
    ALGORITHM,
    AUDIENCES,
    ISSUER,
    MAX_LIFETIME_SECONDS,
    TOKEN_TYPE,
    DelegationClaims,
    DelegationConfigurationError,
    DelegationKeyRing,
    DelegationValidationError,
    _sign_assertion,
    _verify_assertion,
)


def _key_pair() -> tuple[str, str]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def _raw_token(private_key: str, *, claims: dict | None = None, headers: dict | None = None,
               algorithm: str = ALGORITHM) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "iss": ISSUER,
        "aud": "urn:biziq:agent:ir-agent",
        "sub": "urn:biziq:security-user:42",
        "op": "RETRIEVE_DATA",
        "rid": "request-123",
        "iat": now,
        "nbf": now,
        "exp": now + 60,
        "jti": "jti-test-" + "x" * 32,
        "ver": 1,
    }
    payload.update(claims or {})
    token_headers = {"typ": TOKEN_TYPE, "kid": "key-1"}
    token_headers.update(headers or {})
    return jwt.encode(payload, private_key, algorithm=algorithm, headers=token_headers)


class DelegationProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private, self.public = _key_pair()
        self.ring = DelegationKeyRing("key-1", self.private, {"key-1": self.public})

    def _claims(self, **overrides: object) -> DelegationClaims:
        now = int(datetime.now(timezone.utc).timestamp())
        values: dict[str, object] = {
            "iss": ISSUER,
            "aud": "urn:biziq:agent:ir-agent",
            "sub": "urn:biziq:security-user:42",
            "op": "RETRIEVE_DATA",
            "rid": "request-123",
            "iat": now,
            "nbf": now,
            "exp": now + 60,
            "jti": "jti-test-" + "x" * 32,
            "ver": 1,
        }
        values.update(overrides)
        return DelegationClaims.model_validate(values)

    def _verify(self, token: str, **kwargs: object) -> DelegationClaims:
        defaults = {
            "expected_audience": "urn:biziq:agent:ir-agent",
            "expected_operation": "RETRIEVE_DATA",
            "expected_subject": "urn:biziq:security-user:42",
            "expected_request_id": "request-123",
        }
        defaults.update(kwargs)
        return _verify_assertion(token, self.ring, **defaults)

    def test_valid_rs256_assertion_signs_and_verifies(self) -> None:
        token = _sign_assertion(self._claims(), self.ring)
        verified = self._verify(token)
        self.assertEqual(verified.sub, "urn:biziq:security-user:42")
        self.assertEqual(verified.aud, "urn:biziq:agent:ir-agent")

    def test_tampered_payload_or_signature_is_rejected(self) -> None:
        token = _sign_assertion(self._claims(), self.ring)
        header, payload, signature = token.split(".")
        tampered_payload = base64.urlsafe_b64encode(b'{"sub":"attacker"}').decode().rstrip("=")
        for candidate in (f"{header}.{tampered_payload}.{signature}", f"{header}.{payload}.AAAA"):
            with self.subTest(candidate=candidate[:24]), self.assertRaises(DelegationValidationError):
                self._verify(candidate)

    def test_wrong_issuer_audience_type_version_and_unknown_kid_are_rejected(self) -> None:
        cases = [
            ("issuer", {"iss": "urn:other:issuer"}, {}),
            ("audience", {"aud": "urn:biziq:agent:nlp-agent"}, {}),
            ("type", {}, {"typ": "JWT"}),
            ("kid", {}, {"kid": "unknown-key"}),
            ("version", {"ver": 2}, {}),
        ]
        for name, claims, headers in cases:
            with self.subTest(name=name), self.assertRaises(DelegationValidationError):
                self._verify(_raw_token(self.private, claims=claims, headers=headers))

    def test_audience_must_be_one_exact_configured_target(self) -> None:
        token = _raw_token(self.private, claims={"aud": ["urn:biziq:agent:ir-agent"]})
        with self.assertRaises(DelegationValidationError):
            self._verify(token)
        with self.assertRaises(DelegationValidationError):
            self._verify(_sign_assertion(self._claims(), self.ring), expected_audience="urn:other")
        self.assertEqual(len(AUDIENCES), 3)

    def test_none_and_symmetric_algorithms_are_rejected(self) -> None:
        none_header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": TOKEN_TYPE, "kid": "key-1"}).encode()
        ).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"iss": ISSUER}).encode()).decode().rstrip("=")
        none_token = f"{none_header}.{payload}."
        symmetric_token = _raw_token("symmetric-test-secret-not-a-real-credential", algorithm="HS256")
        for token in (none_token, symmetric_token):
            with self.subTest(token=token[:16]), self.assertRaises(DelegationValidationError):
                self._verify(token)

    def test_expired_not_yet_valid_and_excessive_lifetime_are_rejected(self) -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        cases = [
            {"iat": now - 200, "nbf": now - 200, "exp": now - 100},
            {"iat": now, "nbf": now + 90, "exp": now + 100},
            {"iat": now, "nbf": now, "exp": now + MAX_LIFETIME_SECONDS + 1},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(DelegationValidationError):
                self._verify(_raw_token(self.private, claims=overrides))

    def test_operation_subject_and_request_id_mismatch_are_rejected(self) -> None:
        token = _sign_assertion(self._claims(), self.ring)
        for kwargs in (
            {"expected_operation": "QUERY_DATA"},
            {"expected_subject": "urn:biziq:security-user:43"},
            {"expected_request_id": "other-request"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(DelegationValidationError):
                self._verify(token, **kwargs)

    def test_missing_or_invalid_signing_and_verification_configuration_fails_closed(self) -> None:
        with self.assertRaises(DelegationConfigurationError):
            _sign_assertion(self._claims(), DelegationKeyRing(None, None, {}))
        invalid_ring = DelegationKeyRing("broken", "not a private key", {"broken": self.public})
        with self.assertRaises(DelegationConfigurationError) as caught:
            _sign_assertion(self._claims(), invalid_ring)
        self.assertNotIn("not a private key", str(caught.exception))
        with self.assertRaises(DelegationConfigurationError):
            _verify_assertion("not-a-token", DelegationKeyRing(None, None, {}),
                              expected_audience="urn:biziq:agent:ir-agent")

    def test_key_rotation_accepts_configured_old_key_then_rejects_retired_key(self) -> None:
        old_private, old_public = _key_pair()
        old_ring = DelegationKeyRing("old", old_private, {"old": old_public})
        token = _raw_token(old_private, headers={"kid": "old"})
        rotation_ring = DelegationKeyRing("new", self.private, {"old": old_public, "new": self.public})
        claims = _verify_assertion(token, rotation_ring, expected_audience="urn:biziq:agent:ir-agent")
        self.assertEqual(claims.aud, "urn:biziq:agent:ir-agent")
        retired_ring = DelegationKeyRing("new", self.private, {"new": self.public})
        with self.assertRaises(DelegationValidationError):
            _verify_assertion(token, retired_ring, expected_audience="urn:biziq:agent:ir-agent")
        self.assertEqual(old_ring.active_kid, "old")


if __name__ == "__main__":
    unittest.main()
