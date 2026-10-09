import os
import csv
os.environ["DB_PATH"] = "test_insights.db"
os.environ["LLM_API_KEY"] = ""          # force mock mode
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
A = {"X-User-Id": "alice", "X-User-Role": "analyst"}
B = {"X-User-Id": "bob", "X-User-Role": "analyst"}


def rows():
    with open("sample_data/sales.csv") as f:
        return list(csv.DictReader(f))


def payload(intent="comparison", data=None):
    return {"question": "Which region underperformed?",
            "structured_query": {"intent": intent, "metric": "revenue", "group_by": "region", "date_column": "date"},
            "retrieved_data": [{"source": "sales.csv", "rows": rows() if data is None else data}]}


def test_generate_normal():
    r = client.post("/insights/generate", json=payload(), headers=A).json()
    assert r["stats"]["bottom_group"] == "North" and r["grounded"] and r["chart_spec"]


def test_no_data_does_not_hallucinate():
    r = client.post("/insights/generate", json=payload(data=[]), headers=A).json()
    assert r["confidence"] == "low" and "enough data" in r["answer"]


def test_prompt_injection_flagged():
    r = client.post("/insights/generate", json=payload(), headers=A).json()
    assert r["security_flags"]


def test_pii_redacted_before_llm():
    from app.privacy import redact_text
    assert "[EMAIL_REDACTED]" in redact_text("mail me at a.b@x.com")


def test_forecast():
    r = client.post("/insights/generate", json=payload("forecast"), headers=A).json()
    assert r["forecast"]["available"] and len(r["forecast"]["points"]) == 3


def test_forecast_too_little_data():
    r = client.post("/insights/generate", json=payload("forecast", rows()[:6]), headers=A).json()
    assert r["forecast"]["available"] is False


def test_viewer_cannot_generate():
    h = {"X-User-Id": "v", "X-User-Role": "viewer"}
    assert client.post("/insights/generate", json=payload(), headers=h).status_code == 403


def test_report_crud_and_isolation():
    iid = client.post("/insights/generate", json=payload(), headers=A).json()["id"]
    rid = client.post("/reports", json={"insight_id": iid, "title": "Q4"}, headers=A).json()["id"]
    assert client.get(f"/reports/{rid}", headers=A).status_code == 200
    assert client.get(f"/reports/{rid}", headers=B).status_code == 403      # other user blocked
    assert client.put(f"/reports/{rid}", json={"pinned": True}, headers=A).json()["pinned"] is True
    assert client.delete(f"/reports/{rid}", headers=A).status_code == 200
    assert client.get(f"/reports/{rid}", headers=A).status_code == 404
