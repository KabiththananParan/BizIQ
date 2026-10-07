import json
import uuid

from fastapi import APIRouter, HTTPException

from app.schemas import EntityRequest, QueryOut, QueryRequest
from app.services import config
from app.services.ir_client import retrieve_from_ir
from app.services.query_service import process_question, query_to_dict, save_query
from app.services.preprocessing import normalize_text
from app.services.summarizer import summarize_text
from database import db

router = APIRouter()


@router.get("/")
def root():
    return {"message": "BizIQ NLP Query Agent is running", "agent": "member-1-nlp"}


@router.get("/health")
def health():
    return {"status": "ok", "agent": "nlp-agent", "ir_agent_url": config.IR_AGENT_URL}


@router.get("/capabilities")
def capabilities():
    return {
        "agent": "nlp-agent",
        "version": "1.0.0",
        "responsibilities": [
            "normalization", "intent classification", "named entity recognition",
            "extractive summarization", "structured query generation",
            "query/entity CRUD", "REST communication with IR Agent",
        ],
    }

#Give a code to the NLP query agent
@router.post("/query")
def process_query(request: QueryRequest):
    result = process_question(request.question, request.top_k)
    saved = save_query(result)
    response = dict(saved)
    if request.send_to_ir:
        request_id = str(uuid.uuid4())
        response["ir_request_id"] = request_id
        response["ir_result"] = retrieve_from_ir(result["structured_query"], request.top_k, request_id)
    else:
        response["ir_result"] = None
    return response


@router.post("/query/parse")
def parse_only(request: QueryRequest):
    return process_question(request.question, request.top_k)


@router.post("/queries", response_model=QueryOut, status_code=201)
def create_query(request: QueryRequest):
    return save_query(process_question(request.question, request.top_k))


@router.get("/queries")
def list_queries(limit: int = 50):
    limit = max(1, min(limit, 200))
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM queries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [query_to_dict(row) for row in rows]


@router.get("/queries/{query_id}")
def get_query(query_id: int):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM queries WHERE id=?", (query_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Query not found")
    return query_to_dict(row)


@router.put("/queries/{query_id}")
def edit_query(query_id: int, request: QueryRequest):
    result = process_question(request.question, request.top_k)
    with db.get_conn() as conn:
        exists = conn.execute("SELECT id FROM queries WHERE id=?", (query_id,)).fetchone()
        if exists is None:
            raise HTTPException(404, "Query not found")
        conn.execute(
            """UPDATE queries SET original_question=?, normalized_question=?, summary=?,
               intent=?, structured_query=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (result["original_question"], result["normalized_question"], result["summary"],
             result["intent"], json.dumps(result["structured_query"]), query_id),
        )
        conn.execute("DELETE FROM entities WHERE query_id=?", (query_id,))
        conn.executemany(
            "INSERT INTO entities (query_id, text, type) VALUES (?, ?, ?)",
            [(query_id, e["text"], e["type"]) for e in result["entities"]],
        )
        row = conn.execute("SELECT * FROM queries WHERE id=?", (query_id,)).fetchone()
    return query_to_dict(row)


@router.delete("/queries/{query_id}")
def delete_query(query_id: int):
    with db.get_conn() as conn:
        cur = conn.execute("DELETE FROM queries WHERE id=?", (query_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Query not found")
    return {"message": "Query deleted successfully", "query_id": query_id}


@router.post("/entities", status_code=201)
def create_entity(request: EntityRequest):
    with db.get_conn() as conn:
        if request.query_id is not None:
            q = conn.execute("SELECT id FROM queries WHERE id=?", (request.query_id,)).fetchone()
            if q is None:
                raise HTTPException(404, "Query not found")
        cur = conn.execute(
            "INSERT INTO entities (query_id, text, type) VALUES (?, ?, ?)",
            (request.query_id, request.text.strip(), request.type.strip().upper()),
        )
        entity_id = cur.lastrowid
        row = conn.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone()
    return dict(row)


@router.get("/entities")
def list_entities(query_id: int | None = None):
    with db.get_conn() as conn:
        if query_id is None:
            rows = conn.execute("SELECT * FROM entities ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM entities WHERE query_id=? ORDER BY id", (query_id,)).fetchall()
    return [dict(r) for r in rows]


@router.get("/entities/{entity_id}")
def get_entity(entity_id: int):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Entity not found")
    return dict(row)


@router.put("/entities/{entity_id}")
def update_entity(entity_id: int, request: EntityRequest):
    with db.get_conn() as conn:
        exists = conn.execute("SELECT id FROM entities WHERE id=?", (entity_id,)).fetchone()
        if exists is None:
            raise HTTPException(404, "Entity not found")
        if request.query_id is not None:
            q = conn.execute("SELECT id FROM queries WHERE id=?", (request.query_id,)).fetchone()
            if q is None:
                raise HTTPException(404, "Query not found")
        conn.execute(
            "UPDATE entities SET query_id=?, text=?, type=? WHERE id=?",
            (request.query_id, request.text.strip(), request.type.strip().upper(), entity_id),
        )
        row = conn.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone()
    return dict(row)


@router.delete("/entities/{entity_id}")
def delete_entity(entity_id: int):
    with db.get_conn() as conn:
        cur = conn.execute("DELETE FROM entities WHERE id=?", (entity_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Entity not found")
    return {"message": "Entity deleted successfully", "entity_id": entity_id}


@router.post("/forward-to-ir")
def forward_to_ir(request: QueryRequest):
    result = process_question(request.question, request.top_k)
    request_id = str(uuid.uuid4())
    ir_result = retrieve_from_ir(result["structured_query"], request.top_k, request_id)
    return {"request_id": request_id, "nlp_result": result, "ir_result": ir_result}


@router.post("/summarize")
def summarize(request: QueryRequest):
    normalized = normalize_text(request.question)
    return {"original_text": request.question, "normalized_text": normalized, "summary": summarize_text(normalized)}
