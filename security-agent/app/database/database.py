"""SQLAlchemy setup for the service-local SQLite database."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy models."""


# SQLite connections are used by FastAPI request handlers running in worker threads.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for future request dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the SQLite database and any models added in later phases."""
    with engine.begin() as connection:
        # Opening the connection creates security.db when it does not exist.
        connection.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=connection)
