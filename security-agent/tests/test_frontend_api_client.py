"""Unit tests for the frontend SecurityAPIClient response and error handling."""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

import requests

from frontend.api.client import (
    APIError,
    AgentValidationError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    PermissionDeniedError,
    SecurityAPIClient,
    ServerError,
    ValidationError,
)


class FrontendAPIClientTestCase(unittest.TestCase):
    """Test suite for SecurityAPIClient error handling, status code mappings, and parameters."""

    def setUp(self) -> None:
        self.client = SecurityAPIClient(
            base_url="http://test-server:8003", timeout=5, service_token="test-service-token"
        )

    @patch("requests.post")
    def test_login_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock-token-xyz",
            "token_type": "bearer",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_resp

        result = self.client.login("analyst@example.com", "Password123!")
        self.assertEqual(result["access_token"], "mock-token-xyz")
        self.assertEqual(result["expires_in"], 3600)
        mock_post.assert_called_once_with(
            "http://test-server:8003/api/v1/auth/login",
            json={"email": "analyst@example.com", "password": "Password123!"},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=5,
        )

    @patch("requests.post")
    def test_login_invalid_credentials_raises_401(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"detail": "Invalid credentials."}
        mock_post.return_value = mock_resp

        with self.assertRaises(AuthenticationError) as ctx:
            self.client.login("unknown@example.com", "WrongPassword")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid credentials", ctx.exception.message)

    @patch("requests.get")
    def test_get_current_user_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": 1,
            "username": "analyst",
            "email": "analyst@example.com",
            "full_name": "Analyst User",
            "role": "ANALYST",
            "is_active": True,
        }
        mock_get.return_value = mock_resp

        user = self.client.get_current_user("valid-jwt-token")
        self.assertEqual(user["role"], "ANALYST")
        self.assertEqual(user["email"], "analyst@example.com")
        mock_get.assert_called_once_with(
            "http://test-server:8003/api/v1/auth/me",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer valid-jwt-token",
            },
            timeout=5,
        )

    @patch("requests.get")
    def test_get_dashboard_with_utc_parameters(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "overview": {"total_users": 10, "active_users": 9},
            "signals": {"repeated_failed_logins": 1},
            "risk_summary": {"high": 0, "medium": 0, "low": 0, "unknown": 0},
            "recent_events": [],
        }
        mock_get.return_value = mock_resp

        start = datetime(2026, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 10, 8, 23, 59, 59, tzinfo=timezone.utc)

        data = self.client.get_dashboard("valid-jwt-token", start=start, end=end)
        self.assertEqual(data["overview"]["total_users"], 10)
        self.assertEqual(data["signals"]["repeated_failed_logins"], 1)

        mock_get.assert_called_once_with(
            "http://test-server:8003/api/v1/security/dashboard",
            params={"start": start.isoformat(), "end": end.isoformat()},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer valid-jwt-token",
            },
            timeout=5,
        )

    @patch("requests.get")
    def test_get_dashboard_permission_denied_raises_403(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"detail": "You do not have permission to perform this action."}
        mock_get.return_value = mock_resp

        with self.assertRaises(PermissionDeniedError) as ctx:
            self.client.get_dashboard("user-role-token")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("permission", ctx.exception.message.lower())

    @patch("requests.post")
    def test_analyze_security_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "risk_level": "MEDIUM",
            "suspicious": True,
            "confidence": 0.85,
            "findings": [{"signal": "REPEATED_FAILED_LOGINS", "description": "5 failed logins"}],
            "evidence": ["6 failed login attempts observed"],
            "recommendation": "Review account access history.",
        }
        mock_post.return_value = mock_resp

        result = self.client.analyze_security("valid-token", user_id=42)
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertTrue(result["suspicious"])
        self.assertEqual(result["confidence"], 0.85)

    @patch("requests.post")
    def test_analyze_security_user_not_found_raises_404(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "User not found."}
        mock_post.return_value = mock_resp

        with self.assertRaises(NotFoundError) as ctx:
            self.client.analyze_security("valid-token", user_id=9999)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("requests.get")
    def test_server_error_raises_500(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"detail": "Internal Server Error"}
        mock_get.return_value = mock_resp

        with self.assertRaises(ServerError) as ctx:
            self.client.get_dashboard("token")
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("temporarily unavailable", ctx.exception.message)

    @patch("requests.get")
    def test_connection_error_handling(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        with self.assertRaises(ConnectionError) as ctx:
            self.client.get_dashboard("token")
        self.assertIn("Unable to connect", ctx.exception.message)

    @patch("requests.get")
    def test_timeout_error_handling(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with self.assertRaises(ConnectionError) as ctx:
            self.client.get_dashboard("token")
        self.assertIn("timed out", ctx.exception.message)

    @patch("requests.post")
    def test_agent_validation_success_sends_session_token_in_header_and_contract_body(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "allowed": True,
            "request_id": "agent-test-1",
            "reason": "Request authenticated and authorized.",
            "security_status": "VALID",
            "requires_ai_analysis": True,
        }
        mock_post.return_value = mock_resp

        result = self.client.validate_agent_request(
            token="session-jwt", user_id=7, request_id="agent-test-1",
            source_agent="security-agent", target_agent="security-agent",
            operation="SECURITY_ANALYSIS", metadata={"request_type": "business_query"},
        )

        self.assertTrue(result["allowed"])
        mock_post.assert_called_once_with(
            "http://test-server:8003/api/v1/security/validate-request",
            json={
                "request_id": "agent-test-1", "user_id": 7,
                "source_agent": "security-agent", "target_agent": "security-agent",
                "operation": "SECURITY_ANALYSIS", "authorization_token": "session-jwt",
                "metadata": {"request_type": "business_query"},
            },
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "Authorization": "Bearer session-jwt", "X-BizIQ-Service-Token": "test-service-token"},
            timeout=5,
        )

    @patch("requests.post")
    def test_agent_validation_401_and_403_return_safe_denial_results(self, mock_post: MagicMock) -> None:
        for status, security_status in ((401, "INVALID_TOKEN"), (403, "INSUFFICIENT_PERMISSION")):
            mock_resp = MagicMock()
            mock_resp.status_code = status
            mock_resp.json.return_value = {
                "allowed": False, "request_id": "agent-test-2", "reason": "Request denied.",
                "security_status": security_status, "requires_ai_analysis": False,
            }
            mock_post.return_value = mock_resp
            with self.assertRaises(AgentValidationError) as ctx:
                self.client.validate_agent_request(
                    "session-jwt", 7, "agent-test-2", "nlp-agent", "ir-agent", "QUERY_DATA"
                )
            self.assertEqual(ctx.exception.status_code, status)
            self.assertNotIn("session-jwt", str(ctx.exception))

    @patch("requests.post")
    def test_agent_validation_422_uses_existing_validation_error_handling(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.json.return_value = {"detail": [{"loc": ["body", "operation"], "msg": "invalid value"}]}
        mock_post.return_value = mock_resp
        with self.assertRaises(ValidationError) as ctx:
            self.client.validate_agent_request("session-jwt", 7, "agent-test-3", "nlp-agent", "ir-agent", "BAD")
        self.assertEqual(ctx.exception.status_code, 422)

    @patch("requests.post")
    def test_agent_validation_connection_error_is_safe(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError("offline")
        with self.assertRaises(ConnectionError) as ctx:
            self.client.validate_agent_request("session-jwt", 7, "agent-test-4", "nlp-agent", "ir-agent", "QUERY_DATA")
        self.assertNotIn("session-jwt", ctx.exception.message)


if __name__ == "__main__":
    unittest.main()
