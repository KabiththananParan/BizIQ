#what type of data the API expects
from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    send_to_ir: bool = True
    top_k: int = Field(default=5, ge=1, le=20)


class EntityRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    query_id: Optional[int] = None


class QueryOut(BaseModel):
    id: int
    original_question: str
    normalized_question: str
    summary: str
    intent: str
    entities: list[dict]
    structured_query: dict
    created_at: str
    updated_at: str
