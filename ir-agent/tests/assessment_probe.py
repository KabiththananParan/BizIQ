from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("IR Agent security assessment: endpoint availability")
print("GET /health:", client.get("/health").status_code)
print("POST /search without token:",
      client.post("/search", json={"query": "test"}).status_code)
print("POST /search with invalid token:",
      client.post(
          "/search",
          json={"query": "test"},
          headers={"Authorization": "Bearer invalid-assessment-token"}
      ).status_code)

for label, payload in [
    ("empty query", {"query": ""}),
    ("whitespace query", {"query": "   "}),
    ("query over 500 chars", {"query": "a" * 501}),
    ("top_k zero", {"query": "test", "top_k": 0}),
    ("top_k above 20", {"query": "test", "top_k": 21}),
    ("missing query", {"top_k": 3}),
]:
    response = client.post(
        "/search",
        json=payload,
        headers={"Authorization": "Bearer demo-token-123"},
    )
    print(f"{label}: HTTP {response.status_code}")
