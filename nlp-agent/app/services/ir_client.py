"""HTTP client used by Member 1 to communicate with Member 2's IR Agent."""
import httpx
from fastapi import HTTPException
from app.services import config


def retrieve_from_ir(structured_query: dict, top_k: int = 5, request_id: str = "") -> dict:
    """Send Member 1's structured query to Member 2 using REST/HTTP + JSON."""
    payload = {
        "query": structured_query["query"],
        "intent": structured_query["intent"],
        "entities": structured_query["entities"],
        "top_k": top_k,
        "include_structured": True,
        "request_id": request_id,
    }
    headers = {"Authorization": f"Bearer {config.IR_AGENT_TOKEN}"}

    try:
        response = httpx.post(
            f"{config.IR_AGENT_URL}/retrieve",
            json=payload,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"IR Agent is unavailable: {exc}")

    if response.status_code >= 400:
        detail = response.text[:500]
        raise HTTPException(response.status_code, f"IR Agent error: {detail}")

    return response.json()
