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
from text2x.api.state import app_state
from text2x.config import settings

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
) -> None:
    """
    Process a query request and stream events to the WebSocket client using AgentCore.

    Args:
        websocket: WebSocket connection
        request: Query request with natural language input

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
        conversation_id = request.conversation_id or uuid4()

        logger.info(
            f"WebSocket query processing started: provider={request.provider_id}, "
            f"conversation_id={conversation_id}, query='{request.query[:50]}...'"
        )

        # Send started event
        await send_event(
            websocket,
            EventType.PROGRESS,
            {
                "stage": "started",
                "message": "Query processing started",
                "progress": 0.0
            },
            trace_level=trace_level,
        )

        # Get AgentCore runtime
        runtime = app_state.agentcore
        if not runtime or not runtime.is_started:
            raise RuntimeError("AgentCore not initialized")

        # Get or create QueryAgent instance
        from text2x.agentcore.agents.query import QueryAgent
        from text2x.repositories.provider import ProviderRepository
        from text2x.providers.factory import get_provider_instance

        agent_name = f"query_{request.provider_id}"

        # Check if agent already exists
        if agent_name not in runtime.agents:
            # Get provider
            provider_repo = ProviderRepository()
            provider_uuid = UUID(request.provider_id)
            provider = await provider_repo.get_by_id(provider_uuid)

            if not provider:
                raise ValueError(f"Provider {request.provider_id} not found")

            # Create agent instance
            agent = QueryAgent(runtime, agent_name)

            # Set provider on agent
            query_provider = await get_provider_instance(provider)
            agent.set_provider(query_provider)

            # Register agent with runtime
            runtime.agents[agent_name] = agent
            logger.info(f"Created QueryAgent instance: {agent_name}")
        else:
            agent = runtime.agents[agent_name]

        # Send progress event
        await send_event(
            websocket,
            EventType.PROGRESS,
            {
                "stage": "query_generation",
                "message": "Generating query...",
                "progress": 0.3
            },
            trace_level=trace_level,
        )

        # Get schema context
        provider_repo = ProviderRepository()
        provider = await provider_repo.get_by_id(UUID(request.provider_id))
        schema_context = {}

        if provider:
            try:
                schema = await provider.get_schema()
                if schema:
                    schema_context["tables"] = [
                        {
                            "name": table.name,
                            "columns": [
                                {"name": col.name, "type": col.type}
                                for col in table.columns
                            ],
                        }
                        for table in schema.tables
                    ]
            except Exception as e:
                logger.warning(f"Failed to get schema: {e}")

        # Process query through QueryAgent
        agent_result = await agent.process({
            "user_message": request.query,
            "provider_id": request.provider_id,
            "schema_context": schema_context,
            "enable_execution": enable_execution,
            "reset_conversation": not request.conversation_id,
        })

        # Send completion progress
        await send_event(
            websocket,
            EventType.PROGRESS,
            {
                "stage": "completed",
                "message": "Query processing completed",
                "progress": 1.0
            },
            trace_level=trace_level,
        )

        # Build execution result if available
        execution_result = agent_result.get("execution_result")
        execution_data = None
        if execution_result:
            execution_data = {
                "success": execution_result.get("success", False),
                "row_count": execution_result.get("row_count", 0),
                "execution_time_ms": execution_result.get("execution_time_ms", 0),
                "error": execution_result.get("error"),
            }

        # Send final result
        await send_event(
            websocket,
            EventType.RESULT,
            {
                "stage": "completed",
                "message": "Query processing completed",
                "conversation_id": str(conversation_id),
                "generated_query": agent_result.get("generated_query", ""),
                "query_explanation": agent_result.get("query_explanation", ""),
                "execution_result": execution_data,
            },
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
