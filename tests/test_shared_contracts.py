import pytest
from pydantic import ValidationError

from shared_contracts import (
    BusinessQuestionRequest,
    IRSearchResponse,
    RetrievalStatus,
    SafeServiceError,
)


def test_canonical_business_question_validates_limits_and_rejects_credentials():
    request = BusinessQuestionRequest(
        request_id="req-1", question="Show revenue by region", user_id="user-7", top_k=5
    )
    assert request.top_k == 5
    with pytest.raises(ValidationError):
        BusinessQuestionRequest(request_id=" ", question="Hi", user_id="user-7")
    with pytest.raises(ValidationError):
        BusinessQuestionRequest(
            request_id="req-1", question="Show revenue by region", user_id="user-7", top_k=21
        )
    with pytest.raises(ValidationError):
        BusinessQuestionRequest(
            request_id="req-1", question="Show revenue by region", user_id="user-7", password="secret"
        )


def test_retrieval_empty_results_are_successful_no_results():
    response = IRSearchResponse(
        request_id="req-1", query="unknown metric", status=RetrievalStatus.NO_RESULTS, results=[]
    )
    assert response.status == RetrievalStatus.NO_RESULTS


def test_retrieval_status_and_result_invariants_are_validated():
    with pytest.raises(ValidationError):
        IRSearchResponse(request_id="req-1", query="x", status="EMPTY", results=[])
    with pytest.raises(ValidationError):
        IRSearchResponse(request_id="req-1", query="x", status="FOUND", results=[])


def test_safe_service_error_serializes_only_safe_contract_fields():
    error = SafeServiceError(
        request_id="req-1", error={"code": "UPSTREAM_TIMEOUT", "message": "Retrieval timed out"}
    )
    assert error.model_dump() == {
        "request_id": "req-1",
        "error": {"code": "UPSTREAM_TIMEOUT", "message": "Retrieval timed out"},
    }
    with pytest.raises(ValidationError):
        SafeServiceError(
            request_id="req-1",
            error={"code": "UPSTREAM_TIMEOUT", "message": "safe", "token": "secret"},
        )
