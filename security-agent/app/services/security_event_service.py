"""UTC-window retrieval of safe security event records."""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models import AuditLog, LoginAttempt
def get_security_events(db: Session, user_id: int, start: datetime, end: datetime):
    attempts=list(db.scalars(select(LoginAttempt).where(LoginAttempt.user_id==user_id, LoginAttempt.timestamp>=start, LoginAttempt.timestamp<=end)).all())
    audits=list(db.scalars(select(AuditLog).where(AuditLog.user_id==user_id, AuditLog.created_at>=start, AuditLog.created_at<=end)).all())
    return attempts,audits
