# Security & Compliance Agent

The Security Agent backend uses SQLite through SQLAlchemy and provides
authentication, RBAC, audit logging, request validation, security analysis,
and a dashboard API.

## Run locally

From this directory, copy the example configuration, set a strong unique JWT
secret, install dependencies, and start the API:

```powershell
Copy-Item .env.example .env
# Edit .env and replace JWT_SECRET_KEY with a secure random value.
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

The application creates `security.db` automatically at startup and verifies its
connection through the health endpoint.

## Health check

```powershell
Invoke-RestMethod http://127.0.0.1:8003/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "security-compliance-agent",
  "database": "connected"
}
```

## Authentication endpoints

- `POST /api/v1/auth/register` creates a user with the fixed `USER` role.
- `POST /api/v1/auth/login` returns an HS256 bearer access token.
- `GET /api/v1/auth/me` returns the safe profile for an active bearer-token user.

Passwords are stored only as bcrypt hashes and are never included in API responses.

## Development administrator

There is no public administrator-registration endpoint. For local development,
explicitly supply credentials and run the controlled CLI:

```powershell
$env:DEV_ADMIN_USERNAME = "local-admin"
$env:DEV_ADMIN_EMAIL = "local-admin@example.com"
$env:DEV_ADMIN_PASSWORD = "replace-with-a-strong-password"
python -m app.cli.create_dev_admin
```

## Agent-to-agent security validation

`POST /api/v1/security/validate-request` is the Security Agent's REST contract
for future BizIQ agent integration. It validates the supplied end-user JWT,
RBAC permission, and request integrity before another agent processes work.
Service identity is not authenticated in this phase: `source_agent` and
`target_agent` are validated metadata until service credentials are introduced.

```json
{
  "request_id": "req-12345",
  "user_id": 12,
  "source_agent": "nlp-agent",
  "target_agent": "ir-agent",
  "operation": "SECURITY_ANALYSIS",
  "authorization_token": "<JWT>",
  "metadata": {"request_type": "business_query"}
}
```

Successful validation returns:

```json
{
  "allowed": true,
  "request_id": "req-12345",
  "reason": "Request authenticated and authorized.",
  "security_status": "VALID",
  "requires_ai_analysis": false
}
```

The operation-to-permission mapping currently contains only
`SECURITY_ANALYSIS -> RUN_SECURITY_ANALYSIS`. Requests for operations without
an existing security-model permission are denied rather than granted by
default. The JWT is used only for validation and is never written to audit
records. Every decision creates a `SECURITY_REQUEST_VALIDATED` audit event.

### Service authentication for request validation

`POST /api/v1/security/validate-request` now requires both the existing
end-user JWT in `authorization_token` and an independent
`X-BizIQ-Service-Token` HTTP header. The service identity is derived from the
configured token and must match `source_agent`. Service credentials fail closed
when no token is configured. Configure distinct local values for
`BIZIQ_SERVICE_TOKEN_NLP_AGENT`, `BIZIQ_SERVICE_TOKEN_IR_AGENT`,
`BIZIQ_SERVICE_TOKEN_INSIGHT_AGENT`, and
`BIZIQ_SERVICE_TOKEN_SECURITY_AGENT`; do not put values in source control.

The service allowlist is separate from end-user RBAC and currently permits only
`security-agent` to target `security-agent` for `SECURITY_ANALYSIS`. No business
operation is enabled. End-user `ADMIN` is currently the only seeded role with
`RUN_SECURITY_ANALYSIS`; existing role grants are unchanged. Business
permissions and service allowlist entries require explicit policy decisions.

The Streamlit validation console uses the server-side
`BIZIQ_SERVICE_TOKEN_SECURITY_AGENT` setting. It is sent only in the API header
and is not displayed in widgets or session state. For local development, the
same test credential must be configured in the backend and frontend process
environments. The end-user token remains a separate user-validation credential;
it does not authenticate the calling service.

Audit details record the request ID, verified service identity, authenticated
user ID when available, target, operation, outcome, and safe denial category.
Tokens and arbitrary request metadata are excluded. This validation endpoint
does not establish end-to-end correlation until downstream agents propagate the
request ID.

## Intended BizIQ architecture

```text
User Question -> NLP Agent -> IR Agent -> LLM Insight Agent -> Final Response

                  +---------------------------+
                  | Security Agent            |
                  | JWT validation            |
                  | RBAC                      |
                  | Request integrity          |
                  | Audit logging              |
                  | Security analysis / Groq   |
                  +---------------------------+
```

The Security Agent runs alongside this pipeline. It does not automatically
intercept the other agents today; they can integrate with the validation REST
contract in a future phase. Groq is reserved for `/api/v1/security/analyze`
and is not invoked for normal request validation.

## Phase 13B delegation foundation

`app/services/delegation.py` defines isolated v1 RS256 signing and verification
primitives. The profile uses issuer `urn:biziq:security-agent`, one exact
audience (`urn:biziq:agent:nlp-agent`, `urn:biziq:agent:ir-agent`, or
`urn:biziq:agent:insight-agent`), a namespaced Security database user ID,
operation, request ID, `iat`/`nbf`/`exp`, unique `jti`, version `1`, and
optional verified scope. The JOSE header requires `typ=biziq-delegation+jwt`,
`alg=RS256`, and a configured `kid`. Maximum lifetime is 120 seconds with 30
seconds of clock skew. A Security-owned private key signs; verifiers use
trusted public keys selected by `kid`.

These are cryptographic primitives, not an authorization endpoint. No route
calls the signer and the current validation response does not contain an
assertion. The signer does not establish user identity, permissions, an
allowlisted service tuple, or owner scope. Do not call it until those checks
are provided by an approved issuance path. The current allowlist remains only
`security-agent -> security-agent / SECURITY_ANALYSIS`, and the operation
mapping remains `SECURITY_ANALYSIS -> RUN_SECURITY_ANALYSIS`; business
operations remain disabled.

Replay protection is **not implemented**. Verification alone is not sufficient
to execute a protected operation. Every target must atomically consume
`(issuer, audience, jti)` in durable storage before execution and fail closed
if that storage is unavailable. Current persistence is service-local SQLite;
there is no shared target-side replay store. Selecting a shared durable store,
its schema/infrastructure, concurrency guarantees, and retention/cleanup
operations is a prerequisite. This phase intentionally adds no replay table,
database model, or infrastructure. Assertions must not be exposed to targets
until they independently verify the profile and enforce replay consumption.

No production delegation key environment settings are active in this phase.
The `DelegationKeyRing` must be supplied explicitly by future Security-owned
configuration; missing keys fail closed. Provision private keys outside source
control, retain old public keys through the maximum token lifetime plus skew
during rotation, and revoke a key immediately if compromised. Numeric database
IDs are only stable while the Security database identity persists; this does
not solve cross-rebuild identity stability or the missing verified
Security-user-to-IR-owner entitlement mapping.
