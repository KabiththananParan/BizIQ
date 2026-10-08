"""Idempotent role and permission setup for deterministic authorization."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Permission, Role

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "ADMIN": {
        "MANAGE_USERS",
        "VIEW_USERS",
        "CREATE_USERS",
        "UPDATE_USERS",
        "DELETE_USERS",
        "VIEW_AUDIT_LOGS",
        "RUN_SECURITY_ANALYSIS",
        "VIEW_SECURITY_ANALYSIS",
        "VIEW_OWN_PROFILE",
    },
    "ANALYST": {"VIEW_USERS", "VIEW_SECURITY_ANALYSIS", "VIEW_OWN_PROFILE"},
    "USER": {"VIEW_OWN_PROFILE"},
}

PERMISSION_NAMES = frozenset().union(*ROLE_PERMISSIONS.values())
ROLE_NAMES = frozenset(ROLE_PERMISSIONS)


def seed_access_control(db: Session) -> None:
    """Create expected roles, permissions, and mappings without duplicating data."""
    existing_roles = {role.name: role for role in db.scalars(select(Role)).all()}
    existing_permissions = {permission.name: permission for permission in db.scalars(select(Permission)).all()}

    for role_name in ROLE_NAMES:
        if role_name not in existing_roles:
            role = Role(name=role_name)
            db.add(role)
            existing_roles[role_name] = role

    for permission_name in PERMISSION_NAMES:
        if permission_name not in existing_permissions:
            permission = Permission(name=permission_name)
            db.add(permission)
            existing_permissions[permission_name] = permission

    db.flush()

    for role_name, permission_names in ROLE_PERMISSIONS.items():
        role = existing_roles[role_name]
        assigned_names = {permission.name for permission in role.permissions}
        for permission_name in permission_names - assigned_names:
            role.permissions.append(existing_permissions[permission_name])

    db.commit()
