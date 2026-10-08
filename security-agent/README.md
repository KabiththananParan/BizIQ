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
