"""
app/schemas/search.py
Search request/response models: the API contract with the NLP Agent
(Member 1) and the LLM Insight Agent (Member 3).
"""

from pydantic import BaseModel, Field, field_validator

from app.schemas.datasource import clean_text

MAX_QUERY_CHARS = 500


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    top_k: int = Field(default=3, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("query must not be blank")
        return v


class SearchResultItem(BaseModel):
    datasource_id: int
    name: str
    snippet: str                     # best-matching passage, not just the first lines
    score: float                     # cosine similarity, 0..1
    matched_terms: list[str] = []    # explainability: which query terms matched


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
