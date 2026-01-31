"""Tests for Pydantic models."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from text2x_client.models import (
    QueryRequest,
    QueryOptions,
    QueryResponse,
    ValidationResult,
    ValidationStatus,
    TraceLevel,
    ExampleRequest,
    QueryIntent,
    ComplexityLevel,
)


def test_query_request_basic():
    """Test basic QueryRequest creation."""
    request = QueryRequest(
        provider_id="postgres_main",
        query="Show me all orders",
    )

    assert request.provider_id == "postgres_main"
    assert request.query == "Show me all orders"
    assert request.conversation_id is None
    assert isinstance(request.options, QueryOptions)


def test_query_request_with_options():
    """Test QueryRequest with options."""
    request = QueryRequest(
        provider_id="postgres_main",
        query="Show me all orders",
        options=QueryOptions(
            max_iterations=5,
            confidence_threshold=0.85,
            trace_level=TraceLevel.FULL,
            enable_execution=True,
            rag_top_k=10,
        ),
    )

    assert request.options.max_iterations == 5
    assert request.options.confidence_threshold == 0.85
    assert request.options.trace_level == TraceLevel.FULL
    assert request.options.enable_execution is True
    assert request.options.rag_top_k == 10


def test_query_request_validation():
    """Test QueryRequest validation."""
    # Empty provider_id should fail
    with pytest.raises(Exception):
        QueryRequest(provider_id="", query="test")

    # Empty query should fail
    with pytest.raises(Exception):
        QueryRequest(provider_id="test", query="")

    # Invalid max_iterations should fail
    with pytest.raises(Exception):
        QueryRequest(
            provider_id="test",
            query="test",
            options=QueryOptions(max_iterations=0),
        )

    # Invalid confidence_threshold should fail
    with pytest.raises(Exception):
        QueryRequest(
            provider_id="test",
            query="test",
            options=QueryOptions(confidence_threshold=1.5),
        )


def test_query_response():
    """Test QueryResponse creation."""
    response = QueryResponse(
        conversation_id=uuid4(),
        turn_id=uuid4(),
        generated_query="SELECT * FROM orders;",
        confidence_score=0.95,
        validation_status=ValidationStatus.VALID,
        validation_result=ValidationResult(
            status=ValidationStatus.VALID,
            errors=[],
            warnings=[],
            suggestions=[],
        ),
        needs_clarification=False,
        clarification_questions=[],
        iterations=2,
        created_at=datetime.now(timezone.utc),
    )

    assert response.generated_query == "SELECT * FROM orders;"
    assert response.confidence_score == 0.95
    assert response.validation_status == ValidationStatus.VALID
    assert response.needs_clarification is False
    assert response.iterations == 2


def test_validation_result():
    """Test ValidationResult creation."""
    result = ValidationResult(
        status=ValidationStatus.INVALID,
        errors=["Syntax error on line 1"],
        warnings=["Table 'orders' might not exist"],
        suggestions=["Check table name spelling"],
    )

    assert result.status == ValidationStatus.INVALID
    assert len(result.errors) == 1
    assert len(result.warnings) == 1
    assert len(result.suggestions) == 1


def test_example_request():
    """Test ExampleRequest creation."""
    request = ExampleRequest(
        provider_id="postgres_main",
        natural_language_query="Show me all orders",
        generated_query="SELECT * FROM orders;",
        is_good_example=True,
        involved_tables=["orders"],
        query_intent=QueryIntent.FILTER,
        complexity_level=ComplexityLevel.SIMPLE,
    )

    assert request.provider_id == "postgres_main"
    assert request.is_good_example is True
    assert len(request.involved_tables) == 1
    assert request.query_intent == QueryIntent.FILTER
    assert request.complexity_level == ComplexityLevel.SIMPLE


def test_trace_level_enum():
    """Test TraceLevel enum."""
    assert TraceLevel.NONE.value == "none"
    assert TraceLevel.SUMMARY.value == "summary"
    assert TraceLevel.FULL.value == "full"


def test_validation_status_enum():
    """Test ValidationStatus enum."""
    assert ValidationStatus.VALID.value == "valid"
    assert ValidationStatus.INVALID.value == "invalid"
    assert ValidationStatus.WARNING.value == "warning"
    assert ValidationStatus.UNKNOWN.value == "unknown"


def test_query_intent_enum():
    """Test QueryIntent enum."""
    assert QueryIntent.AGGREGATION.value == "aggregation"
    assert QueryIntent.FILTER.value == "filter"
    assert QueryIntent.JOIN.value == "join"
    assert QueryIntent.SEARCH.value == "search"
    assert QueryIntent.MIXED.value == "mixed"


def test_complexity_level_enum():
    """Test ComplexityLevel enum."""
    assert ComplexityLevel.SIMPLE.value == "simple"
    assert ComplexityLevel.MEDIUM.value == "medium"
    assert ComplexityLevel.COMPLEX.value == "complex"
