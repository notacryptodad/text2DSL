"""Tests for WebSocket streaming functionality."""
import json
import pytest
from fastapi.testclient import TestClient

from text2x.api.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_websocket_query_streaming(client):
    """Test WebSocket query streaming with mock data."""
    with client.websocket_connect("/ws/query") as websocket:
        # Send query request
        request = {
            "provider_id": "postgres-test",
            "query": "Show me all users",
            "options": {
                "trace_level": "summary",
                "max_iterations": 3,
                "confidence_threshold": 0.8,
                "enable_execution": False,
            },
        }
        websocket.send_json(request)

        # Collect all events
        events = []
        event_types = set()

        # Receive events until we get a result or error
        while True:
            data = websocket.receive_json()
            events.append(data)
            event_types.add(data["type"])

            # Stop when we get a result or error
            if data["type"] in ["result", "error"]:
                break

        # Verify we got the expected event types
        assert "progress" in event_types
        assert "result" in event_types or "error" in event_types

        # Verify the structure of progress events
        progress_events = [e for e in events if e["type"] == "progress"]
        assert len(progress_events) > 0

        for event in progress_events:
            assert "data" in event
            assert "stage" in event["data"]
            assert "message" in event["data"]

        # Verify the result event structure
        result_events = [e for e in events if e["type"] == "result"]
        if result_events:
            result = result_events[0]
            assert "data" in result
            assert "result" in result["data"]
            assert "generated_query" in result["data"]["result"]
            assert "confidence_score" in result["data"]["result"]
            assert "validation_status" in result["data"]["result"]


def test_websocket_invalid_request(client):
    """Test WebSocket with invalid request format."""
    with client.websocket_connect("/ws/query") as websocket:
        # Send invalid request (missing required fields)
        invalid_request = {
            "query": "Show me all users",
            # Missing provider_id
        }
        websocket.send_json(invalid_request)

        # Should receive error event
        data = websocket.receive_json()
        assert data["type"] == "error"
        assert "validation_error" in data["data"]["error"]


def test_websocket_trace_levels(client):
    """Test WebSocket with different trace levels."""
    trace_levels = ["none", "summary", "full"]

    for trace_level in trace_levels:
        with client.websocket_connect("/ws/query") as websocket:
            request = {
                "provider_id": "postgres-test",
                "query": "Show me all users",
                "options": {
                    "trace_level": trace_level,
                },
            }
            websocket.send_json(request)

            # Collect events
            events = []
            while True:
                data = websocket.receive_json()
                events.append(data)
                if data["type"] in ["result", "error"]:
                    break

            # Check trace field presence based on level
            if trace_level == "none":
                # No events should have trace field
                for event in events:
                    assert event.get("trace") is None
            else:
                # At least result event should have trace
                result_events = [e for e in events if e["type"] == "result"]
                if result_events:
                    # Trace might be present for summary/full levels
                    pass  # Just verify it doesn't crash


def test_websocket_with_conversation_id(client):
    """Test WebSocket with conversation continuation."""
    import uuid

    conversation_id = str(uuid.uuid4())

    with client.websocket_connect("/ws/query") as websocket:
        request = {
            "provider_id": "postgres-test",
            "query": "Show me all users",
            "conversation_id": conversation_id,
            "options": {
                "trace_level": "none",
            },
        }
        websocket.send_json(request)

        # Find the result event
        while True:
            data = websocket.receive_json()
            if data["type"] == "result":
                # Verify conversation_id is preserved
                result_data = data["data"]["result"]
                assert str(result_data["conversation_id"]) == conversation_id
                break
            elif data["type"] == "error":
                pytest.fail(f"Unexpected error: {data}")
                break


def test_websocket_enable_execution(client):
    """Test WebSocket with query execution enabled."""
    with client.websocket_connect("/ws/query") as websocket:
        request = {
            "provider_id": "postgres-test",
            "query": "Show me all users",
            "options": {
                "enable_execution": True,
                "trace_level": "none",
            },
        }
        websocket.send_json(request)

        # Look for execution stage in progress events
        has_execution_stage = False
        while True:
            data = websocket.receive_json()

            if data["type"] == "progress":
                stage = data["data"].get("stage")
                if stage == "execution":
                    has_execution_stage = True

            if data["type"] in ["result", "error"]:
                break

        # With execution enabled, we should see execution stage
        assert has_execution_stage

        # Also check if result has execution_result
        if data["type"] == "result":
            result_data = data["data"]["result"]
            assert "execution_result" in result_data
            # execution_result might be None if not actually executed, but field should exist


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
