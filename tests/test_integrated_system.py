"""End-to-End Integration Test Suite for BizIQ Multi-Agent Platform."""

import pytest
from fastapi.testclient import TestClient
from app_gateway import app, seed_demo_environment


@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    seed_demo_environment()


def test_gateway_health_and_system_status():
    """Verify that all 4 AI agents report online and operational."""
    with TestClient(app) as client:
        res = client.get("/api/system/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "agents" in data
        assert data["agents"]["nlp"]["status"] == "online"
        assert data["agents"]["ir"]["status"] == "online"
        assert data["agents"]["insight"]["status"] == "online"
        assert data["agents"]["security"]["status"] == "online"


def test_end_to_end_regional_performance_pipeline():
    """Test full 4-agent execution on regional performance query."""
    with TestClient(app) as client:
        payload = {
            "question": "Which region underperformed last quarter and why?",
            "top_k": 5,
            "user_id": "1",
            "user_role": "analyst",
            "owner": "demo",
        }
        res = client.post("/api/orchestrate/query", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["pipeline_status"] == "SUCCESS"
        assert "timings" in data
        assert "agents" in data
        assert data["agents"]["security"]["audit_recorded"] is True
        assert data["agents"]["nlp"]["intent"] in ("RANKING", "REGIONAL_ANALYSIS", "UNKNOWN")
        assert data["agents"]["ir"]["documents_ranked"] >= 1
        assert data["insight"]["grounded"] is True
        assert any(r in data["insight"]["answer"] for r in ("West", "Colombo", "Jaffna", "Kandy", "region", "lowest", "revenue"))
        assert len(data["insight"]["answer"]) > 15


def test_end_to_end_comparison_pipeline():
    """Test comparison query between Colombo and Kandy."""
    with TestClient(app) as client:
        payload = {
            "question": "Compare sales between Colombo and Kandy",
            "top_k": 5,
            "user_id": "1",
            "user_role": "analyst",
        }
        res = client.post("/api/orchestrate/query", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "Colombo" in data["insight"]["answer"]
        assert "Kandy" in data["insight"]["answer"]
        assert bool(data["insight"]["chart_spec"]) is True


def test_end_to_end_forecasting_pipeline():
    """Test time-series statistical forecasting."""
    with TestClient(app) as client:
        payload = {
            "question": "Forecast sales for next 3 months",
            "top_k": 5,
            "user_id": "1",
            "user_role": "analyst",
        }
        res = client.post("/api/orchestrate/query", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["insight"]["forecast"] is not None
        assert data["insight"]["forecast"]["available"] is True
        assert len(data["insight"]["forecast"]["points"]) == 3


def test_all_four_agents_crud_endpoints():
    """Test CRUD routes for all 4 agents."""
    with TestClient(app) as client:
        # 1. NLP
        nlp_queries = client.get("/api/v1/nlp/queries").json()
        assert isinstance(nlp_queries, list)

        # 2. IR
        datasources = client.get("/api/v1/ir/datasources").json()
        assert isinstance(datasources, list)
        assert len(datasources) >= 1

        # 3. Insight & Reports
        reports = client.get("/api/v1/insight/reports").json()
        assert isinstance(reports, list)

        # 4. Security & Audit
        logs = client.get("/api/v1/audit/logs").json()
        assert isinstance(logs, list)
        assert len(logs) >= 1

        users = client.get("/api/v1/users").json()
        assert isinstance(users, list)
        assert len(users) >= 1


def test_frontend_index_serving():
    """Verify that frontend HTML is served at the root."""
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "BizIQ" in res.text
        assert "MULTI-AGENT AI" in res.text
