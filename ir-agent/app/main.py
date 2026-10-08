"""
app/main.py
BizIQ - Data Retrieval (IR) Agent entry point.

Run from the ir-agent/ folder:   uvicorn app.main:app --reload
Docs:                            http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import datasources, search
from database.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BizIQ - Data Retrieval (IR) Agent", version="0.2.0", lifespan=lifespan)
app.include_router(datasources.router)
app.include_router(search.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "agent": "IR Agent"}
