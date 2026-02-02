"""WebSocket handler for streaming query processing."""
import logging
from typing import AsyncGenerator, Optional, Any
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, ValidationError

from text2x.api.models import (
    QueryOptions,
    QueryResponse,
    TraceLevel,
    ValidationStatus,
)
from text2x.config import settings
from text2x.agents.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)


# WebSocket Message Models
class WebSocketQueryRequest(BaseModel):
    """Request model for WebSocket query processing."""

    provider_id: str = Field(
        default="demo",
        min_length=1,
        max_length=100,
        description="ID of the database provider/connection (default: demo mode)",
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural language query",
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="Conversation ID for multi-turn dialogue",
    )
    options: QueryOptions = Field(
        default_factory=QueryOptions,
        description="Optional query processing parameters",
    )


class WebSocketEvent(BaseModel):
    """Base model for WebSocket events."""

    type: str = Field(..., description="Event type")
    data: dict = Field(default_factory=dict, description="Event data")
    trace: Optional[dict] = Field(default=None, description="Trace information if enabled")


# Event Types
class EventType:
    """WebSocket event types."""

    PROGRESS = "progress"
    CLARIFICATION = "clarification"
    RESULT = "result"
    ERROR = "error"


class ProgressStage:
    """Progress stages during query processing."""

    STARTED = "started"
    SCHEMA_RETRIEVAL = "schema_retrieval"
    RAG_SEARCH = "rag_search"
    QUERY_GENERATION = "query_generation"
    VALIDATION = "validation"
    EXECUTION = "execution"
    COMPLETED = "completed"


async def handle_websocket_query(
    websocket: WebSocket,
    request: WebSocketQueryRequest,
    orchestrator: OrchestratorAgent,
) -> None:
    """
    Process a query request and stream events to the WebSocket client.

    Args:
        websocket: WebSocket connection
        request: Query request with natural language input
        orchestrator: Orchestrator instance (injected from app state)

    Yields:
        WebSocketEvent objects representing progress, clarification needs, results, or errors
    """
    try:
        # Merge request options with defaults
        enable_execution = (
            request.options.enable_execution
            if request.options.enable_execution is not None
            else settings.enable_execution
        )
        trace_level = request.options.trace_level

        # Generate conversation ID if not provided
        conversation_id = request.conversation_id

        logger.info(
            f"WebSocket query processing started: provider={request.provider_id}, "
            f"conversation_id={conversation_id}, query='{request.query[:50]}...'"
        )

        # Stream events from orchestrator
        async for event in orchestrator.process_query_stream(
            user_query=request.query,
            provider_id=request.provider_id,
            conversation_id=conversation_id,
            enable_execution=enable_execution,
            trace_level=trace_level.value,
            annotations={}
        ):
            # Send event to WebSocket client
            await send_event(
                websocket,
                event["type"],
                event["data"],
                trace=event.get("trace") if trace_level != TraceLevel.NONE else None,
                trace_level=trace_level,
            )

        logger.info(f"WebSocket query processing completed")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during query processing")
        raise
    except ValidationError as e:
        logger.warning(f"Invalid WebSocket request: {e}")
        await send_event(
            websocket,
            EventType.ERROR,
            {
                "error": "validation_error",
                "message": "Invalid request parameters",
                "details": {"errors": e.errors()},
            },
            trace_level=TraceLevel.NONE,
        )
    except Exception as e:
        logger.error(f"Error during WebSocket query processing: {e}", exc_info=True)
        await send_event(
            websocket,
            EventType.ERROR,
            {
                "error": "processing_error",
                "message": "Failed to process query",
                "details": {"error": str(e)} if settings.debug else {},
            },
            trace_level=TraceLevel.NONE,
        )


async def send_event(
    websocket: WebSocket,
    event_type: str,
    data: dict,
    trace: Optional[dict] = None,
    trace_level: TraceLevel = TraceLevel.NONE,
) -> None:
    """
    Send an event to the WebSocket client.

    Args:
        websocket: WebSocket connection
        event_type: Type of event (progress, clarification, result, error)
        data: Event data
        trace: Optional trace information
        trace_level: Trace level setting
    """
    event = WebSocketEvent(
        type=event_type,
        data=data,
        trace=trace if trace_level != TraceLevel.NONE else None,
    )

    try:
        await websocket.send_json(event.model_dump(mode="json", exclude_none=True))
    except Exception as e:
        logger.error(f"Failed to send WebSocket event: {e}", exc_info=True)
        raise
