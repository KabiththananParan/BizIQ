# BizIQ NLP Query Agent - Member 1

This folder follows the common BizIQ multi-agent project structure used by the team.

## Responsibilities
- Normalize and sanitize user questions
- Classify business intent using keyword-based rules
- Extract entities using spaCy pre-trained NER + domain-specific rules
- Summarize long queries
- Build structured queries
- Query & Entity CRUD using SQLite
- Communicate with the IR Agent using REST/HTTP + JSON

## Folder structure
```text
nlp-agent/
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── models/
│   ├── schemas/
│   │   └── schemas.py
│   ├── services/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── intent.py
│   │   ├── ir_client.py
│   │   ├── ner.py
│   │   ├── preprocessing.py
│   │   ├── query_service.py
│   │   └── summarizer.py
│   └── main.py
├── database/
│   └── db.py
├── tests/
├── requirements.txt
└── README.md
```

## Run on Windows
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload --port 8001
```

Open `http://127.0.0.1:8001/docs`.

## Test
```powershell
python -m pytest -q
```

## Member 2 integration
The IR Agent is expected at `http://127.0.0.1:8002` with `POST /retrieve`. The development token is configured in `app/services/config.py` and should later be replaced by the team's final authentication configuration.
