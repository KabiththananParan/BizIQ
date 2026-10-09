"""Read-only deterministic security analysis API."""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.database.database import get_db
from app.database.models import User
from app.schemas.security import (
    SecurityAnalysisRequest,
    SecurityAnalysisResponse,
    SecurityAIResult,
    SecurityDashboardResponse,
    SecurityValidationRequest,
    SecurityValidationResponse,
)
from app.services.security_event_service import get_security_events
from app.services.security_analyzer import analyze_security_events
from app.services.groq_security_service import analyze_security_evidence
from app.services.security_dashboard_service import get_security_dashboard
from app.services.audit_service import record_event
from app.services.request_security_service import validate_agent_request
router=APIRouter(prefix="/api/v1/security",tags=["security"])
DB=Annotated[Session,Depends(get_db)]


@router.post("/validate-request", response_model=SecurityValidationResponse)
def validate_request(
    payload: SecurityValidationRequest,
    db: DB,
    service_token: str | None = Header(default=None, alias="X-BizIQ-Service-Token"),
) -> JSONResponse:
    """Validate independent service credentials and end-user authorization."""
    decision = validate_agent_request(db, payload, service_token)
    return JSONResponse(status_code=decision.status_code, content=decision.response.model_dump())

@router.get("/dashboard", response_model=SecurityDashboardResponse)
def security_dashboard(
    db: DB,
    _: Annotated[User, Depends(require_permission("VIEW_SECURITY_ANALYSIS"))],
    start: datetime | None = None,
    end: datetime | None = None,
) -> SecurityDashboardResponse:
    """Return aggregated security metrics, signals, and recent events for the dashboard."""
    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(hours=24)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start > end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start must be before end.")
    return get_security_dashboard(db, start, end)

@router.get("/events/{user_id}",response_model=SecurityAnalysisResponse)
def security_events(user_id:int,db:DB,_:Annotated[User,Depends(require_permission("VIEW_SECURITY_ANALYSIS"))],start:datetime|None=None,end:datetime|None=None):
    if db.get(User,user_id) is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found.")
    end=end or datetime.now(timezone.utc); start=start or end-timedelta(hours=24)
    if start>end: raise HTTPException(status_code=422,detail="start must be before end.")
    attempts,audits=get_security_events(db,user_id,start,end)
    return analyze_security_events(user_id,start,end,attempts,audits)
@router.post("/analyze",response_model=SecurityAIResult)
def analyze_with_ai(payload: SecurityAnalysisRequest, db: DB, current: Annotated[User,Depends(require_permission("RUN_SECURITY_ANALYSIS"))]):
    if db.get(User,payload.user_id) is None: raise HTTPException(status_code=404,detail="User not found.")
    end=payload.end or datetime.now(timezone.utc); start=payload.start or end-timedelta(hours=24)
    if start>end: raise HTTPException(status_code=422,detail="start must be before end.")
    attempts,audits=get_security_events(db,payload.user_id,start,end); context=analyze_security_events(payload.user_id,start,end,attempts,audits)
    result=analyze_security_evidence(context)
    record_event(db,"SECURITY_ANALYSIS_REQUESTED","SUCCESS" if result.risk_level!="UNKNOWN" else "FAILED",current.id,f"/api/v1/security/analyze",details=f"model={__import__('app.core.config',fromlist=['settings']).settings.groq_model}")
    return result
