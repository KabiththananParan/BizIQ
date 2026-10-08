"""Reusable HTTP client communicating with the FastAPI Security Agent backend."""

from datetime import datetime
from typing import Any
import requests

try:
    from frontend.utils.config import API_BASE_URL, DEFAULT_TIMEOUT_SECONDS
except ImportError:
    from utils.config import API_BASE_URL, DEFAULT_TIMEOUT_SECONDS



class APIError(Exception):
    """Base exception for API communication failures."""

    def __init__(self, message: str, status_code: int | None = None, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class AuthenticationError(APIError):
    """Raised when authentication fails or session expires (401)."""


class PermissionDeniedError(APIError):
    """Raised when the user lacks required permission (403)."""


class NotFoundError(APIError):
    """Raised when a requested resource or user is not found (404)."""


class ValidationError(APIError):
    """Raised when invalid request parameters are provided (422)."""


class ServerError(APIError):
    """Raised when backend returns an internal server error (500)."""


class ConnectionError(APIError):
    """Raised when unable to reach the FastAPI service."""


class AgentValidationError(APIError):
    """A safe denied validation decision returned by the security gateway."""

    def __init__(self, message: str, response: dict[str, Any], status_code: int):
        super().__init__(message, status_code=status_code, detail=response.get("reason"))
        self.response = response


class SecurityAPIClient:
    """Client for BizIQ Security & Compliance Agent REST APIs."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or API_BASE_URL).rstrip("/")
        self.timeout = timeout or DEFAULT_TIMEOUT_SECONDS

    def _headers(self, token: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _handle_response(self, response: requests.Response) -> Any:
        """Parse response or raise user-friendly domain exceptions."""
        if response.status_code in (200, 201):
            try:
                return response.json()
            except Exception:
                return response.text

        detail: str | None = None
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = body.get("detail")
                if isinstance(detail, list):  # Pydantic validation list
                    detail = "; ".join(f"{item.get('loc', [])}: {item.get('msg')}" for item in detail)
            else:
                detail = str(body)
        except Exception:
            detail = response.text

        if response.status_code == 401:
            raise AuthenticationError(
                detail or "Invalid credentials or session expired. Please log in again.",
                status_code=401,
                detail=detail,
            )
        elif response.status_code == 403:
            raise PermissionDeniedError(
                detail or "You do not have permission to access this security feature.",
                status_code=403,
                detail=detail,
            )
        elif response.status_code == 404:
            raise NotFoundError(
                detail or "Requested user or security resource was not found.",
                status_code=404,
                detail=detail,
            )
        elif response.status_code == 422:
            raise ValidationError(
                detail or "Invalid request parameters provided.",
                status_code=422,
                detail=detail,
            )
        elif response.status_code >= 500:
            raise ServerError(
                "Security service temporarily unavailable. Please try again later.",
                status_code=response.status_code,
                detail=detail,
            )
        else:
            raise APIError(
                detail or f"Request failed with status code {response.status_code}.",
                status_code=response.status_code,
                detail=detail,
            )

    def login(self, username_or_email: str, password: str) -> dict[str, Any]:
        """Authenticate user and obtain a JWT bearer token.

        Consumes: POST /api/v1/auth/login
        """
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {"email": username_or_email, "password": password}
        try:
            response = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.Timeout as exc:
            raise ConnectionError("Login request timed out. Please try again.") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError("Unable to connect to the Security Agent service.") from exc

    def get_current_user(self, token: str) -> dict[str, Any]:
        """Fetch current authenticated user profile and assigned role.

        Consumes: GET /api/v1/auth/me
        """
        url = f"{self.base_url}/api/v1/auth/me"
        try:
            response = requests.get(url, headers=self._headers(token), timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.Timeout as exc:
            raise ConnectionError("Session verification timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError("Unable to connect to the Security Agent service.") from exc

    def get_dashboard(
        self,
        token: str,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> dict[str, Any]:
        """Fetch aggregated security dashboard overview, signals, risk summary, and recent events.

        Consumes: GET /api/v1/security/dashboard
        """
        url = f"{self.base_url}/api/v1/security/dashboard"
        params: dict[str, str] = {}
        if start:
            params["start"] = start.isoformat() if isinstance(start, datetime) else str(start)
        if end:
            params["end"] = end.isoformat() if isinstance(end, datetime) else str(end)

        try:
            response = requests.get(url, params=params, headers=self._headers(token), timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.Timeout as exc:
            raise ConnectionError("Dashboard request timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError("Unable to connect to the Security Agent service.") from exc

    def get_security_events(
        self,
        token: str,
        user_id: int,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> dict[str, Any]:
        """Fetch deterministic security events and signals for a specific user.

        Consumes: GET /api/v1/security/events/{user_id}
        """
        url = f"{self.base_url}/api/v1/security/events/{user_id}"
        params: dict[str, str] = {}
        if start:
            params["start"] = start.isoformat() if isinstance(start, datetime) else str(start)
        if end:
            params["end"] = end.isoformat() if isinstance(end, datetime) else str(end)

        try:
            response = requests.get(url, params=params, headers=self._headers(token), timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.Timeout as exc:
            raise ConnectionError("Security events request timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError("Unable to connect to the Security Agent service.") from exc

    def analyze_security(
        self,
        token: str,
        user_id: int,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> dict[str, Any]:
        """Request backend AI security analysis on deterministic evidence for a specific user.

        Consumes: POST /api/v1/security/analyze
        """
        url = f"{self.base_url}/api/v1/security/analyze"
        payload: dict[str, Any] = {"user_id": user_id}
        if start:
            payload["start"] = start.isoformat() if isinstance(start, datetime) else str(start)
        if end:
            payload["end"] = end.isoformat() if isinstance(end, datetime) else str(end)

        try:
            response = requests.post(url, json=payload, headers=self._headers(token), timeout=self.timeout)
            return self._handle_response(response)
        except requests.exceptions.Timeout as exc:
            raise ConnectionError("AI security analysis timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError("Unable to connect to the Security Agent service.") from exc

    def validate_agent_request(
        self,
        token: str,
        user_id: int,
        request_id: str,
        source_agent: str,
        target_agent: str,
        operation: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send the current session JWT to the Phase 10 agent-validation contract.

        The backend needs the token both as a standard Bearer header and in its
        current request-body contract. This client never logs or displays it.
        """
        url = f"{self.base_url}/api/v1/security/validate-request"
        payload = {
            "request_id": request_id,
            "user_id": user_id,
            "source_agent": source_agent,
            "target_agent": target_agent,
            "operation": operation,
            "authorization_token": token,
            "metadata": metadata or {},
        }
        try:
            response = requests.post(url, json=payload, headers=self._headers(token), timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            if response.status_code in (401, 403, 404):
                body = response.json()
                if isinstance(body, dict):
                    raise AgentValidationError(
                        body.get("reason", "Request validation was denied."), body, response.status_code
                    )
            return self._handle_response(response)
        except requests.exceptions.Timeout as exc:
            raise ConnectionError("Agent validation request timed out. Please try again.") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError("Unable to connect to the Security Agent service.") from exc
