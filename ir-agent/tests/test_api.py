import sqlite3

from tests.conftest import ALICE, BOB

SALES = {"name": "West Sales Q3",
         "description": "Quarterly report",
         "content": "West region sales dropped 18 percent in Q3 due to a distributor losing a retail contract."}
HR = {"name": "HR Policy", "content": "Employees receive 14 days of annual leave. Remote work needs approval."}


def make(client, payload, headers=ALICE):
    r = client.post("/datasources", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- auth ----------
def test_auth_required(client):
    assert client.get("/datasources").status_code == 401
    assert client.get("/datasources", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/datasources", headers={"Authorization": "Basic x"}).status_code == 401
    assert client.get("/datasources", headers={"Authorization": "Bearer "}).status_code == 401
    assert client.get("/health").status_code == 200


def test_rate_limit(client, monkeypatch):
    monkeypatch.setenv("IR_RATE_LIMIT", "3")
    codes = [client.get("/datasources", headers=ALICE).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


# ---------- CRUD ----------
def test_crud_flow(client):
    ds = make(client, SALES)
    assert ds["status"] == "active" and "content" not in ds
    assert client.get(f"/datasources/{ds['id']}", headers=ALICE).json()["name"] == SALES["name"]
    assert len(client.get("/datasources", headers=ALICE).json()) == 1

    r = client.put(f"/datasources/{ds['id']}", json={"name": "Renamed"}, headers=ALICE)
    assert r.status_code == 200 and r.json()["name"] == "Renamed"

    assert client.delete(f"/datasources/{ds['id']}", headers=ALICE).status_code == 204
    assert client.get(f"/datasources/{ds['id']}", headers=ALICE).status_code == 404
    assert client.delete(f"/datasources/{ds['id']}", headers=ALICE).status_code == 404


def test_update_null_description_does_not_crash(client):
    ds = make(client, SALES)
    r = client.put(f"/datasources/{ds['id']}", json={"description": None}, headers=ALICE)
    assert r.status_code == 200 and r.json()["description"] == ""
    # explicit nulls on required fields are ignored, not stored
    r = client.put(f"/datasources/{ds['id']}", json={"name": None, "status": None}, headers=ALICE)
    assert r.status_code == 200 and r.json()["name"] == SALES["name"]


def test_validation(client):
    bad = [
        {"name": "", "content": "x"},
        {"name": "   ", "content": "x"},
        {"name": "n", "content": ""},
        {"name": "n"},
        {"name": "n", "content": "x" * 1_000_001},
    ]
    for payload in bad:
        assert client.post("/datasources", json=payload, headers=ALICE).status_code == 422
    ds = make(client, SALES)
    assert client.put(f"/datasources/{ds['id']}", json={"status": "hacked"}, headers=ALICE).status_code == 422
    assert client.put(f"/datasources/{ds['id']}", json={"id": 99, "owner": "bob"}, headers=ALICE).status_code == 200
    assert client.put(f"/datasources/{ds['id']}", json={"name": ""}, headers=ALICE).status_code == 422


def test_control_chars_stripped(client):
    ds = make(client, {"name": "a\x00b", "content": "hello\x07 world"})
    assert ds["name"] == "ab"


def test_sql_injection_is_inert(client):
    ds = make(client, {"name": "x'); DROP TABLE datasources;--", "content": "safe content"})
    assert client.get("/datasources", headers=ALICE).json()[0]["id"] == ds["id"]
    r = client.post("/search", json={"query": "' OR 1=1 --"}, headers=ALICE)
    assert r.status_code == 200


def test_nonexistent_404_and_bad_id(client):
    assert client.get("/datasources/999", headers=ALICE).status_code == 404
    assert client.put("/datasources/999", json={"name": "x"}, headers=ALICE).status_code == 404
    assert client.get("/datasources/abc", headers=ALICE).status_code == 422


# ---------- isolation ----------
def test_users_cannot_see_each_others_data(client):
    ds = make(client, SALES, ALICE)
    assert client.get("/datasources", headers=BOB).json() == []
    assert client.get(f"/datasources/{ds['id']}", headers=BOB).status_code == 404
    assert client.put(f"/datasources/{ds['id']}", json={"name": "x"}, headers=BOB).status_code == 404
    assert client.delete(f"/datasources/{ds['id']}", headers=BOB).status_code == 404
    r = client.post("/search", json={"query": "west region sales"}, headers=BOB)
    assert r.json()["results"] == []
    assert client.get(f"/datasources/{ds['id']}", headers=ALICE).status_code == 200


# ---------- search ----------
def test_search_ranks_relevant_first_and_explains(client):
    make(client, HR)
    sales = make(client, SALES)
    r = client.post("/search", json={"query": "why did west region sales underperform?", "top_k": 3}, headers=ALICE)
    assert r.status_code == 200
    res = r.json()["results"]
    assert res[0]["datasource_id"] == sales["id"]
    assert 0 < res[0]["score"] <= 1
    assert {"west", "region", "sales"} <= set(res[0]["matched_terms"])
    assert all(x["datasource_id"] != 0 for x in res)


def test_snippet_is_best_passage_not_first_lines(client):
    content = ("Intro paragraph about the company history. " * 3 +
               "Marketing budget was increased. " +
               "Inventory shrinkage hit warehouse three badly in October.")
    make(client, {"name": "Ops", "content": content})
    make(client, HR)
    res = client.post("/search", json={"query": "warehouse inventory shrinkage"}, headers=ALICE).json()["results"]
    assert "shrinkage" in res[0]["snippet"]


def test_stemming_matches_word_variants(client):
    make(client, SALES)
    make(client, HR)
    res = client.post("/search", json={"query": "sale dropping"}, headers=ALICE).json()["results"]
    assert res and res[0]["name"] == "West Sales Q3"


def test_search_edge_cases_never_crash(client):
    # empty corpus
    assert client.post("/search", json={"query": "anything"}, headers=ALICE).json()["results"] == []
    # single document
    make(client, SALES)
    assert client.post("/search", json={"query": "sales"}, headers=ALICE).json()["results"]
    # stop-word-only query, unknown words, punctuation, unicode
    for q in ["the and of", "zzzzqqq", "!!!???", "销售 额", "a"]:
        r = client.post("/search", json={"query": q}, headers=ALICE)
        assert r.status_code == 200 and r.json()["results"] == [], q
    # corpus consisting only of stop words
    client2_ds = make(client, {"name": "stop", "content": "the and of to"})
    assert client.post("/search", json={"query": "the"}, headers=ALICE).status_code == 200
    client.delete(f"/datasources/{client2_ds['id']}", headers=ALICE)


def test_search_input_validation(client):
    for payload in [{"query": ""}, {"query": "   "}, {"query": "x" * 501},
                    {"query": "ok", "top_k": 0}, {"query": "ok", "top_k": 21}, {}]:
        assert client.post("/search", json=payload, headers=ALICE).status_code == 422, payload


def test_top_k_respected(client):
    for i in range(5):
        make(client, {"name": f"d{i}", "content": f"revenue report number {i} revenue"})
    res = client.post("/search", json={"query": "revenue", "top_k": 2}, headers=ALICE).json()["results"]
    assert len(res) == 2


def test_cache_invalidation(client):
    ds = make(client, SALES)
    q = {"query": "distributor retail contract"}
    assert client.post("/search", json=q, headers=ALICE).json()["results"]
    # update content -> index must change
    client.put(f"/datasources/{ds['id']}", json={"content": "Totally different text about payroll."}, headers=ALICE)
    assert client.post("/search", json=q, headers=ALICE).json()["results"] == []
    assert client.post("/search", json={"query": "payroll"}, headers=ALICE).json()["results"]
    # retire -> excluded; reactivate -> included
    client.put(f"/datasources/{ds['id']}", json={"status": "retired"}, headers=ALICE)
    assert client.post("/search", json={"query": "payroll"}, headers=ALICE).json()["results"] == []
    client.put(f"/datasources/{ds['id']}", json={"status": "active"}, headers=ALICE)
    assert client.post("/search", json={"query": "payroll"}, headers=ALICE).json()["results"]
    # delete -> gone
    client.delete(f"/datasources/{ds['id']}", headers=ALICE)
    assert client.post("/search", json={"query": "payroll"}, headers=ALICE).json()["results"] == []


def test_cache_correct_across_processes(client, tmp_path):
    """Simulate another worker modifying the DB directly: fingerprint must catch it."""
    ds = make(client, SALES)
    assert client.post("/search", json={"query": "distributor"}, headers=ALICE).json()["results"]
    import os
    conn = sqlite3.connect(os.environ["IR_DB_PATH"])
    conn.execute("UPDATE datasources SET content='payroll only', updated_at='2999-01-01' WHERE id=?", (ds["id"],))
    conn.commit(); conn.close()
    assert client.post("/search", json={"query": "distributor"}, headers=ALICE).json()["results"] == []


def test_migrates_old_database(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE datasources (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        description TEXT, content TEXT NOT NULL, source_type TEXT DEFAULT 'text',
        status TEXT DEFAULT 'active', uploaded_at TEXT DEFAULT (datetime('now')))""")
    conn.execute("INSERT INTO datasources (name, description, content) VALUES ('old', NULL, 'legacy sales data')")
    conn.commit(); conn.close()
    monkeypatch.setenv("IR_DB_PATH", str(path))
    monkeypatch.setenv("IR_API_TOKENS", "tok-demo:demo")
    from database import db as database
    database.init_db()
    database.init_db()  # idempotent
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        h = {"Authorization": "Bearer tok-demo"}
        items = c.get("/datasources", headers=h).json()
        assert items[0]["name"] == "old" and items[0]["description"] == ""
        assert c.post("/search", json={"query": "legacy"}, headers=h).json()["results"]
