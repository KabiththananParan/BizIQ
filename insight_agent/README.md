# BizIQ - LLM Insight Agent (Member 3)

Turns retrieved business data + a structured query into an explainable insight, chart and forecast.

## Setup
```
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # add LLM_API_KEY (optional - mock mode works without)
uvicorn app.main:app --reload --port 8004
```
Open http://localhost:8004/docs for the Swagger UI. Run tests: `pytest -q`

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | /insights/generate | Generate insight (called by orchestrator / IR agent) |
| GET | /insights, /insights/{id} | Read insights |
| POST | /insights/{id}/feedback | Thumbs up/down |
| POST/GET/PUT/DELETE | /reports, /reports/{id} | Reports CRUD (soft delete) |

## Pipeline
validate -> injection check + PII redaction -> pandas stats -> forecast (statsmodels) -> LLM (JSON) -> numeric grounding check -> chart -> save
