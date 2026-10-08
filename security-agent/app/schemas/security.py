"""Safe structured output for deterministic security analysis."""
from datetime import datetime
from pydantic import BaseModel
from typing import Literal
class SecuritySignal(BaseModel): type: str; count: int; threshold: int; description: str
class SecurityEvidence(BaseModel): event_type: str; timestamp: datetime; ip_address: str | None = None; status: str
class SecuritySummary(BaseModel):
    total_login_attempts: int; successful_logins: int; failed_logins: int; successful_login_rate: float; failed_login_rate: float; unique_ip_addresses: int; access_denied_events: int; invalid_token_events: int; expired_token_events: int; security_related_audit_events: int
class SecurityAnalysisResponse(BaseModel): user_id: int; window_start: datetime; window_end: datetime; summary: SecuritySummary; signals: list[SecuritySignal]; evidence: list[SecurityEvidence]
class SecurityAnalysisRequest(BaseModel): user_id: int; start: datetime | None = None; end: datetime | None = None
class SecurityAIFinding(BaseModel): signal: str; description: str
class SecurityAIResult(BaseModel): risk_level: Literal["LOW","MEDIUM","HIGH","UNKNOWN"]; suspicious: bool; confidence: float; findings: list[SecurityAIFinding]; evidence: list[str]; recommendation: str
