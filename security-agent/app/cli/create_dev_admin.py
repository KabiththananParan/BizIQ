"""Create a development administrator only when explicit credentials are supplied."""

import os

from sqlalchemy import or_, select

from app.core.security import hash_password
from app.database.database import SessionLocal, init_db
from app.database.models import Role, User


def required_environment(name: str) -> str:
    """Read a non-empty explicit development-admin setting."""
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} must be set to create a development administrator.")
    return value


def main() -> None:
    """Create one ADMIN account without exposing a public provisioning endpoint."""
    username = required_environment("DEV_ADMIN_USERNAME")
    email = required_environment("DEV_ADMIN_EMAIL")
    password = required_environment("DEV_ADMIN_PASSWORD")
    full_name = os.getenv("DEV_ADMIN_FULL_NAME", username)

    if len(password) < 8 or len(password) > 72:
        raise SystemExit("DEV_ADMIN_PASSWORD must be between 8 and 72 characters.")

    init_db()
    with SessionLocal() as db:
        existing_user = db.scalar(select(User).where(or_(User.username == username, User.email == email)))
        if existing_user is not None:
            raise SystemExit("An account with that username or email already exists.")

        admin_role = db.scalar(select(Role).where(Role.name == "ADMIN"))
        if admin_role is None:
            raise SystemExit("The ADMIN role is unavailable after access-control initialization.")

        db.add(
            User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role=admin_role,
            )
        )
        db.commit()

    print("Development administrator created.")


if __name__ == "__main__":
    main()
