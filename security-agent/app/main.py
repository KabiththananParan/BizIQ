"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.database.database import SessionLocal, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize the local SQLite database when the service starts."""
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Report application health and verify SQLite connectivity."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "service": settings.service_name,
                "database": "disconnected",
            },
        ) from exc

    return {
        "status": "healthy",
        "service": settings.service_name,
        "database": "connected",
    }
