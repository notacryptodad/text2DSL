"""WebSocket client for streaming Text2X query processing."""

import asyncio
import json
from typing import Any, AsyncIterator, Optional
from uuid import UUID

import websockets
from pydantic import ValidationError
from websockets.client import WebSocketClientProtocol

from .models import QueryOptions, QueryRequest


class WebSocketError(Exception):
    """Base exception for WebSocket client errors."""

    pass


class WebSocketConnectionError(WebSocketError):
    """Exception raised when WebSocket connection fails."""

    pass


class WebSocketMessageError(WebSocketError):
    """Exception raised when message parsing fails."""

    pass


class StreamEvent:
    """Represents a streaming event from the WebSocket."""

    def __init__(self, event_type: str, data: dict[str, Any], trace: Optional[dict[str, Any]] = None):
        self.type = event_type
        self.data = data
        self.trace = trace

    def __repr__(self) -> str:
        return f"StreamEvent(type={self.type}, data={self.data})"

    @property
    def is_progress(self) -> bool:
        """Check if this is a progress event."""
        return self.type == "progress"

    @property
    def is_clarification(self) -> bool:
        """Check if this is a clarification request."""
        return self.type == "clarification"

    @property
    def is_result(self) -> bool:
        """Check if this is the final result."""
        return self.type == "result"

    @property
    def is_error(self) -> bool:
        """Check if this is an error event."""
        return self.type == "error"


class WebSocketClient:
    """WebSocket client for streaming Text2X query processing.

    This client provides real-time streaming of query processing events,
    including progress updates, clarification requests, and final results.

    Args:
        base_url: Base URL of the Text2X API (e.g., "ws://localhost:8000")
        api_key: Optional API key for authentication

    Example:
        ```python
        async with WebSocketClient("ws://localhost:8000") as ws_client:
            async for event in ws_client.query_stream(
                provider_id="postgres_main",
                query="Show me all orders from last month"
            ):
                if event.is_progress:
                    print(f"Progress: {event.data}")
                elif event.is_result:
                    print(f"Result: {event.data}")
        ```
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize the WebSocket client."""
        # Convert http(s) to ws(s) if needed
        if base_url.startswith("http://"):
            base_url = base_url.replace("http://", "ws://")
        elif base_url.startswith("https://"):
            base_url = base_url.replace("https://", "wss://")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        if self._connected:
            return

        ws_url = f"{self.base_url}/ws/query"
        extra_headers = {}

        if self.api_key:
            extra_headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            self._ws = await websockets.connect(
                ws_url,
                extra_headers=extra_headers,
                ping_interval=20,
                ping_timeout=10,
            )
            self._connected = True
        except Exception as e:
            raise WebSocketConnectionError(f"Failed to connect to WebSocket: {e}") from e

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self._ws and self._connected:
            await self._ws.close()
            self._connected = False
            self._ws = None

    async def _send_message(self, message: dict[str, Any]) -> None:
        """Send a message through the WebSocket."""
        if not self._ws or not self._connected:
            raise WebSocketConnectionError("WebSocket is not connected")

        try:
            await self._ws.send(json.dumps(message))
        except Exception as e:
            raise WebSocketError(f"Failed to send message: {e}") from e

    async def _receive_message(self) -> dict[str, Any]:
        """Receive a message from the WebSocket."""
        if not self._ws or not self._connected:
            raise WebSocketConnectionError("WebSocket is not connected")

        try:
            message = await self._ws.recv()
            return json.loads(message)
        except websockets.exceptions.ConnectionClosed as e:
            self._connected = False
            raise WebSocketConnectionError(f"WebSocket connection closed: {e}") from e
        except json.JSONDecodeError as e:
            raise WebSocketMessageError(f"Failed to parse message: {e}") from e
        except Exception as e:
            raise WebSocketError(f"Failed to receive message: {e}") from e

    async def query_stream(
        self,
        provider_id: str,
        query: str,
        conversation_id: Optional[UUID] = None,
        **options,
    ) -> AsyncIterator[StreamEvent]:
        """Stream query processing events.

        Args:
            provider_id: ID of the database provider/connection
            query: Natural language query
            conversation_id: Optional conversation ID for multi-turn dialogue
            **options: Additional query options (max_iterations, confidence_threshold, etc.)

        Yields:
            StreamEvent objects with type and data

        Raises:
            WebSocketConnectionError: If connection fails or is closed
            WebSocketMessageError: If message parsing fails

        Example:
            ```python
            async for event in ws_client.query_stream(
                provider_id="postgres_main",
                query="Show me all orders",
                trace_level="summary"
            ):
                if event.is_progress:
                    print(f"Step: {event.data['step']}")
                elif event.is_clarification:
                    print(f"Questions: {event.data['questions']}")
                elif event.is_result:
                    print(f"Query: {event.data['generated_query']}")
                elif event.is_error:
                    print(f"Error: {event.data['message']}")
                    break
            ```
        """
        # Ensure we're connected
        if not self._connected:
            await self.connect()

        # Build and validate request
        try:
            request = QueryRequest(
                provider_id=provider_id,
                query=query,
                conversation_id=conversation_id,
                options=QueryOptions(**options),
            )
        except ValidationError as e:
            raise WebSocketMessageError(f"Invalid request: {e}") from e

        # Send query request
        await self._send_message(request.model_dump(mode="json"))

        # Stream events until we get a result or error
        while True:
            try:
                message = await self._receive_message()

                event_type = message.get("type")
                event_data = message.get("data", {})
                event_trace = message.get("trace")

                if not event_type:
                    raise WebSocketMessageError("Received message without 'type' field")

                event = StreamEvent(
                    event_type=event_type,
                    data=event_data,
                    trace=event_trace,
                )

                yield event

                # Stop streaming after result or error
                if event.is_result or event.is_error:
                    break

            except WebSocketConnectionError:
                # Connection closed, stop streaming
                break

    async def query_stream_with_clarification(
        self,
        provider_id: str,
        query: str,
        conversation_id: Optional[UUID] = None,
        clarification_callback: Optional[callable] = None,
        **options,
    ) -> StreamEvent:
        """Stream query processing with automatic clarification handling.

        This method automatically handles clarification requests by calling
        the provided callback function and sending the response.

        Args:
            provider_id: ID of the database provider/connection
            query: Natural language query
            conversation_id: Optional conversation ID for multi-turn dialogue
            clarification_callback: Async function to call for clarifications.
                Should accept (questions: list[str]) and return (answer: str)
            **options: Additional query options

        Returns:
            Final StreamEvent with result or error

        Example:
            ```python
            async def handle_clarification(questions):
                print("Questions:", questions)
                return input("Your answer: ")

            result = await ws_client.query_stream_with_clarification(
                provider_id="postgres_main",
                query="Show me orders",
                clarification_callback=handle_clarification
            )

            if result.is_result:
                print(f"Query: {result.data['generated_query']}")
            ```
        """
        current_conversation_id = conversation_id
        current_query = query

        while True:
            final_event = None

            async for event in self.query_stream(
                provider_id=provider_id,
                query=current_query,
                conversation_id=current_conversation_id,
                **options,
            ):
                if event.is_clarification and clarification_callback:
                    # Get clarification from user
                    questions = event.data.get("questions", [])
                    answer = await clarification_callback(questions)

                    # Update for next iteration
                    current_query = answer
                    current_conversation_id = event.data.get("conversation_id")
                    break

                elif event.is_result or event.is_error:
                    final_event = event
                    break

            # If we got a final result or error, return it
            if final_event:
                return final_event

            # If no clarification callback and we need clarification, return the event
            if not clarification_callback:
                async for event in self.query_stream(
                    provider_id=provider_id,
                    query=current_query,
                    conversation_id=current_conversation_id,
                    **options,
                ):
                    if event.is_clarification or event.is_result or event.is_error:
                        return event


class WebSocketManager:
    """Manager for multiple WebSocket connections with connection pooling.

    This is useful for applications that need to handle multiple concurrent
    query streams.

    Example:
        ```python
        manager = WebSocketManager(base_url="ws://localhost:8000")

        async with manager.get_client() as client:
            async for event in client.query_stream(...):
                print(event)
        ```
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, pool_size: int = 5):
        """Initialize the WebSocket manager."""
        self.base_url = base_url
        self.api_key = api_key
        self.pool_size = pool_size
        self._pool: asyncio.Queue[WebSocketClient] = asyncio.Queue(maxsize=pool_size)
        self._initialized = False

    async def _initialize_pool(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return

        for _ in range(self.pool_size):
            client = WebSocketClient(self.base_url, self.api_key)
            await self._pool.put(client)

        self._initialized = True

    async def get_client(self) -> WebSocketClient:
        """Get a client from the pool.

        Returns:
            WebSocketClient instance

        Example:
            ```python
            async with manager.get_client() as client:
                # Use client
                pass
            ```
        """
        if not self._initialized:
            await self._initialize_pool()

        client = await self._pool.get()
        return _PooledWebSocketClient(client, self._pool)

    async def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                client = self._pool.get_nowait()
                await client.close()
            except asyncio.QueueEmpty:
                break


class _PooledWebSocketClient:
    """Wrapper for pooled WebSocket client that returns to pool on close."""

    def __init__(self, client: WebSocketClient, pool: asyncio.Queue):
        self._client = client
        self._pool = pool

    async def __aenter__(self):
        await self._client.connect()
        return self._client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Return to pool instead of closing
        await self._pool.put(self._client)
