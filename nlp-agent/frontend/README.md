# BizIQ Frontend - Member 1 NLP Dashboard

## 1. Start the NLP Agent

Open PowerShell in the NLP Agent folder:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001
```

Keep this terminal running.

## 2. CORS

Because the frontend is served from port 5500 and FastAPI runs on port 8001,
FastAPI must allow the frontend origin.

Add this to `app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Put the middleware after creating `app` and before `app.include_router(router)`.

## 3. Start the frontend

Open another PowerShell terminal in this `frontend` folder:

```powershell
python -m http.server 5500
```

Open:

`http://127.0.0.1:5500`

## 4. Current functionality

- Ask a new question
- NLP analysis for the current question
- Save query
- Show recent saved questions
- Search previous questions
- Load an old question
- Edit an existing query using `PUT /queries/{id}`
- Delete a query using `DELETE /queries/{id}`
- Display an LLM response when the integrated backend returns one

## 5. Important integration note

At the moment, the frontend sends:

```json
{
  "question": "...",
  "send_to_ir": false,
  "top_k": 5
}
```

This is intentional while the other agents are not integrated.

After Member 2 + Member 3 integration, the request can use:

```json
{
  "question": "...",
  "send_to_ir": true,
  "top_k": 5
}
```

The frontend's `showLLMResponse()` function is prepared to display an actual
LLM response returned by the integrated backend. It does not invent an answer.

## 6. CRUD mapping

Create:
`POST /query`

Read:
`GET /queries`
`GET /queries/{id}`

Update:
`PUT /queries/{id}`

Delete:
`DELETE /queries/{id}`

The Edit action updates the existing query ID; it does not intentionally create
a second record.
