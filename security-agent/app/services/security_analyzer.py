"""Descriptive, deterministic security signal calculations; no LLM decisions."""
from datetime import datetime
from app.core.config import settings
from app.schemas.security import SecurityAnalysisResponse, SecurityEvidence, SecuritySignal, SecuritySummary
def analyze_security_events(user_id: int, start: datetime, end: datetime, attempts, audits) -> SecurityAnalysisResponse:
    total=len(attempts); successful=sum(a.success for a in attempts); failed=total-successful; ips={a.ip_address for a in attempts if a.ip_address}; denied=sum(a.action=="ACCESS_DENIED" for a in audits); invalid=sum(a.action=="INVALID_TOKEN" for a in audits); expired=sum(a.action=="EXPIRED_TOKEN" for a in audits)
    signals=[]
    def add(kind,count,threshold,description):
        if count>=threshold: signals.append(SecuritySignal(type=kind,count=count,threshold=threshold,description=description))
    add("REPEATED_FAILED_LOGINS",failed,settings.failed_login_threshold,"Multiple failed login attempts were observed.")
    add("MULTIPLE_IP_ADDRESSES",len(ips),settings.unique_ip_threshold,"Multiple IP addresses were observed.")
    add("REPEATED_ACCESS_DENIED",denied,settings.access_denied_threshold,"Repeated access-denied events were observed.")
    if invalid: signals.append(SecuritySignal(type="INVALID_TOKEN_ACTIVITY",count=invalid,threshold=1,description="Invalid token events were observed."))
    if expired: signals.append(SecuritySignal(type="EXPIRED_TOKEN_ACTIVITY",count=expired,threshold=1,description="Expired token events were observed."))
    add("UNUSUAL_LOGIN_FREQUENCY",total,settings.login_frequency_threshold,"Frequent login attempts were observed.")
    evidence=[SecurityEvidence(event_type="LOGIN_SUCCESS" if a.success else "LOGIN_FAILED",timestamp=a.timestamp,ip_address=a.ip_address,status="SUCCESS" if a.success else "FAILED") for a in attempts]+[SecurityEvidence(event_type=a.action,timestamp=a.created_at,ip_address=a.ip_address,status=a.status) for a in audits]
    return SecurityAnalysisResponse(user_id=user_id,window_start=start,window_end=end,summary=SecuritySummary(total_login_attempts=total,successful_logins=successful,failed_logins=failed,successful_login_rate=successful/total if total else 0,failed_login_rate=failed/total if total else 0,unique_ip_addresses=len(ips),access_denied_events=denied,invalid_token_events=invalid,expired_token_events=expired,security_related_audit_events=len(audits)),signals=signals,evidence=evidence)
