"""WebSocket handler for streaming query processing."""
import logging
from typing import AsyncGenerator, Optional
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

logger = logging.getLogger(__name__)


# WebSocket Message Models
class WebSocketQueryRequest(BaseModel):
    """Request model for WebSocket query processing."""

    provider_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the database provider/connection",
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
    Process a query request and stream events to the WebSocket client.

    Args:
        websocket: WebSocket connection
        request: Query request with natural language input

    Yields:
        WebSocketEvent objects representing progress, clarification needs, results, or errors
    """
    try:
        # Merge request options with defaults
        max_iterations = request.options.max_iterations or settings.max_iterations
        confidence_threshold = (
            request.options.confidence_threshold or settings.confidence_threshold
        )
        enable_execution = (
            request.options.enable_execution
            if request.options.enable_execution is not None
            else settings.enable_execution
        )
        trace_level = request.options.trace_level

        # Generate IDs
        conversation_id = request.conversation_id or uuid4()
        turn_id = uuid4()

        logger.info(
            f"WebSocket query processing started: provider={request.provider_id}, "
            f"conversation_id={conversation_id}, turn_id={turn_id}"
        )

        # Send started event
        await send_event(
            websocket,
            EventType.PROGRESS,
            {
                "stage": ProgressStage.STARTED,
                "message": "Query processing started",
                "conversation_id": str(conversation_id),
                "turn_id": str(turn_id),
            },
            trace_level=trace_level,
        )

        # TODO: Integrate with actual orchestrator
        # from text2x.agents.orchestrator import QueryOrchestrator
        # orchestrator = QueryOrchestrator()
        #
        # async for event in orchestrator.process_query_stream(
        #     provider_id=request.provider_id,
        #     query=request.query,
        #     conversation_id=conversation_id,
        #     max_iterations=max_iterations,
        #     confidence_threshold=confidence_threshold,
        #     enable_execution=enable_execution,
        #     trace_level=trace_level,
        # ):
        #     await send_event(
        #         websocket,
        #         event.type,
        #         event.data,
        #         trace=event.trace if trace_level != TraceLevel.NONE else None,
        #         trace_level=trace_level,
        #     )

        # Mock streaming events for now (replace with actual orchestrator integration)
        async for event in mock_query_stream(
            request,
            conversation_id,
            turn_id,
            max_iterations,
            confidence_threshold,
            enable_execution,
            trace_level,
        ):
            await send_event(
                websocket,
                event["type"],
                event["data"],
                trace=event.get("trace"),
                trace_level=trace_level,
            )

        logger.info(f"WebSocket query processing completed: turn_id={turn_id}")

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
        await websocket.send_json(event.model_dump(exclude_none=True))
    except Exception as e:
        logger.error(f"Failed to send WebSocket event: {e}", exc_info=True)
        raise


async def mock_query_stream(
    request: WebSocketQueryRequest,
    conversation_id: UUID,
    turn_id: UUID,
    max_iterations: int,
    confidence_threshold: float,
    enable_execution: bool,
    trace_level: TraceLevel,
) -> AsyncGenerator[dict, None]:
    """
    Mock query processing stream for testing.
    This will be replaced with actual orchestrator integration.

    Args:
        request: Query request
        conversation_id: Conversation ID
        turn_id: Turn ID
        max_iterations: Max iterations
        confidence_threshold: Confidence threshold
        enable_execution: Whether to execute queries
        trace_level: Trace level

    Yields:
        Event dictionaries
    """
    import asyncio

    # Schema retrieval progress
    await asyncio.sleep(0.3)
    yield {
        "type": EventType.PROGRESS,
        "data": {
            "stage": ProgressStage.SCHEMA_RETRIEVAL,
            "message": "Retrieving database schema...",
            "progress": 0.2,
        },
        "trace": (
            {
                "agent": "SchemaExpert",
                "action": "retrieving_schema",
                "details": {"tables_found": 5},
            }
            if trace_level == TraceLevel.FULL
            else None
        ),
    }

    # RAG search progress
    await asyncio.sleep(0.2)
    yield {
        "type": EventType.PROGRESS,
        "data": {
            "stage": ProgressStage.RAG_SEARCH,
            "message": "Searching for similar examples...",
            "progress": 0.4,
        },
        "trace": (
            {
                "agent": "RAGRetrieval",
                "action": "searching_examples",
                "details": {"examples_found": 3, "top_similarity": 0.87},
            }
            if trace_level == TraceLevel.FULL
            else None
        ),
    }

    # Query generation progress
    await asyncio.sleep(0.5)
    yield {
        "type": EventType.PROGRESS,
        "data": {
            "stage": ProgressStage.QUERY_GENERATION,
            "message": "Generating query...",
            "progress": 0.6,
        },
        "trace": (
            {
                "agent": "QueryBuilder",
                "action": "generating_query",
                "details": {"iteration": 1},
            }
            if trace_level == TraceLevel.FULL
            else None
        ),
    }

    # Validation progress
    await asyncio.sleep(0.2)
    yield {
        "type": EventType.PROGRESS,
        "data": {
            "stage": ProgressStage.VALIDATION,
            "message": "Validating generated query...",
            "progress": 0.8,
        },
        "trace": (
            {
                "agent": "Validator",
                "action": "validating_query",
                "details": {"checks": ["syntax", "schema", "semantics"]},
            }
            if trace_level == TraceLevel.FULL
            else None
        ),
    }

    # Execution progress (if enabled)
    if enable_execution:
        await asyncio.sleep(0.2)
        yield {
            "type": EventType.PROGRESS,
            "data": {
                "stage": ProgressStage.EXECUTION,
                "message": "Executing query...",
                "progress": 0.9,
            },
            "trace": (
                {
                    "agent": "Validator",
                    "action": "executing_query",
                    "details": {"timeout": 30},
                }
                if trace_level == TraceLevel.FULL
                else None
            ),
        }

    # Final result
    await asyncio.sleep(0.1)

    from text2x.api.models import (
        AgentTrace,
        ExecutionResult,
        ReasoningTrace,
        ValidationResult,
    )

    # Build the response
    query_response = QueryResponse(
        conversation_id=conversation_id,
        turn_id=turn_id,
        generated_query="SELECT * FROM users WHERE age > 18",
        confidence_score=0.92,
        validation_status=ValidationStatus.VALID,
        validation_result=ValidationResult(
            status=ValidationStatus.VALID,
            errors=[],
            warnings=[],
            suggestions=["Consider adding LIMIT clause for large result sets"],
        ),
        execution_result=(
            ExecutionResult(
                success=True,
                row_count=150,
                data=None,
                execution_time_ms=45,
            )
            if enable_execution
            else None
        ),
        reasoning_trace=(
            ReasoningTrace(
                schema_agent=AgentTrace(
                    agent_name="SchemaExpert",
                    latency_ms=250,
                    tokens_input=500,
                    tokens_output=800,
                    details={"tables_analyzed": ["users"]},
                ),
                rag_agent=AgentTrace(
                    agent_name="RAGRetrieval",
                    latency_ms=150,
                    tokens_input=300,
                    tokens_output=0,
                    details={"examples_retrieved": 5, "top_similarity": 0.87},
                ),
                query_builder_agent=AgentTrace(
                    agent_name="QueryBuilder",
                    latency_ms=800,
                    tokens_input=2000,
                    tokens_output=150,
                    iterations=1,
                    details={"query_type": "filter"},
                ),
                validator_agent=AgentTrace(
                    agent_name="Validator",
                    latency_ms=100,
                    tokens_input=200,
                    tokens_output=50,
                    details={"validation_checks": ["syntax", "schema"]},
                ),
                orchestrator_latency_ms=1300,
                total_tokens_input=3000,
                total_tokens_output=1000,
                total_cost_usd=0.012,
            )
            if trace_level != TraceLevel.NONE
            else None
        ),
        needs_clarification=False,
        clarification_questions=[],
        iterations=1,
    )

    yield {
        "type": EventType.RESULT,
        "data": {
            "stage": ProgressStage.COMPLETED,
            "message": "Query processing completed",
            "progress": 1.0,
            "result": query_response.model_dump(exclude_none=True),
        },
        "trace": (
            {
                "total_latency_ms": 1300,
                "total_tokens": 4000,
                "total_cost_usd": 0.012,
            }
            if trace_level == TraceLevel.SUMMARY
            else None
        ),
    }
