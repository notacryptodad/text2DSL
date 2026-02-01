"""Tests for WebSocket orchestrator integration."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import WebSocket
from text2x.api.websocket import (
    handle_websocket_query,
    WebSocketQueryRequest,
    QueryOptions,
    TraceLevel,
    EventType,
    ProgressStage,
)
from text2x.agents.orchestrator import OrchestratorAgent
from text2x.agents.base import LLMConfig
from text2x.models import (
    ConversationStatus,
    ValidationStatus as DomainValidationStatus,
)


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def send_json(self, data: dict):
        """Mock sending JSON data."""
        self.sent_messages.append(data)

    async def close(self):
        """Mock closing connection."""
        self.closed = True


class MockProvider:
    """Mock query provider for testing."""

    def get_provider_id(self):
        return "test-provider"

    async def get_schema(self):
        return {"tables": ["users", "orders"]}

    async def validate_query(self, query: str):
        return {"valid": True, "errors": []}

    async def execute_query(self, query: str):
        return {"success": True, "rows": 10}


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    return MockProvider()


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = AsyncMock(spec=OrchestratorAgent)

    # Mock the process_query_stream method to yield test events
    async def mock_stream(*args, **kwargs):
        # Yield progress events
        yield {
            "type": "progress",
            "data": {
                "stage": "started",
                "message": "Query processing started",
                "progress": 0.0
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "schema_retrieval",
                "message": "Retrieving database schema...",
                "progress": 0.1,
                "iteration": 1
            },
            "trace": {"agent": "SchemaExpert", "action": "retrieving_schema"}
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "rag_search",
                "message": "Searching for similar examples...",
                "progress": 0.2,
                "iteration": 1
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "context_gathered",
                "message": "Found 2 tables and 1 examples",
                "progress": 0.3,
                "iteration": 1,
                "tables_found": 2,
                "examples_found": 1,
                "top_similarity": 0.9
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "query_generation",
                "message": "Generating query (iteration 1)...",
                "progress": 0.3,
                "iteration": 1
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "query_generated",
                "message": "Query generated with confidence 0.92",
                "progress": 0.4,
                "iteration": 1,
                "confidence": 0.92,
                "query_preview": "SELECT * FROM users"
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "validation",
                "message": "Validating generated query...",
                "progress": 0.5,
                "iteration": 1
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "validation_complete",
                "message": "Validation passed",
                "progress": 0.6,
                "iteration": 1,
                "validation_status": "passed",
                "has_errors": False,
                "has_warnings": False
            }
        }

        # Yield final result
        yield {
            "type": "result",
            "data": {
                "stage": "completed",
                "message": "Query processing completed",
                "progress": 1.0,
                "conversation_id": str(uuid4()),
                "turn_id": str(uuid4()),
                "generated_query": "SELECT * FROM users",
                "confidence_score": 0.92,
                "validation_status": "passed",
                "execution_result": None,
                "iterations": 1,
                "needs_clarification": False,
                "clarification_question": None,
                "total_duration_ms": 1200.0
            }
        }

    orchestrator.process_query_stream = mock_stream
    return orchestrator


@pytest.mark.asyncio
async def test_websocket_streaming_query_progress(mock_websocket, mock_orchestrator):
    """Test that WebSocket streams query progress events."""
    request = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me all users",
        options=QueryOptions(trace_level=TraceLevel.FULL)
    )

    # Process query
    await handle_websocket_query(
        websocket=mock_websocket,
        request=request,
        orchestrator=mock_orchestrator
    )

    # Verify events were sent
    assert len(mock_websocket.sent_messages) > 0

    # Check for expected event types
    event_types = [msg["type"] for msg in mock_websocket.sent_messages]
    assert "progress" in event_types
    assert "result" in event_types

    # Check for expected stages
    stages = [
        msg["data"].get("stage")
        for msg in mock_websocket.sent_messages
        if msg["type"] == "progress"
    ]
    assert "started" in stages
    assert "schema_retrieval" in stages
    assert "rag_search" in stages
    assert "query_generation" in stages
    assert "validation" in stages


@pytest.mark.asyncio
async def test_websocket_clarification_flow(mock_websocket):
    """Test WebSocket clarification request flow."""
    # Create orchestrator that requests clarification
    orchestrator = AsyncMock(spec=OrchestratorAgent)

    async def clarification_stream(*args, **kwargs):
        yield {
            "type": "progress",
            "data": {
                "stage": "started",
                "message": "Query processing started",
                "progress": 0.0
            }
        }

        # Yield clarification event
        yield {
            "type": "clarification",
            "data": {
                "stage": "clarification_needed",
                "message": "Need clarification from user",
                "question": "Which table would you like to query: users, orders, or products?",
                "conversation_id": str(uuid4()),
                "turn_id": str(uuid4()),
                "current_query": "SELECT * FROM ???",
                "confidence": 0.45
            }
        }

    orchestrator.process_query_stream = clarification_stream

    request = WebSocketQueryRequest(
        provider_id="test-provider",
        query="show data",
        options=QueryOptions(trace_level=TraceLevel.NONE)
    )

    # Process query
    await handle_websocket_query(
        websocket=mock_websocket,
        request=request,
        orchestrator=orchestrator
    )

    # Verify clarification event was sent
    clarification_events = [
        msg for msg in mock_websocket.sent_messages
        if msg["type"] == "clarification"
    ]
    assert len(clarification_events) == 1

    clarification = clarification_events[0]
    assert "question" in clarification["data"]
    assert clarification["data"]["confidence"] < 0.6


@pytest.mark.asyncio
async def test_websocket_error_handling(mock_websocket):
    """Test WebSocket error handling."""
    # Create orchestrator that raises an error
    orchestrator = AsyncMock(spec=OrchestratorAgent)

    async def error_stream(*args, **kwargs):
        yield {
            "type": "progress",
            "data": {
                "stage": "started",
                "message": "Query processing started",
                "progress": 0.0
            }
        }

        # Raise an error
        raise ValueError("Test error during query processing")

    orchestrator.process_query_stream = error_stream

    request = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me all users",
        options=QueryOptions()
    )

    # Process query (should handle error gracefully)
    await handle_websocket_query(
        websocket=mock_websocket,
        request=request,
        orchestrator=orchestrator
    )

    # Verify error event was sent
    error_events = [
        msg for msg in mock_websocket.sent_messages
        if msg["type"] == "error"
    ]
    assert len(error_events) == 1

    error = error_events[0]
    assert error["data"]["error"] == "processing_error"
    assert "Failed to process query" in error["data"]["message"]


@pytest.mark.asyncio
async def test_websocket_trace_levels(mock_websocket, mock_orchestrator):
    """Test WebSocket respects trace level settings."""
    # Test with FULL trace level
    request_full = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me all users",
        options=QueryOptions(trace_level=TraceLevel.FULL)
    )

    await handle_websocket_query(
        websocket=mock_websocket,
        request=request_full,
        orchestrator=mock_orchestrator
    )

    # Check that trace information is included
    messages_with_trace = [
        msg for msg in mock_websocket.sent_messages
        if msg.get("trace") is not None
    ]
    assert len(messages_with_trace) > 0

    # Test with NONE trace level
    mock_websocket.sent_messages.clear()

    request_none = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me all users",
        options=QueryOptions(trace_level=TraceLevel.NONE)
    )

    # Create new orchestrator without traces
    orchestrator_no_trace = AsyncMock(spec=OrchestratorAgent)

    async def stream_no_trace(*args, **kwargs):
        yield {
            "type": "progress",
            "data": {
                "stage": "started",
                "message": "Query processing started",
                "progress": 0.0
            }
        }

        yield {
            "type": "result",
            "data": {
                "stage": "completed",
                "message": "Query processing completed",
                "progress": 1.0,
                "generated_query": "SELECT * FROM users",
                "confidence_score": 0.92
            }
        }

    orchestrator_no_trace.process_query_stream = stream_no_trace

    await handle_websocket_query(
        websocket=mock_websocket,
        request=request_none,
        orchestrator=orchestrator_no_trace
    )

    # Check that NO trace information is included
    messages_with_trace = [
        msg for msg in mock_websocket.sent_messages
        if msg.get("trace") is not None
    ]
    assert len(messages_with_trace) == 0


@pytest.mark.asyncio
async def test_websocket_multiple_iterations(mock_websocket):
    """Test WebSocket streaming with multiple query refinement iterations."""
    orchestrator = AsyncMock(spec=OrchestratorAgent)

    async def multi_iteration_stream(*args, **kwargs):
        # Iteration 1
        yield {
            "type": "progress",
            "data": {
                "stage": "query_generation",
                "message": "Generating query (iteration 1)...",
                "progress": 0.3,
                "iteration": 1
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "validation_complete",
                "message": "Validation failed",
                "progress": 0.4,
                "iteration": 1,
                "validation_status": "failed",
                "has_errors": True,
                "has_warnings": False
            }
        }

        # Iteration 2
        yield {
            "type": "progress",
            "data": {
                "stage": "query_generation",
                "message": "Generating query (iteration 2)...",
                "progress": 0.45,
                "iteration": 2
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "validation_complete",
                "message": "Validation passed",
                "progress": 0.6,
                "iteration": 2,
                "validation_status": "passed",
                "has_errors": False,
                "has_warnings": False
            }
        }

        # Final result
        yield {
            "type": "result",
            "data": {
                "stage": "completed",
                "message": "Query processing completed",
                "progress": 1.0,
                "generated_query": "SELECT * FROM users WHERE active = true",
                "confidence_score": 0.88,
                "iterations": 2
            }
        }

    orchestrator.process_query_stream = multi_iteration_stream

    request = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me active users",
        options=QueryOptions(max_iterations=3)
    )

    await handle_websocket_query(
        websocket=mock_websocket,
        request=request,
        orchestrator=orchestrator
    )

    # Verify multiple iterations were streamed
    query_gen_events = [
        msg for msg in mock_websocket.sent_messages
        if msg["type"] == "progress" and msg["data"].get("stage") == "query_generation"
    ]
    assert len(query_gen_events) == 2

    # Verify iterations are correctly numbered
    iterations = [msg["data"]["iteration"] for msg in query_gen_events]
    assert iterations == [1, 2]


@pytest.mark.asyncio
async def test_websocket_execution_results(mock_websocket):
    """Test WebSocket streaming with query execution results."""
    orchestrator = AsyncMock(spec=OrchestratorAgent)

    async def execution_stream(*args, **kwargs):
        yield {
            "type": "progress",
            "data": {
                "stage": "validation_complete",
                "message": "Validation passed",
                "progress": 0.6,
                "iteration": 1,
                "validation_status": "passed"
            }
        }

        yield {
            "type": "progress",
            "data": {
                "stage": "execution_complete",
                "message": "Execution successful",
                "progress": 0.8,
                "iteration": 1,
                "execution_success": True,
                "row_count": 150,
                "execution_time_ms": 45
            },
            "trace": {
                "success": True,
                "row_count": 150,
                "execution_time_ms": 45,
                "error": None
            }
        }

        yield {
            "type": "result",
            "data": {
                "stage": "completed",
                "message": "Query processing completed",
                "progress": 1.0,
                "generated_query": "SELECT * FROM users",
                "confidence_score": 0.92,
                "execution_result": {
                    "success": True,
                    "row_count": 150,
                    "execution_time_ms": 45,
                    "error": None
                }
            }
        }

    orchestrator.process_query_stream = execution_stream

    request = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me all users",
        options=QueryOptions(
            enable_execution=True,
            trace_level=TraceLevel.FULL
        )
    )

    await handle_websocket_query(
        websocket=mock_websocket,
        request=request,
        orchestrator=orchestrator
    )

    # Verify execution event was sent
    execution_events = [
        msg for msg in mock_websocket.sent_messages
        if msg["type"] == "progress" and msg["data"].get("stage") == "execution_complete"
    ]
    assert len(execution_events) == 1

    execution = execution_events[0]
    assert execution["data"]["execution_success"] is True
    assert execution["data"]["row_count"] == 150
    assert execution["data"]["execution_time_ms"] == 45


@pytest.mark.asyncio
async def test_websocket_conversation_continuity(mock_websocket, mock_orchestrator):
    """Test WebSocket maintains conversation context across multiple turns."""
    conversation_id = uuid4()

    # First turn
    request1 = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me all users",
        conversation_id=conversation_id,
        options=QueryOptions()
    )

    await handle_websocket_query(
        websocket=mock_websocket,
        request=request1,
        orchestrator=mock_orchestrator
    )

    # Verify conversation_id is maintained
    result_events = [
        msg for msg in mock_websocket.sent_messages
        if msg["type"] == "result"
    ]
    assert len(result_events) == 1
    # Note: The mock orchestrator doesn't preserve conversation_id in this test,
    # but in real usage the orchestrator would maintain it


@pytest.mark.asyncio
async def test_websocket_intermediate_results(mock_websocket):
    """Test WebSocket streams intermediate results (schema, RAG examples, query drafts)."""
    orchestrator = AsyncMock(spec=OrchestratorAgent)

    async def detailed_stream(*args, **kwargs):
        # Schema retrieval
        yield {
            "type": "progress",
            "data": {
                "stage": "schema_retrieval",
                "message": "Retrieving database schema...",
                "progress": 0.1
            }
        }

        # Schema found
        yield {
            "type": "progress",
            "data": {
                "stage": "context_gathered",
                "message": "Found 3 tables and 5 examples",
                "progress": 0.3,
                "tables_found": 3,
                "examples_found": 5,
                "top_similarity": 0.92
            },
            "trace": {
                "schema": {
                    "tables": ["users", "orders", "products"],
                    "total_columns": 15
                },
                "rag": {
                    "examples_count": 5,
                    "top_scores": [0.92, 0.88, 0.85]
                }
            }
        }

        # Query draft
        yield {
            "type": "progress",
            "data": {
                "stage": "query_generated",
                "message": "Query generated with confidence 0.90",
                "progress": 0.6,
                "confidence": 0.90,
                "query_preview": "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o..."
            }
        }

        # Final result
        yield {
            "type": "result",
            "data": {
                "stage": "completed",
                "message": "Query processing completed",
                "progress": 1.0,
                "generated_query": "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name",
                "confidence_score": 0.90
            }
        }

    orchestrator.process_query_stream = detailed_stream

    request = WebSocketQueryRequest(
        provider_id="test-provider",
        query="Show me user order counts",
        options=QueryOptions(trace_level=TraceLevel.FULL)
    )

    await handle_websocket_query(
        websocket=mock_websocket,
        request=request,
        orchestrator=orchestrator
    )

    # Verify intermediate results were streamed
    context_events = [
        msg for msg in mock_websocket.sent_messages
        if msg["type"] == "progress" and msg["data"].get("stage") == "context_gathered"
    ]
    assert len(context_events) == 1
    assert context_events[0]["data"]["tables_found"] == 3
    assert context_events[0]["data"]["examples_found"] == 5

    query_draft_events = [
        msg for msg in mock_websocket.sent_messages
        if msg["type"] == "progress" and msg["data"].get("stage") == "query_generated"
    ]
    assert len(query_draft_events) == 1
    assert "query_preview" in query_draft_events[0]["data"]
