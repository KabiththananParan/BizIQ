"""app/api/search.py — the IR Agent's core endpoint (called by the NLP Agent)."""

from fastapi import APIRouter, Depends

from app.schemas import SearchRequest, SearchResponse
from app.services.auth import AuthUser, verify_token
from app.services.ir_engine import search as run_search

router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
def search_datasources(payload: SearchRequest, user: AuthUser = Depends(verify_token)):
    """Rank the caller's active data sources against the query (TF-IDF + cosine)."""
    results = run_search(payload.query, owner=user.user_id, top_k=payload.top_k)
    return {"query": payload.query, "results": results}
