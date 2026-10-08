"""Safe structured output for deterministic security analysis."""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal
class SecuritySignal(BaseModel): type: str; count: int; threshold: int; description: str
class SecurityEvidence(BaseModel): event_type: str; timestamp: datetime; ip_address: str | None = None; status: str
class SecuritySummary(BaseModel):
    total_login_attempts: int; successful_logins: int; failed_logins: int; successful_login_rate: float; failed_login_rate: float; unique_ip_addresses: int; access_denied_events: int; invalid_token_events: int; expired_token_events: int; security_related_audit_events: int
class SecurityAnalysisResponse(BaseModel): user_id: int; window_start: datetime; window_end: datetime; summary: SecuritySummary; signals: list[SecuritySignal]; evidence: list[SecurityEvidence]
class SecurityAnalysisRequest(BaseModel): user_id: int; start: datetime | None = None; end: datetime | None = None
class SecurityAIFinding(BaseModel): signal: str; description: str
class SecurityAIResult(BaseModel): risk_level: Literal["LOW","MEDIUM","HIGH","UNKNOWN"]; suspicious: bool; confidence: float; findings: list[SecurityAIFinding]; evidence: list[str]; recommendation: str

class SecurityDashboardOverview(BaseModel):
    total_users: int
    active_users: int
    total_login_attempts: int
    successful_logins: int
    failed_logins: int
    access_denied_events: int
    invalid_token_events: int
    expired_token_events: int

class SecurityDashboardSignals(BaseModel):
    repeated_failed_logins: int
    multiple_ip_addresses: int
    repeated_access_denied: int
    invalid_token_activity: int
    expired_token_activity: int
    unusual_login_frequency: int

class SecurityDashboardRiskSummary(BaseModel):
    high: int
    medium: int
    low: int
    unknown: int

class SecurityDashboardRecentEvent(BaseModel):
    event: str
    user_id: int | None = None
    status: str
    ip_address: str | None = None
    timestamp: datetime
    details: str | None = None

class SecurityDashboardResponse(BaseModel):
    overview: SecurityDashboardOverview
    signals: SecurityDashboardSignals
    risk_summary: SecurityDashboardRiskSummary
    recent_events: list[SecurityDashboardRecentEvent]


AgentName = Literal["nlp-agent", "ir-agent", "insight-agent", "security-agent"]
SecurityOperation = Literal["QUERY_DATA", "RETRIEVE_DATA", "GENERATE_INSIGHT", "SECURITY_ANALYSIS"]
SecurityValidationStatus = Literal[
    "VALID", "DENIED", "INVALID_TOKEN", "INSUFFICIENT_PERMISSION", "INVALID_REQUEST"
]


class SecurityValidationRequest(BaseModel):
    """Service-to-service request metadata and the end-user token to validate."""

    request_id: str = Field(min_length=1, max_length=100)
    user_id: int = Field(gt=0)
    source_agent: AgentName
    target_agent: AgentName
    operation: SecurityOperation
    # Optional at schema level so missing credentials receive the API's 401
    # authentication response instead of a generic schema-validation response.
    authorization_token: str | None = Field(default=None, max_length=8192)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_id")
    @classmethod
    def request_id_must_not_be_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must not be blank.")
        return value


class SecurityValidationResponse(BaseModel):
    """Safe deterministic decision returned to another BizIQ agent."""

    allowed: bool
    request_id: str
    reason: str
    security_status: SecurityValidationStatus
    requires_ai_analysis: bool = False
