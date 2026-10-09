"""Version-one shared contracts for BizIQ service boundaries.

These models document and validate boundaries; they do not replace agent-local
schemas or change any existing route in this phase.
"""

from enum import Enum
from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


CorrelationId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BusinessQuestionRequest(ContractModel):
    """Canonical public request; credentials belong in HTTP auth headers."""

    request_id: CorrelationId
    question: str = Field(min_length=3, max_length=1000)
    user_id: str = Field(min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20)


class NLPParseRequest(ContractModel):
    """Fields needed by the current NLP parsing operation."""

    request_id: CorrelationId
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class NLPExtractedEntity(ContractModel):
    text: str
    type: str


class NLPStructuredQuery(ContractModel):
    """Current NLP shape; not the Insight Agent's StructuredQuery shape."""

    intent: str
    operation: str
    metric: str | None = None
    locations: list[str] = Field(default_factory=list)
    time_period: str | None = None
    query: str
    entities: dict[str, list[str]] = Field(default_factory=dict)


class NLPParseResponse(ContractModel):
    """Current parsed fields plus the proposed echoed correlation identifier."""

    request_id: CorrelationId
    original_question: str
    normalized_question: str
    summary: str
    intent: str
    entities: list[NLPExtractedEntity]
    structured_query: NLPStructuredQuery
    top_k: int = Field(ge=1, le=20)


class IRSearchRequest(ContractModel):
    """Intended IR boundary; request_id is a proposed addition to current /search."""

    request_id: CorrelationId
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=20)


class RetrievalStatus(str, Enum):
    FOUND = "FOUND"
    NO_RESULTS = "NO_RESULTS"
    FAILED = "FAILED"


class RetrievalResult(ContractModel):
    """Current IR search-result fields."""

    datasource_id: int
    name: str
    snippet: str
    score: float = Field(ge=0, le=1)
    matched_terms: list[str] = Field(default_factory=list)


class SafeErrorDetail(ContractModel):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z0-9_]+$")
    message: str = Field(min_length=1, max_length=500)


class SafeServiceError(ContractModel):
    """Safe error envelope; do not place credentials or stack traces in it."""

    request_id: CorrelationId
    error: SafeErrorDetail


class IRSearchResponse(ContractModel):
    """Proposed normalized IR envelope around the currently returned fields."""

    request_id: CorrelationId
    query: str
    status: RetrievalStatus
    results: list[RetrievalResult] = Field(default_factory=list)
    error: SafeErrorDetail | None = None

    @model_validator(mode="after")
    def status_matches_contents(self):
        if self.status == RetrievalStatus.FOUND and not self.results:
            raise ValueError("FOUND requires at least one result")
        if self.status == RetrievalStatus.NO_RESULTS and (self.results or self.error):
            raise ValueError("NO_RESULTS requires an empty result list and no error")
        if self.status == RetrievalStatus.FAILED and (self.results or not self.error):
            raise ValueError("FAILED requires an empty result list and a safe error")
        if self.status != RetrievalStatus.FAILED and self.error is not None:
            raise ValueError("Only FAILED may include an error")
        return self


class InsightStructuredQuery(ContractModel):
    """Current Insight Agent input query shape."""

    intent: str = "summary"
    metric: str | None = None
    group_by: str | None = None
    date_column: str | None = "date"
    entities: dict[str, Any] = Field(default_factory=dict)


class RetrievedSource(ContractModel):
    """Current Insight data source input; IR snippets need an adapter to this."""

    source: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    text: str | None = None


class InsightGenerationRequest(ContractModel):
    """Insight input plus proposed correlation and delegated-user context."""

    request_id: CorrelationId
    user_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=3, max_length=1000)
    structured_query: InsightStructuredQuery
    retrieved_data: list[RetrievedSource]


class InsightEvidence(ContractModel):
    source: str
    rows_used: int = Field(ge=0)


class InsightGenerationResponse(ContractModel):
    """Current insight output fields plus proposed correlation identifier."""

    request_id: CorrelationId
    id: str
    question: str
    ai_generated: bool
    disclaimer: str
    answer: str
    key_findings: list[str]
    reasoning_steps: list[str]
    assumptions: list[str]
    confidence: str
    limitations: str
    evidence: list[InsightEvidence]
    stats: dict[str, Any]
    chart_spec: dict[str, Any] | None
    forecast: dict[str, Any] | None
    grounded: bool
    ungrounded_numbers: list[str]
    security_flags: list[str]
    model_used: str | None = None
