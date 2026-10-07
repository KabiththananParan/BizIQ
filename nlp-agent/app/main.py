from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="BizIQ NLP Query Agent",
    version="1.0.0",
    description="Member 1 agent: converts natural-language business questions into structured queries.",
    lifespan=lifespan,
)

app.include_router(router)
