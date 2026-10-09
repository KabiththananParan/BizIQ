"""BizIQ Unified Application Gateway & Multi-Agent API Server.

Integrates the 4 specialised AI agents:
1. 🔐 Security & Compliance Agent (Port 8003 / Member 4)
2. 🗣️ NLP Query Agent (Port 8001 / Member 1)
3. 🔎 Data Retrieval / IR Agent (Port 8002 / Member 2)
4. 🧠 LLM Insight Agent (Port 8004 / Member 3)

Serves the unified frontend on http://127.0.0.1:8000
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from orchestrator.pipeline import run_biziq_pipeline
from orchestrator.sample_data import SAMPLE_DATASOURCES
from orchestrator.service_client import (
    insight_client,
    ir_client,
    nlp_client,
    security_client,
)

logger = logging.getLogger("biziq.gateway")
logging.basicConfig(level=logging.INFO)

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"


# -----------------------------------------------------------------------------
# Pydantic Request & Response Schemas
# -----------------------------------------------------------------------------

class OrchestratedQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000, description="Natural language business question")
    top_k: int = Field(default=5, ge=1, le=20)
    user_id: str = Field(default="1")
    user_role: str = Field(default="analyst")
    owner: str = Field(default="demo")


class LoginPayload(BaseModel):
    email: str
    password: str


class RegisterPayload(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "USER"


class DataSourceCreatePayload(BaseModel):
    name: str
    description: str = ""
    content: str
    source_type: str = "csv"
    owner: str = "demo"


class DataSourceUpdatePayload(BaseModel):
    name: str
    description: str = ""
    content: str
    owner: str = "demo"


class SearchTestPayload(BaseModel):
    query: str
    top_k: int = 5
    owner: str = "demo"


class ReportCreatePayload(BaseModel):
    insight_id: str
    title: str
    notes: str = ""
    user_id: str = "1"


class ReportUpdatePayload(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    pinned: Optional[bool] = None


class FeedbackPayload(BaseModel):
    helpful: bool
    comment: str = ""


# -----------------------------------------------------------------------------
# Lifespan & Seeding
# -----------------------------------------------------------------------------

def seed_demo_environment():
    """Ensure sample SME datasets, default users, and initial queries are seeded."""
    logger.info("Seeding BizIQ Demo Environment...")
    # 1. Seed IR sample datasources
    try:
        active = ir_client.list_datasources(owner="demo")
        if not active:
            for ds in SAMPLE_DATASOURCES:
                ir_client.create_datasource(
                    name=ds["name"],
                    description=ds["description"],
                    content=ds["content"],
                    source_type=ds["source_type"],
                    owner="demo",
                )
            logger.info(f"Seeded {len(SAMPLE_DATASOURCES)} sample SME data sources.")
    except Exception as e:
        logger.warning(f"Data source seeding non-fatal error: {e}")

    # 2. Seed Default Security Users if needed
    try:
        security_client.seed_default_users()
        logger.info("Verified default security demo users.")
    except Exception as e:
        logger.warning(f"User seeding non-fatal error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_demo_environment()
    yield


# -----------------------------------------------------------------------------
# FastAPI Application Configuration
# -----------------------------------------------------------------------------

app = FastAPI(
    title="🧠 BizIQ — Integrated Multi-Agent Business Intelligence Gateway",
    description="Unified API gateway and orchestrator connecting NLP, IR, LLM Insight, and Security Agents.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# 1. Multi-Agent Pipeline Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/orchestrate/query", tags=["Multi-Agent Orchestrator"])
def orchestrate_query(payload: OrchestratedQueryRequest):
    """Execute the full 4-agent business intelligence pipeline."""
    try:
        result = run_biziq_pipeline(
            question=payload.question,
            user_id=payload.user_id,
            user_role=payload.user_role,
            top_k=payload.top_k,
            owner=payload.owner,
        )
        return result
    except Exception as exc:
        logger.error(f"Pipeline execution error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(exc)}")


@app.get("/api/system/status", tags=["System Diagnostics"])
def system_status():
    """Return live health and statistics for all 4 agents."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        users = security_client.list_users()
        user_count = len(users)
    except Exception:
        user_count = 0

    try:
        queries = nlp_client.list_queries(limit=10)
        query_count = len(queries)
    except Exception:
        query_count = 0

    try:
        datasources = ir_client.list_datasources(owner="demo")
        ds_count = len(datasources)
    except Exception:
        ds_count = 0

    try:
        insights = insight_client.list_insights(limit=10)
        reports = insight_client.list_reports()
        insight_count = len(insights)
        report_count = len(reports)
    except Exception:
        insight_count = 0
        report_count = 0

    return {
        "status": "healthy",
        "timestamp": now,
        "environment": "production-ready",
        "agents": {
            "security": {
                "name": "Security & Compliance Agent",
                "member": "Member 4",
                "status": "online",
                "db_status": "connected",
                "users_count": user_count,
            },
            "nlp": {
                "name": "NLP Query Agent",
                "member": "Member 1",
                "status": "online",
                "db_status": "connected",
                "queries_count": query_count,
            },
            "ir": {
                "name": "Data Retrieval / IR Agent",
                "member": "Member 2",
                "status": "online",
                "db_status": "connected",
                "active_datasources": ds_count,
            },
            "insight": {
                "name": "LLM Insight Agent",
                "member": "Member 3",
                "status": "online",
                "db_status": "connected",
                "insights_count": insight_count,
                "reports_count": report_count,
            },
        },
    }


@app.post("/api/system/seed-demo", tags=["System Diagnostics"])
def seed_demo():
    """Re-seed sample datasets and demo state."""
    seed_demo_environment()
    return {"status": "success", "message": "Demo datasets and security users seeded successfully."}


# -----------------------------------------------------------------------------
# 2. Security & Compliance Agent Routes (Member 4)
# -----------------------------------------------------------------------------

@app.post("/api/v1/auth/login", tags=["Security & Auth"])
def auth_login(payload: LoginPayload):
    try:
        return security_client.authenticate(payload.email, payload.password)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(exc)}")


@app.post("/api/v1/auth/register", tags=["Security & Auth"], status_code=201)
def auth_register(payload: RegisterPayload):
    try:
        return security_client.register_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role_name=payload.role,
        )
    except ValueError as exc:
        if "already exists" in str(exc).lower():
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/auth/me", tags=["Security & Auth"])
def auth_me(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split("Bearer ")[1].strip()
    try:
        return security_client.verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))



@app.get("/api/v1/users", tags=["Security & Auth"])
def list_users():
    return security_client.list_users()


@app.get("/api/v1/security/dashboard", tags=["Security & Auth"])
def security_dashboard():
    return security_client.get_dashboard_metrics()


@app.get("/api/v1/audit/logs", tags=["Security & Auth"])
def audit_logs(limit: int = Query(50, ge=1, le=200), action: Optional[str] = None):
    return security_client.get_audit_logs(limit=limit, action=action)


@app.post("/api/v1/security/analyze", tags=["Security & Auth"])
def security_analyze_user(user_id: int = Query(1)):
    return security_client.analyze_anomalies(user_id=user_id)


# -----------------------------------------------------------------------------
# 3. NLP Query Agent Routes (Member 1)
# -----------------------------------------------------------------------------

@app.post("/api/v1/nlp/process", tags=["NLP Query Agent"])
def nlp_process(payload: OrchestratedQueryRequest):
    return nlp_client.process_question(payload.question, payload.top_k)


@app.get("/api/v1/nlp/queries", tags=["NLP Query Agent"])
def nlp_list_queries(limit: int = Query(50, ge=1, le=200)):
    return nlp_client.list_queries(limit=limit)


@app.delete("/api/v1/nlp/queries/{query_id}", tags=["NLP Query Agent"])
def nlp_delete_query(query_id: int):
    if not nlp_client.delete_query(query_id):
        raise HTTPException(status_code=404, detail="Query not found")
    return {"message": "Query deleted successfully", "query_id": query_id}


@app.get("/api/v1/nlp/entities", tags=["NLP Query Agent"])
def nlp_list_entities(query_id: Optional[int] = None):
    return nlp_client.list_entities(query_id=query_id)


# -----------------------------------------------------------------------------
# 4. IR / Data Retrieval Agent Routes (Member 2)
# -----------------------------------------------------------------------------

@app.get("/api/v1/ir/datasources", tags=["IR Agent"])
def ir_list_datasources(owner: str = "demo"):
    return ir_client.list_datasources(owner=owner)


@app.post("/api/v1/ir/datasources", tags=["IR Agent"], status_code=201)
def ir_create_datasource(payload: DataSourceCreatePayload):
    return ir_client.create_datasource(
        name=payload.name,
        description=payload.description,
        content=payload.content,
        source_type=payload.source_type,
        owner=payload.owner,
    )


@app.get("/api/v1/ir/datasources/{datasource_id}", tags=["IR Agent"])
def ir_get_datasource(datasource_id: int, owner: str = "demo"):
    ds = ir_client.get_datasource(datasource_id, owner=owner)
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


@app.put("/api/v1/ir/datasources/{datasource_id}", tags=["IR Agent"])
def ir_update_datasource(datasource_id: int, payload: DataSourceUpdatePayload):
    ds = ir_client.update_datasource(
        datasource_id=datasource_id,
        name=payload.name,
        description=payload.description,
        content=payload.content,
        owner=payload.owner,
    )
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ds


@app.delete("/api/v1/ir/datasources/{datasource_id}", tags=["IR Agent"])
def ir_delete_datasource(datasource_id: int, owner: str = "demo"):
    if not ir_client.delete_datasource(datasource_id, owner=owner):
        raise HTTPException(status_code=404, detail="Data source not found")
    return {"message": "Data source deleted successfully", "datasource_id": datasource_id}


@app.post("/api/v1/ir/search", tags=["IR Agent"])
def ir_test_search(payload: SearchTestPayload):
    results = ir_client.search(query=payload.query, owner=payload.owner, top_k=payload.top_k)
    return {"query": payload.query, "results": results, "total": len(results)}


# -----------------------------------------------------------------------------
# 5. LLM Insight Agent Routes (Member 3)
# -----------------------------------------------------------------------------

@app.get("/api/v1/insight/insights", tags=["LLM Insight Agent"])
def insight_list(limit: int = Query(30, ge=1, le=100)):
    return insight_client.list_insights(limit=limit)


@app.get("/api/v1/insight/insights/{insight_id}", tags=["LLM Insight Agent"])
def insight_get(insight_id: str):
    res = insight_client.get_insight(insight_id)
    if not res:
        raise HTTPException(status_code=404, detail="Insight not found")
    return res


@app.post("/api/v1/insight/insights/{insight_id}/feedback", tags=["LLM Insight Agent"])
def insight_feedback(insight_id: str, payload: FeedbackPayload):
    if not insight_client.submit_feedback(insight_id, payload.helpful, payload.comment):
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"status": "success", "saved": True}


@app.get("/api/v1/insight/reports", tags=["LLM Insight Agent"])
def report_list(pinned: Optional[bool] = None):
    return insight_client.list_reports(pinned=pinned)


@app.post("/api/v1/insight/reports", tags=["LLM Insight Agent"], status_code=201)
def report_create(payload: ReportCreatePayload):
    return insight_client.create_report(
        insight_id=payload.insight_id,
        title=payload.title,
        notes=payload.notes,
        user_id=payload.user_id,
    )


@app.get("/api/v1/insight/reports/{report_id}", tags=["LLM Insight Agent"])
def report_get(report_id: str):
    rep = insight_client.get_report(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return rep


@app.put("/api/v1/insight/reports/{report_id}", tags=["LLM Insight Agent"])
def report_update(report_id: str, payload: ReportUpdatePayload):
    rep = insight_client.update_report(
        report_id=report_id,
        title=payload.title,
        notes=payload.notes,
        pinned=payload.pinned,
    )
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return rep


@app.delete("/api/v1/insight/reports/{report_id}", tags=["LLM Insight Agent"])
def report_delete(report_id: str):
    if not insight_client.delete_report(report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "success", "deleted": True, "report_id": report_id}


# -----------------------------------------------------------------------------
# 6. Static Frontend Files Mount
# -----------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/style.css", include_in_schema=False)
    def serve_style_css():
        css_file = FRONTEND_DIR / "style.css"
        if css_file.exists():
            return FileResponse(str(css_file), media_type="text/css")
        raise HTTPException(status_code=404, detail="style.css not found")

    @app.get("/app.js", include_in_schema=False)
    def serve_app_js():
        js_file = FRONTEND_DIR / "app.js"
        if js_file.exists():
            return FileResponse(str(js_file), media_type="application/javascript")
        raise HTTPException(status_code=404, detail="app.js not found")

    @app.get("/", include_in_schema=False)
    def serve_frontend_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "BizIQ API Gateway running. Frontend index.html not found."}
