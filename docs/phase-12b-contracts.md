# Phase 12B — Shared Contracts and Local Configuration

This document defines the shared HTTP boundaries for later integration. The
models in `shared_contracts/` validate the proposed boundary shape; agents keep
their existing local schemas and routes in this phase. Fields explicitly marked
**proposed** are not current API behavior.

## Development ports

| Service | Local port | Startup command (from service folder) |
|---|---:|---|
| NLP Agent | 8001 | `uvicorn app.main:app --reload --port 8001` |
| IR Agent | 8002 | `uvicorn app.main:app --reload --port 8002` |
| Security Agent backend | 8003 | `uvicorn app.main:app --reload --port 8003` |
| Insight Agent | 8004 | `uvicorn app.main:app --reload --port 8004` |
| Security Streamlit frontend | 8501 | `streamlit run app.py --server.port 8501` |

The Security frontend's `API_BASE_URL` remains `http://localhost:8003`.
`IR_AGENT_URL` defaults to `http://127.0.0.1:8002`. The NLP client still calls
`/retrieve`; changing its URL default does not fix the route mismatch.

## Canonical business-question request

The proposed entry request is `BusinessQuestionRequest`:

```json
{
  "request_id": "req-12345",
  "question": "Which region had the lowest sales in Q3?",
  "user_id": "security-user-42",
  "top_k": 5
}
```

`request_id` is a trimmed, non-empty string up to 100 characters. `question` is
3–1000 characters. `user_id` is a delegated identity reference, 1–100
characters; the canonical body carries no credentials. `top_k` is an integer
from 1 through 20, default 5. Authentication stays in HTTP authorization
headers or a separately designed, signed delegation mechanism. Do not copy a
raw JWT into this object.

## Agent boundary models

| Boundary model | Contract fields | Status |
|---|---|---|
| `NLPParseRequest` | `request_id`, `question` (1–2000 chars), `top_k` (1–20) | `request_id` is a **proposed** input addition; current `QueryRequest` has `question`, `send_to_ir`, `top_k`. |
| `NLPParseResponse` | `request_id`, `original_question`, `normalized_question`, `summary`, `intent`, `entities[]` (`text`, `type`), `structured_query` (`intent`, `operation`, `metric`, `locations`, `time_period`, `query`, `entities`), `top_k` | Parsed fields reflect current `/query/parse`; echoed `request_id` is **proposed**. |
| `IRSearchRequest` | `request_id`, `query` (1–500 chars), `top_k` (1–20) | Current `/search` accepts only `query`, `top_k`; `request_id` is **proposed**. |
| `RetrievalResult` | `datasource_id`, `name`, `snippet`, `score` (0–1), `matched_terms[]` | Current IR result item. |
| `IRSearchResponse` | `request_id`, `query`, `status`, `results[]`, optional safe `error` | Wrapper/status/correlation fields are **proposed** around current `{query, results}`. |
| `InsightGenerationRequest` | `request_id`, `user_id`, `question`, `structured_query` (`intent`, `metric`, `group_by`, `date_column`, `entities`), `retrieved_data[]` (`source`, `rows[]`, `text`) | Current Insight fields are `question`, `structured_query`, `retrieved_data`; identity and correlation fields are **proposed**. |
| `InsightGenerationResponse` | `request_id`, `id`, `question`, `ai_generated`, `disclaimer`, `answer`, `key_findings[]`, `reasoning_steps[]`, `assumptions[]`, `confidence`, `limitations`, `evidence[]` (`source`, `rows_used`), `stats`, `chart_spec`, `forecast`, `grounded`, `ungrounded_numbers[]`, `security_flags[]`, optional `model_used` | Output fields reflect current `/insights/generate`; echoed `request_id` is **proposed**. |
| `SafeServiceError` | `request_id`, `error` (`code`, `message`) | **Proposed** standard safe error envelope. Do not serialize stack traces or secrets. |

Models reject undeclared fields. Agent-specific models remain authoritative for
their current routes until later phases adopt these boundaries.

## Retrieval semantics (for Phase 12E)

`RetrievalStatus` has `FOUND`, `NO_RESULTS`, and `FAILED` values.

- `FOUND` requires one or more validated results.
- `NO_RESULTS` requires an empty `results` list and is a successful search (HTTP
  success), not an HTTP error.
- `FAILED` requires an empty result list and a safe error. It represents a
  normalized failed retrieval; callers must not pass it to Insight generation.
- An upstream transport/HTTP failure should use the standard safe service error
  response. A malformed successful response is a contract failure and must be
  rejected before Insight is called; it is not equivalent to `NO_RESULTS`.

These are schema semantics only in Phase 12B. Runtime orchestration and failure
handling are deferred.

## Current NLP-to-IR mismatch

NLP's current client posts to `IR_AGENT_URL + "/retrieve"` with `query`,
`intent`, `entities`, `top_k`, `include_structured`, and `request_id`. IR exposes
`POST /search`, accepts `query` and `top_k`, and returns `{ "query": ..., 
"results": [...] }`. IR has no `/retrieve` endpoint. NLP's default URL now
matches the planned IR port 8002, but the route, extra request fields, and
response contract are still incompatible. The planned adapter maps NLP's
normalized query to IR's `query`, forwards `top_k`, authenticates in headers,
and wraps the current IR response with request ID and retrieval status. The
adapter/client correction is deferred; no retrieval business logic changed.

IR result snippets are not Insight tabular rows. A later adapter must map
`name`/`snippet` to Insight's `source`/`text` or provide genuine structured rows;
it must not pretend snippets are rows.

## Environment variable names and database paths

Names below are from source and example templates; not every variable is
required in every mode. No real `.env` values are part of this document.

| Agent | Environment names | Database path and working directory |
|---|---|---|
| NLP | `NLP_DB_PATH`, `IR_AGENT_URL`, `IR_AGENT_TOKEN`, `IR_REQUEST_TIMEOUT`, `MAX_QUERY_CHARS`, `SUMMARY_THRESHOLD_WORDS`, `SUMMARY_SENTENCES` | `NLP_DB_PATH` defaults to `biziq_nlp.db`, relative to the process working directory. |
| IR | `IR_DB_PATH`, `IR_API_TOKENS`, `IR_RATE_LIMIT` | `IR_DB_PATH` defaults to `ir-agent/database/datasources.db`, anchored to the module directory. |
| Insight | `DB_PATH`, `JWT_SECRET`, `DEV_AUTH`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | `DB_PATH` defaults to `insights.db`, relative to the process working directory. `LLM_API_KEY` may be empty for mock mode; `DEV_AUTH` defaults true. |
| Security backend | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `FAILED_LOGIN_THRESHOLD`, `ACCESS_DENIED_THRESHOLD`, `UNIQUE_IP_THRESHOLD`, `LOGIN_FREQUENCY_THRESHOLD`, `GROQ_API_KEY`, `GROQ_MODEL` | `sqlite:///./security.db`, relative to the backend process working directory. Source currently does not read a database URL environment variable. |
| Security frontend | `API_BASE_URL` | Not applicable; frontend defaults to Security backend port 8003. |

Keep separate virtual environments and each agent's existing requirements file.
The NLP, IR, and Insight database paths are distinct. Security's `JWT_SECRET_KEY`
and Insight's `JWT_SECRET` must not be unified automatically; shared user
identity and token delegation require a deliberate security design. Service
URLs and timeouts are not centrally configurable yet: `IR_AGENT_URL` and
`IR_REQUEST_TIMEOUT` configure the existing NLP-to-IR client; the other future
service URLs/timeouts are **proposed configuration**, not existing settings.
Correlation IDs are request data, not secrets or environment credentials.

## Phase 12C boundary

Phase 12C still needs to implement the approved service identity and user
delegation design, establish actual route/client adapters, and decide how
existing auth and per-user IR ownership map to one user identity. The existing
Security validator has no business-operation permission mappings, so required
permissions and role grants must be explicitly designed and approved before
business requests can pass it. Do not grant them by default.
