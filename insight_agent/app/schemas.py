"""Request/response contracts. Agree on these with Member 1 (query) and Member 2 (retrieval)."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class StructuredQuery(BaseModel):          # produced by Member 1 (NLP Query Agent)
    intent: str = "summary"                # summary | comparison | trend | forecast
    metric: Optional[str] = None           # e.g. "revenue"
    group_by: Optional[str] = None         # e.g. "region"
    date_column: Optional[str] = "date"
    entities: dict[str, Any] = {}


class RetrievedSource(BaseModel):          # produced by Member 2 (IR Agent)
    source: str                            # e.g. "sales_2026.csv"
    rows: list[dict[str, Any]] = []
    text: Optional[str] = None             # optional document chunk


class InsightRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    structured_query: StructuredQuery
    retrieved_data: list[RetrievedSource]


class ReportCreate(BaseModel):
    insight_id: str
    title: str = Field(min_length=1, max_length=200)
    notes: str = ""


class ReportUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = None
    pinned: Optional[bool] = None


class Feedback(BaseModel):
    helpful: bool
    comment: str = ""
