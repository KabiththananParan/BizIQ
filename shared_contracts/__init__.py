"""Shared BizIQ API boundary contracts."""

from .schemas import (
    BusinessQuestionRequest,
    CorrelationId,
    InsightGenerationRequest,
    InsightGenerationResponse,
    IRSearchRequest,
    IRSearchResponse,
    NLPParseRequest,
    NLPParseResponse,
    RetrievalResult,
    RetrievalStatus,
    SafeServiceError,
)

__all__ = [
    "BusinessQuestionRequest",
    "CorrelationId",
    "InsightGenerationRequest",
    "InsightGenerationResponse",
    "IRSearchRequest",
    "IRSearchResponse",
    "NLPParseRequest",
    "NLPParseResponse",
    "RetrievalResult",
    "RetrievalStatus",
    "SafeServiceError",
]
