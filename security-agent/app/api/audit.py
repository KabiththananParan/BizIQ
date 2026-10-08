"""Protected audit-log read endpoints."""
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.database.database import get_db
from app.database.models import User
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import get_event, get_events
router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit"])
DB = Annotated[Session, Depends(get_db)]
def serialize(event): return AuditLogResponse(id=event.id,user_id=event.user_id,action=event.action,resource=event.resource,ip_address=event.ip_address,user_agent=event.user_agent,status=event.status,details=event.details,created_at=event.created_at)
@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(db: DB, _: Annotated[User, Depends(require_permission("VIEW_AUDIT_LOGS"))], user_id: int | None = None, action: str | None = None, status_filter: str | None = None, start: datetime | None = None, end: datetime | None = None):
    return [serialize(e) for e in get_events(db,user_id,action,status_filter,start,end)]
@router.get("/{event_id}", response_model=AuditLogResponse)
def read_audit_log(event_id: int, db: DB, _: Annotated[User, Depends(require_permission("VIEW_AUDIT_LOGS"))]):
    event=get_event(db,event_id)
    if not event: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Audit log not found.")
    return serialize(event)
