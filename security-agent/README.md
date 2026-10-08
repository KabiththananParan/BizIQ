# Security & Compliance Agent

The service foundation uses a local SQLite database through SQLAlchemy. It does
not yet include authentication, authorization, audit logging, or security
analysis functionality.

## Run locally

From this directory, copy the example configuration, set a strong unique JWT
secret, install dependencies, and start the API:

```powershell
Copy-Item .env.example .env
# Edit .env and replace JWT_SECRET_KEY with a secure random value.
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The application creates `security.db` automatically at startup and verifies its
connection through the health endpoint.

## Health check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
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
