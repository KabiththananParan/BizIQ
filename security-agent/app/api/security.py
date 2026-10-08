"""Read-only deterministic security analysis API."""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.database.database import get_db
from app.database.models import User
from app.schemas.security import SecurityAnalysisResponse, SecurityAnalysisRequest, SecurityAIResult
from app.services.security_event_service import get_security_events
from app.services.security_analyzer import analyze_security_events
from app.services.groq_security_service import analyze_security_evidence
from app.services.audit_service import record_event
router=APIRouter(prefix="/api/v1/security",tags=["security"])
DB=Annotated[Session,Depends(get_db)]
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
