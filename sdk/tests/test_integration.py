"""Integration tests for Text2X SDK (requires running API server)."""

import pytest
import os
from uuid import uuid4

from text2x_client import Text2XClient, WebSocketClient
from text2x_client.client import Text2XConnectionError

# Skip integration tests unless TEXT2X_RUN_INTEGRATION_TESTS is set
pytestmark = pytest.mark.skipif(
    not os.getenv("TEXT2X_RUN_INTEGRATION_TESTS"),
    reason="Integration tests disabled. Set TEXT2X_RUN_INTEGRATION_TESTS=1 to enable.",
)


@pytest.fixture
def base_url():
    """Get API base URL from environment."""
    return os.getenv("TEXT2X_BASE_URL", "http://localhost:8000")


@pytest.fixture
def api_key():
    """Get API key from environment."""
    return os.getenv("TEXT2X_API_KEY")


@pytest.mark.asyncio
async def test_health_check(base_url, api_key):
    """Test API health check endpoint."""
    async with Text2XClient(base_url, api_key) as client:
        try:
            health = await client.health_check()
            assert health is not None
            assert "status" in health
        except Text2XConnectionError:
            pytest.skip("API server not available")


@pytest.mark.asyncio
async def test_list_providers(base_url, api_key):
    """Test listing providers."""
    async with Text2XClient(base_url, api_key) as client:
        try:
            providers = await client.list_providers()
            assert isinstance(providers, list)
        except Text2XConnectionError:
            pytest.skip("API server not available")


@pytest.mark.asyncio
async def test_query_flow(base_url, api_key):
    """Test complete query flow."""
    async with Text2XClient(base_url, api_key) as client:
        try:
            # Get providers
            providers = await client.list_providers()
            if not providers:
                pytest.skip("No providers configured")

            provider_id = providers[0].id

            # Run a query
            response = await client.query(
                provider_id=provider_id,
                query="Show me all records, limit to 5",
                max_iterations=3,
            )

            assert response.generated_query is not None
            assert 0 <= response.confidence_score <= 1
            assert response.iterations >= 1

            # Get conversation
            conversation = await client.get_conversation(response.conversation_id)
            assert conversation.id == response.conversation_id

            # Submit feedback
            await client.submit_feedback(
                conversation_id=response.conversation_id,
                rating=5,
                is_query_correct=True,
            )

        except Text2XConnectionError:
            pytest.skip("API server not available")


@pytest.mark.asyncio
async def test_websocket_streaming(base_url, api_key):
    """Test WebSocket streaming."""
    # Convert to WebSocket URL
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")

    try:
        async with WebSocketClient(ws_url, api_key) as ws_client:
            # Get providers first via HTTP
            async with Text2XClient(base_url, api_key) as client:
                providers = await client.list_providers()
                if not providers:
                    pytest.skip("No providers configured")

                provider_id = providers[0].id

            # Stream query
            events = []
            async for event in ws_client.query_stream(
                provider_id=provider_id,
                query="Show me all records, limit to 3",
            ):
                events.append(event)

            assert len(events) > 0
            assert events[-1].is_result or events[-1].is_error

    except Text2XConnectionError:
        pytest.skip("API server not available")


@pytest.mark.asyncio
async def test_multi_turn_conversation(base_url, api_key):
    """Test multi-turn conversation."""
    async with Text2XClient(base_url, api_key) as client:
        try:
            providers = await client.list_providers()
            if not providers:
                pytest.skip("No providers configured")

            provider_id = providers[0].id

            # Turn 1
            response1 = await client.query(
                provider_id=provider_id,
                query="Show me all data",
            )

            conversation_id = response1.conversation_id

            # Turn 2 - refine
            response2 = await client.query(
                provider_id=provider_id,
                query="Limit to 10 rows",
                conversation_id=conversation_id,
            )

            # Should be same conversation
            assert response2.conversation_id == conversation_id

            # Get conversation history
            conversation = await client.get_conversation(conversation_id)
            assert conversation.turn_count >= 2

        except Text2XConnectionError:
            pytest.skip("API server not available")


@pytest.mark.asyncio
async def test_rag_example_management(base_url, api_key):
    """Test RAG example management."""
    async with Text2XClient(base_url, api_key) as client:
        try:
            providers = await client.list_providers()
            if not providers:
                pytest.skip("No providers configured")

            provider_id = providers[0].id

            # Add an example
            example = await client.add_example(
                provider_id=provider_id,
                natural_language_query="Show me test data",
                generated_query="SELECT * FROM test LIMIT 10;",
                is_good_example=True,
                involved_tables=["test"],
            )

            assert example.id is not None
            assert example.provider_id == provider_id

            # List examples
            examples = await client.list_examples(
                provider_id=provider_id,
                limit=10,
            )

            assert isinstance(examples, list)

        except Text2XConnectionError:
            pytest.skip("API server not available")
