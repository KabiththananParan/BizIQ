# Security & Compliance Agent

The service foundation uses a local SQLite database through SQLAlchemy. It does
not yet include authentication, authorization, audit logging, or security
analysis functionality.

## Run locally

From this directory, install dependencies and start the API:

```powershell
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
