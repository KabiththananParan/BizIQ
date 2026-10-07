import json

from app.services import config
from app.services.intent import classify_intent
from app.services.ner import entities_to_ir_format, extract_entities
from app.services.preprocessing import sanitize_input, normalize_text
from app.services.summarizer import summarize_text
from database import db


def build_structured_query(
    intent: str,
    entities: list[dict],
    normalized_question: str
) -> dict:
    """Create the logical contract sent to the IR Agent."""

    ir_entities = entities_to_ir_format(entities)

    operation_map = {
        "COMPARISON": "COMPARE",
        "RANKING": "RANK",
        "AGGREGATION": "AGGREGATE",
        "FORECAST_REQUEST": "FORECAST",
        "TREND_ANALYSIS": "TREND",
        "REGIONAL_ANALYSIS": "REGIONAL_ANALYSIS",
        "PRODUCT_ANALYSIS": "PRODUCT_ANALYSIS",
        "REVENUE_ANALYSIS": "REVENUE_ANALYSIS",
        "SALES_ANALYSIS": "SALES_ANALYSIS",
        "UNKNOWN": "UNKNOWN",
    }

    metric = ir_entities.get("metric", [None])[0]

    locations = (
        ir_entities.get("location", [])
        + ir_entities.get("region", [])
    )

    time_period = None

    if ir_entities.get("time_period"):
        time_period = ir_entities["time_period"][0]
    elif ir_entities.get("quarter"):
        time_period = ir_entities["quarter"][0]

    return {
        "intent": intent,
        "operation": operation_map[intent],
        "metric": metric,
        "locations": locations,
        "time_period": time_period,
        "query": normalized_question,
        "entities": ir_entities,
    }


def process_question(question: str, top_k: int = 5) -> dict:
    """Run the complete Member 1 NLP pipeline."""

    # Step 1: Sanitize user input
    sanitized = sanitize_input(question)

    # Step 2: Normalize the sanitized input
    normalized = normalize_text(sanitized)

    # Step 3: Classify intent
    intent = classify_intent(normalized)

    # Step 4: Extract entities
    entities = extract_entities(normalized)

    # Step 5: Generate summary when the question is long enough
    summary = ""

    if len(normalized.split()) >= config.SUMMARY_THRESHOLD_WORDS:
        summary = summarize_text(normalized)

    # Step 6: Build structured query for IR Agent
    structured = build_structured_query(
        intent,
        entities,
        normalized
    )

    return {
        "original_question": question,
        "normalized_question": normalized,
        "summary": summary,
        "intent": intent,
        "entities": entities,
        "structured_query": structured,
        "top_k": top_k,
    }


def save_query(result: dict) -> dict:
    with db.get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO queries
               (original_question, normalized_question, summary, intent, structured_query)
               VALUES (?, ?, ?, ?, ?)""",
            (
                result["original_question"],
                result["normalized_question"],
                result["summary"],
                result["intent"],
                json.dumps(result["structured_query"]),
            ),
        )

        query_id = cur.lastrowid

        conn.executemany(
            "INSERT INTO entities (query_id, text, type) VALUES (?, ?, ?)",
            [
                (query_id, e["text"], e["type"])
                for e in result["entities"]
            ],
        )

        row = conn.execute(
            "SELECT * FROM queries WHERE id=?",
            (query_id,)
        ).fetchone()

    return query_to_dict(row)


def query_to_dict(row) -> dict:
    with db.get_conn() as conn:
        entity_rows = conn.execute(
            "SELECT text, type FROM entities WHERE query_id=? ORDER BY id",
            (row["id"],)
        ).fetchall()

    return {
        "id": row["id"],
        "original_question": row["original_question"],
        "normalized_question": row["normalized_question"],
        "summary": row["summary"],
        "intent": row["intent"],
        "entities": [dict(e) for e in entity_rows],
        "structured_query": json.loads(row["structured_query"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }