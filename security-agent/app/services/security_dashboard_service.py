"""Aggregated security dashboard service for system-wide security monitoring."""

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import AuditLog, LoginAttempt, User
from app.schemas.security import (
    SecurityDashboardOverview,
    SecurityDashboardRecentEvent,
    SecurityDashboardResponse,
    SecurityDashboardRiskSummary,
    SecurityDashboardSignals,
)


def get_security_dashboard(db: Session, start: datetime, end: datetime) -> SecurityDashboardResponse:
    """Aggregate security metrics, deterministic signals, and recent events across the system.

    Parameters:
        db: Active SQLAlchemy database session.
        start: UTC start timestamp of the observation window.
        end: UTC end timestamp of the observation window.

    Returns:
        SecurityDashboardResponse containing aggregated overview, signals,
        risk summary, and sanitized recent security events.

    Design Notes:
        - Overview metrics aggregate total registered users and active users across the
          entire system, while login attempts and audit event counts are scoped to the
          specified UTC [start, end] window.
        - Signal counts represent the number of distinct users who triggered each
          deterministic Phase 7 security signal within the window:
            * repeated_failed_logins: users with failed logins >= failed_login_threshold
            * multiple_ip_addresses: users with distinct login IPs >= unique_ip_threshold
            * repeated_access_denied: users with access denied events >= access_denied_threshold
            * invalid_token_activity: users with >= 1 invalid token event
            * expired_token_activity: users with >= 1 expired token event
            * unusual_login_frequency: users with total login attempts >= login_frequency_threshold
        - AI risk summary: AI security analysis (POST /api/v1/security/analyze) is performed
          on-demand and its detailed outputs are ephemeral and not persisted in a separate
          database table in this phase. Safe zero values are returned.
        - Recent events returns up to the latest 20 security audit logs in the window with
          safe fields only (no credentials, hashes, or secrets).
    """
    # 1. Global and Windowed Overview Metrics
    user_counts = db.execute(
        select(
            func.count(User.id).label("total_users"),
            func.sum(case((User.is_active.is_(True), 1), else_=0)).label("active_users"),
        )
    ).one()
    total_users = user_counts.total_users or 0
    active_users = user_counts.active_users or 0

    login_counts = db.execute(
        select(
            func.count(LoginAttempt.id).label("total_logins"),
            func.sum(case((LoginAttempt.success.is_(True), 1), else_=0)).label("successful_logins"),
            func.sum(case((LoginAttempt.success.is_(False), 1), else_=0)).label("failed_logins"),
        ).where(
            LoginAttempt.timestamp >= start,
            LoginAttempt.timestamp <= end,
        )
    ).one()
    total_login_attempts = login_counts.total_logins or 0
    successful_logins = login_counts.successful_logins or 0
    failed_logins = login_counts.failed_logins or 0

    audit_counts = db.execute(
        select(
            func.sum(case((AuditLog.action == "ACCESS_DENIED", 1), else_=0)).label("access_denied"),
            func.sum(case((AuditLog.action == "INVALID_TOKEN", 1), else_=0)).label("invalid_tokens"),
            func.sum(case((AuditLog.action == "EXPIRED_TOKEN", 1), else_=0)).label("expired_tokens"),
        ).where(
            AuditLog.created_at >= start,
            AuditLog.created_at <= end,
        )
    ).one()
    access_denied_events = audit_counts.access_denied or 0
    invalid_token_events = audit_counts.invalid_tokens or 0
    expired_token_events = audit_counts.expired_tokens or 0

    overview = SecurityDashboardOverview(
        total_users=total_users,
        active_users=active_users,
        total_login_attempts=total_login_attempts,
        successful_logins=successful_logins,
        failed_logins=failed_logins,
        access_denied_events=access_denied_events,
        invalid_token_events=invalid_token_events,
        expired_token_events=expired_token_events,
    )

    # 2. Phase 7 Deterministic Signals Aggregation (Users affected per signal)
    login_user_stats = db.execute(
        select(
            LoginAttempt.user_id,
            func.count(LoginAttempt.id).label("total_attempts"),
            func.sum(case((LoginAttempt.success.is_(False), 1), else_=0)).label("failed_attempts"),
            func.count(func.distinct(LoginAttempt.ip_address)).label("unique_ips"),
        )
        .where(
            LoginAttempt.timestamp >= start,
            LoginAttempt.timestamp <= end,
            LoginAttempt.user_id.isnot(None),
        )
        .group_by(LoginAttempt.user_id)
    ).all()

    repeated_failed_logins = sum(
        1 for row in login_user_stats if (row.failed_attempts or 0) >= settings.failed_login_threshold
    )
    multiple_ip_addresses = sum(
        1 for row in login_user_stats if (row.unique_ips or 0) >= settings.unique_ip_threshold
    )
    unusual_login_frequency = sum(
        1 for row in login_user_stats if (row.total_attempts or 0) >= settings.login_frequency_threshold
    )

    audit_user_stats = db.execute(
        select(
            AuditLog.user_id,
            func.sum(case((AuditLog.action == "ACCESS_DENIED", 1), else_=0)).label("denied_count"),
            func.sum(case((AuditLog.action == "INVALID_TOKEN", 1), else_=0)).label("invalid_count"),
            func.sum(case((AuditLog.action == "EXPIRED_TOKEN", 1), else_=0)).label("expired_count"),
        )
        .where(
            AuditLog.created_at >= start,
            AuditLog.created_at <= end,
            AuditLog.user_id.isnot(None),
        )
        .group_by(AuditLog.user_id)
    ).all()

    repeated_access_denied = sum(
        1 for row in audit_user_stats if (row.denied_count or 0) >= settings.access_denied_threshold
    )
    invalid_token_activity = sum(
        1 for row in audit_user_stats if (row.invalid_count or 0) >= 1
    )
    expired_token_activity = sum(
        1 for row in audit_user_stats if (row.expired_count or 0) >= 1
    )

    signals = SecurityDashboardSignals(
        repeated_failed_logins=repeated_failed_logins,
        multiple_ip_addresses=multiple_ip_addresses,
        repeated_access_denied=repeated_access_denied,
        invalid_token_activity=invalid_token_activity,
        expired_token_activity=expired_token_activity,
        unusual_login_frequency=unusual_login_frequency,
    )

    # 3. AI Risk Summary (Safe zero representation for unpersisted AI analyses)
    risk_summary = SecurityDashboardRiskSummary(
        high=0,
        medium=0,
        low=0,
        unknown=0,
    )

    # 4. Recent Security Events (Safe audit logs limited to 20)
    recent_logs = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.created_at >= start, AuditLog.created_at <= end)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        ).all()
    )

    recent_events = [
        SecurityDashboardRecentEvent(
            event=log.action,
            user_id=log.user_id,
            status=log.status,
            ip_address=log.ip_address,
            timestamp=log.created_at,
            details=log.details[:255] if log.details else None,
        )
        for log in recent_logs
    ]

    return SecurityDashboardResponse(
        overview=overview,
        signals=signals,
        risk_summary=risk_summary,
        recent_events=recent_events,
    )
