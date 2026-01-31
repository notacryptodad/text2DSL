"""Tests for Text2XClient."""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from text2x_client.client import (
    Text2XClient,
    Text2XError,
    Text2XAPIError,
    Text2XConnectionError,
    Text2XValidationError,
)
from text2x_client.models import (
    QueryResponse,
    ConversationResponse,
    ProviderInfo,
    ProviderSchema,
    RAGExampleResponse,
    ReviewQueueItem,
    ValidationResult,
    ValidationStatus,
    ErrorResponse,
    TableInfo,
    ConversationStatus,
    ExampleStatus,
)


@pytest.fixture
def mock_client():
    """Create a Text2XClient with mocked httpx client."""
    client = Text2XClient(base_url="http://localhost:8000", api_key="test-key")
    client._client = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = Text2XClient(
        base_url="http://localhost:8000",
        api_key="test-key",
        timeout=60.0,
        max_retries=5,
    )

    assert client.base_url == "http://localhost:8000"
    assert client.api_key == "test-key"
    assert client.timeout == 60.0
    assert client.max_retries == 5

    await client.close()


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client as async context manager."""
    async with Text2XClient("http://localhost:8000") as client:
        assert client._client is not None

    # Client should be closed after context exit
    # _client.aclose() should have been called


@pytest.mark.asyncio
async def test_query_success(mock_client):
    """Test successful query request."""
    conversation_id = uuid4()
    turn_id = uuid4()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "conversation_id": str(conversation_id),
        "turn_id": str(turn_id),
        "generated_query": "SELECT * FROM orders;",
        "confidence_score": 0.95,
        "validation_status": "valid",
        "validation_result": {
            "status": "valid",
            "errors": [],
            "warnings": [],
            "suggestions": [],
        },
        "needs_clarification": False,
        "clarification_questions": [],
        "iterations": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    mock_client._client.request.return_value = mock_response

    response = await mock_client.query(
        provider_id="postgres_main",
        query="Show me all orders",
    )

    assert isinstance(response, QueryResponse)
    assert response.conversation_id == conversation_id
    assert response.generated_query == "SELECT * FROM orders;"
    assert response.confidence_score == 0.95
    assert response.validation_status == ValidationStatus.VALID


@pytest.mark.asyncio
async def test_query_with_options(mock_client):
    """Test query with custom options."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "conversation_id": str(uuid4()),
        "turn_id": str(uuid4()),
        "generated_query": "SELECT * FROM orders;",
        "confidence_score": 0.85,
        "validation_status": "valid",
        "validation_result": {
            "status": "valid",
            "errors": [],
            "warnings": [],
            "suggestions": [],
        },
        "needs_clarification": False,
        "clarification_questions": [],
        "iterations": 3,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    mock_client._client.request.return_value = mock_response

    response = await mock_client.query(
        provider_id="postgres_main",
        query="Show me all orders",
        max_iterations=5,
        confidence_threshold=0.8,
        trace_level="full",
        enable_execution=True,
    )

    assert isinstance(response, QueryResponse)


@pytest.mark.asyncio
async def test_query_validation_error(mock_client):
    """Test query with invalid request parameters."""
    with pytest.raises(Text2XValidationError):
        await mock_client.query(
            provider_id="",  # Empty provider_id
            query="test",
        )


@pytest.mark.asyncio
async def test_query_api_error(mock_client):
    """Test query with API error response."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error": "ValidationError",
        "message": "Invalid provider_id",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    mock_client._client.request.return_value = mock_response

    with pytest.raises(Text2XAPIError) as exc_info:
        await mock_client.query(
            provider_id="invalid",
            query="test",
        )

    assert exc_info.value.error_response.error == "ValidationError"


@pytest.mark.asyncio
async def test_get_conversation(mock_client):
    """Test get conversation."""
    conversation_id = uuid4()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": str(conversation_id),
        "provider_id": "postgres_main",
        "status": "active",
        "turn_count": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "turns": [],
    }

    mock_client._client.request.return_value = mock_response

    conversation = await mock_client.get_conversation(conversation_id)

    assert isinstance(conversation, ConversationResponse)
    assert conversation.id == conversation_id
    assert conversation.status == ConversationStatus.ACTIVE


@pytest.mark.asyncio
async def test_submit_feedback(mock_client):
    """Test submit feedback."""
    conversation_id = uuid4()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Feedback submitted"}

    mock_client._client.request.return_value = mock_response

    result = await mock_client.submit_feedback(
        conversation_id=conversation_id,
        rating=5,
        is_query_correct=True,
        comments="Great query!",
    )

    assert result["message"] == "Feedback submitted"


@pytest.mark.asyncio
async def test_list_providers(mock_client):
    """Test list providers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "postgres_main",
            "name": "PostgreSQL Main",
            "type": "postgresql",
            "connection_status": "connected",
            "table_count": 10,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    mock_client._client.request.return_value = mock_response

    providers = await mock_client.list_providers()

    assert len(providers) == 1
    assert isinstance(providers[0], ProviderInfo)
    assert providers[0].id == "postgres_main"


@pytest.mark.asyncio
async def test_get_schema(mock_client):
    """Test get schema."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "provider_id": "postgres_main",
        "provider_type": "postgresql",
        "tables": [
            {
                "name": "orders",
                "columns": [],
                "primary_keys": ["id"],
                "foreign_keys": [],
            }
        ],
        "metadata": {},
        "last_refreshed": datetime.now(timezone.utc).isoformat(),
    }

    mock_client._client.request.return_value = mock_response

    schema = await mock_client.get_schema("postgres_main")

    assert isinstance(schema, ProviderSchema)
    assert schema.provider_id == "postgres_main"
    assert len(schema.tables) == 1


@pytest.mark.asyncio
async def test_refresh_schema(mock_client):
    """Test refresh schema."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Schema refresh initiated"}

    mock_client._client.request.return_value = mock_response

    result = await mock_client.refresh_schema("postgres_main")

    assert result["message"] == "Schema refresh initiated"


@pytest.mark.asyncio
async def test_get_review_queue(mock_client):
    """Test get review queue."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "turn_id": str(uuid4()),
            "provider_id": "postgres_main",
            "user_input": "Show me orders",
            "generated_query": "SELECT * FROM orders;",
            "confidence_score": 0.6,
            "validation_status": "valid",
            "reason_for_review": "low_confidence",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "priority": 1,
        }
    ]

    mock_client._client.request.return_value = mock_response

    queue = await mock_client.get_review_queue(limit=10)

    assert len(queue) == 1
    assert isinstance(queue[0], ReviewQueueItem)


@pytest.mark.asyncio
async def test_submit_review(mock_client):
    """Test submit review."""
    review_id = uuid4()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Review submitted"}

    mock_client._client.request.return_value = mock_response

    result = await mock_client.submit_review(
        review_id=review_id,
        approved=True,
        feedback="Query looks good",
    )

    assert result["message"] == "Review submitted"


@pytest.mark.asyncio
async def test_list_examples(mock_client):
    """Test list examples."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": str(uuid4()),
            "provider_id": "postgres_main",
            "natural_language_query": "Show me orders",
            "generated_query": "SELECT * FROM orders;",
            "is_good_example": True,
            "status": "approved",
            "involved_tables": ["orders"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    mock_client._client.request.return_value = mock_response

    examples = await mock_client.list_examples(
        provider_id="postgres_main",
        status="approved",
        limit=10,
    )

    assert len(examples) == 1
    assert isinstance(examples[0], RAGExampleResponse)


@pytest.mark.asyncio
async def test_add_example(mock_client):
    """Test add example."""
    example_id = uuid4()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": str(example_id),
        "provider_id": "postgres_main",
        "natural_language_query": "Show me orders",
        "generated_query": "SELECT * FROM orders;",
        "is_good_example": True,
        "status": "pending_review",
        "involved_tables": ["orders"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    mock_client._client.request.return_value = mock_response

    example = await mock_client.add_example(
        provider_id="postgres_main",
        natural_language_query="Show me orders",
        generated_query="SELECT * FROM orders;",
        is_good_example=True,
        involved_tables=["orders"],
    )

    assert isinstance(example, RAGExampleResponse)
    assert example.id == example_id


@pytest.mark.asyncio
async def test_health_check(mock_client):
    """Test health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "healthy",
        "version": "0.1.0",
    }

    mock_client._client.request.return_value = mock_response

    health = await mock_client.health_check()

    assert health["status"] == "healthy"
    assert health["version"] == "0.1.0"
