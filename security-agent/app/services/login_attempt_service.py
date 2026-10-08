"""Safe persistence for successful and failed login attempts."""
from sqlalchemy.orm import Session
from app.database.models import LoginAttempt

def record_login_attempt(db: Session, email: str, success: bool, user_id: int | None = None, ip_address: str | None = None, user_agent: str | None = None, failure_reason: str | None = None) -> LoginAttempt:
    attempt = LoginAttempt(email=email, success=success, user_id=user_id, ip_address=ip_address, user_agent=user_agent, failure_reason=failure_reason)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
