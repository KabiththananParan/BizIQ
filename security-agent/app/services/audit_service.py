"""Safe persistence and retrieval of audit events."""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models import AuditLog

def record_event(db: Session, action: str, status: str, user_id: int | None = None, resource: str | None = None, ip_address: str | None = None, user_agent: str | None = None, details: str | None = None) -> AuditLog:
    """Persist a non-sensitive audit event."""
    event = AuditLog(action=action, status=status, user_id=user_id, resource=resource, ip_address=ip_address, user_agent=user_agent, details=details)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def get_events(db: Session, user_id: int | None = None, action: str | None = None, status: str | None = None, start: datetime | None = None, end: datetime | None = None) -> list[AuditLog]:
    query = select(AuditLog)
    if user_id is not None: query = query.where(AuditLog.user_id == user_id)
    if action: query = query.where(AuditLog.action == action)
    if status: query = query.where(AuditLog.status == status)
    if start: query = query.where(AuditLog.created_at >= start)
    if end: query = query.where(AuditLog.created_at <= end)
    return list(db.scalars(query.order_by(AuditLog.created_at.desc())).all())

def get_event(db: Session, event_id: int) -> AuditLog | None:
    return db.get(AuditLog, event_id)
