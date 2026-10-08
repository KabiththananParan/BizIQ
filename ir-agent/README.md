# BizIQ IR Agent - Member 2

This folder follows the common BizIQ multi-agent project structure used by the team.

## Responsibilities
- Manage data sources (CRUD)
- Retrieve and rank relevant business data for structured queries from the NLP Agent
- Rank results using scikit-learn (TODO: confirm method, e.g. TF-IDF + cosine similarity)
- Authenticate requests to the agent
- Communicate with the NLP Agent and LLM Insight Agent using REST/HTTP + JSON

## Folder structure
```text
ir-agent/
├── app/
│   ├── api/
│   │   ├── datasources.py
│   │   └── search.py
│   ├── models/
│   │   └── datasource.py
│   ├── schemas/
│   │   ├── datasource.py
│   │   └── search.py
│   ├── services/
│   │   ├── auth.py
│   │   └── ir_engine.py
│   └── main.py
├── database/
│   └── db.py
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── README.md
└── requirements.txt
```

## API endpoints
| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /search | Search data sources and return ranked results |
| POST | /datasources | Create a data source (201) |
| GET | /datasources | List all data sources |
| GET | /datasources/{datasource_id} | Get one data source |
| PUT | /datasources/{datasource_id} | Update a data source |
| DELETE | /datasources/{datasource_id} | Delete a data source (204) |

Interactive docs: http://127.0.0.1:8000/docs

## Setup
Run from the `ir-agent/` folder:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tests
```bash
pytest
```
