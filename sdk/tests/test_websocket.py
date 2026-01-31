"""Tests for WebSocketClient."""

import pytest
import json
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from text2x_client.websocket import (
    WebSocketClient,
    WebSocketManager,
    StreamEvent,
    WebSocketError,
    WebSocketConnectionError,
    WebSocketMessageError,
)


@pytest.fixture
def mock_ws_client():
    """Create a WebSocketClient with mocked websocket."""
    client = WebSocketClient(base_url="ws://localhost:8000", api_key="test-key")
    client._ws = AsyncMock()
    client._connected = True
    return client


def test_stream_event_properties():
    """Test StreamEvent properties."""
    # Progress event
    progress = StreamEvent("progress", {"step": "schema_retrieval"})
    assert progress.is_progress
    assert not progress.is_clarification
    assert not progress.is_result
    assert not progress.is_error

    # Clarification event
    clarification = StreamEvent("clarification", {"questions": ["Which table?"]})
    assert clarification.is_clarification
    assert not clarification.is_progress

    # Result event
    result = StreamEvent("result", {"generated_query": "SELECT * FROM orders;"})
    assert result.is_result
    assert not result.is_error

    # Error event
    error = StreamEvent("error", {"message": "Connection failed"})
    assert error.is_error
    assert not error.is_result


def test_websocket_client_initialization():
    """Test WebSocket client initialization."""
    # Test with http:// prefix
    client = WebSocketClient(base_url="http://localhost:8000")
    assert client.base_url == "ws://localhost:8000"

    # Test with https:// prefix
    client = WebSocketClient(base_url="https://localhost:8000")
    assert client.base_url == "wss://localhost:8000"

    # Test with ws:// prefix
    client = WebSocketClient(base_url="ws://localhost:8000")
    assert client.base_url == "ws://localhost:8000"

    # Test with API key
    client = WebSocketClient(base_url="ws://localhost:8000", api_key="test-key")
    assert client.api_key == "test-key"


@pytest.mark.asyncio
async def test_websocket_connect():
    """Test WebSocket connection."""
    with patch("text2x_client.websocket.websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        # Make the mock awaitable
        async def mock_connect_impl(*args, **kwargs):
            return mock_ws
        mock_connect.side_effect = mock_connect_impl

        client = WebSocketClient("ws://localhost:8000")
        await client.connect()

        assert client._connected
        assert client._ws == mock_ws
        mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_close(mock_ws_client):
    """Test WebSocket close."""
    await mock_ws_client.close()

    assert not mock_ws_client._connected
    assert mock_ws_client._ws is None


@pytest.mark.asyncio
async def test_websocket_send_message(mock_ws_client):
    """Test sending WebSocket message."""
    message = {"provider_id": "postgres_main", "query": "Show me orders"}

    await mock_ws_client._send_message(message)

    mock_ws_client._ws.send.assert_called_once()
    sent_data = mock_ws_client._ws.send.call_args[0][0]
    assert json.loads(sent_data) == message


@pytest.mark.asyncio
async def test_websocket_send_message_not_connected():
    """Test sending message when not connected."""
    client = WebSocketClient("ws://localhost:8000")

    with pytest.raises(WebSocketConnectionError):
        await client._send_message({"test": "data"})


@pytest.mark.asyncio
async def test_websocket_receive_message(mock_ws_client):
    """Test receiving WebSocket message."""
    test_message = {"type": "progress", "data": {"step": "schema_retrieval"}}
    mock_ws_client._ws.recv.return_value = json.dumps(test_message)

    message = await mock_ws_client._receive_message()

    assert message == test_message


@pytest.mark.asyncio
async def test_websocket_receive_message_invalid_json(mock_ws_client):
    """Test receiving invalid JSON message."""
    mock_ws_client._ws.recv.return_value = "invalid json"

    with pytest.raises(WebSocketMessageError):
        await mock_ws_client._receive_message()


@pytest.mark.asyncio
async def test_query_stream(mock_ws_client):
    """Test query streaming."""
    # Mock responses
    messages = [
        {"type": "progress", "data": {"step": "schema_retrieval"}},
        {"type": "progress", "data": {"step": "query_generation"}},
        {
            "type": "result",
            "data": {
                "conversation_id": str(uuid4()),
                "generated_query": "SELECT * FROM orders;",
                "confidence_score": 0.95,
            },
        },
    ]

    mock_ws_client._ws.recv.side_effect = [json.dumps(msg) for msg in messages]

    events = []
    async for event in mock_ws_client.query_stream(
        provider_id="postgres_main",
        query="Show me orders",
    ):
        events.append(event)

    assert len(events) == 3
    assert events[0].is_progress
    assert events[1].is_progress
    assert events[2].is_result


@pytest.mark.asyncio
async def test_query_stream_with_error(mock_ws_client):
    """Test query streaming with error."""
    messages = [
        {"type": "progress", "data": {"step": "schema_retrieval"}},
        {"type": "error", "data": {"message": "Provider not found"}},
    ]

    mock_ws_client._ws.recv.side_effect = [json.dumps(msg) for msg in messages]

    events = []
    async for event in mock_ws_client.query_stream(
        provider_id="invalid",
        query="Show me orders",
    ):
        events.append(event)

    assert len(events) == 2
    assert events[0].is_progress
    assert events[1].is_error
    assert events[1].data["message"] == "Provider not found"


@pytest.mark.asyncio
async def test_query_stream_auto_connect():
    """Test query stream auto-connects if not connected."""
    with patch("text2x_client.websocket.websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        # Make the mock awaitable
        async def mock_connect_impl(*args, **kwargs):
            return mock_ws
        mock_connect.side_effect = mock_connect_impl

        # Mock recv to return a result immediately
        mock_ws.recv.return_value = json.dumps(
            {
                "type": "result",
                "data": {"generated_query": "SELECT * FROM orders;"},
            }
        )

        client = WebSocketClient("ws://localhost:8000")

        events = []
        async for event in client.query_stream(
            provider_id="postgres_main",
            query="Show me orders",
        ):
            events.append(event)

        # Should have connected automatically
        mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_query_stream_with_clarification(mock_ws_client):
    """Test query streaming with clarification handling."""
    # Mock clarification callback
    clarification_callback = AsyncMock(return_value="I mean the orders table")

    # Mock messages for first query (needs clarification)
    first_messages = [
        {
            "type": "clarification",
            "data": {
                "questions": ["Which table do you mean?"],
                "conversation_id": str(uuid4()),
            },
        },
    ]

    # Mock messages for second query (after clarification)
    second_messages = [
        {
            "type": "result",
            "data": {
                "conversation_id": str(uuid4()),
                "generated_query": "SELECT * FROM orders;",
                "confidence_score": 0.95,
            },
        },
    ]

    # Set up mock to return messages in sequence
    mock_ws_client._ws.recv.side_effect = [
        json.dumps(msg) for msg in first_messages + second_messages
    ]

    result = await mock_ws_client.query_stream_with_clarification(
        provider_id="postgres_main",
        query="Show me the data",
        clarification_callback=clarification_callback,
    )

    assert result.is_result
    assert result.data["generated_query"] == "SELECT * FROM orders;"
    clarification_callback.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_manager():
    """Test WebSocketManager."""
    manager = WebSocketManager(
        base_url="ws://localhost:8000",
        api_key="test-key",
        pool_size=3,
    )

    assert manager.pool_size == 3
    assert not manager._initialized

    # Initialize pool
    await manager._initialize_pool()

    assert manager._initialized
    assert manager._pool.qsize() == 3

    # Clean up
    await manager.close_all()
    assert manager._pool.empty()


@pytest.mark.asyncio
async def test_websocket_manager_get_client():
    """Test getting client from manager."""
    with patch("text2x_client.websocket.websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        # Make the mock awaitable
        async def mock_connect_impl(*args, **kwargs):
            return mock_ws
        mock_connect.side_effect = mock_connect_impl

        manager = WebSocketManager(
            base_url="ws://localhost:8000",
            pool_size=2,
        )

        # Get a client (note: get_client returns awaitable)
        pooled_client = await manager.get_client()
        async with pooled_client as client:
            assert isinstance(client, WebSocketClient)

        # Client should be returned to pool
        assert manager._pool.qsize() == 2

        await manager.close_all()


@pytest.mark.asyncio
async def test_stream_event_with_trace():
    """Test StreamEvent with trace data."""
    trace_data = {
        "schema_agent": {"latency_ms": 100},
        "query_builder_agent": {"latency_ms": 200},
    }

    event = StreamEvent(
        event_type="result",
        data={"generated_query": "SELECT * FROM orders;"},
        trace=trace_data,
    )

    assert event.trace == trace_data
    assert event.is_result
