"""Query processing endpoints."""
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from text2x.api.models import (
    ConversationResponse,
    ConversationTurnResponse,
    ErrorResponse,
    FeedbackRequest,
    QueryRequest,
    QueryResponse,
    ValidationStatus,
)
from text2x.config import settings
from text2x.utils.observability import (
    async_log_context,
    record_query_success,
    record_query_failure,
    record_validation_result,
    record_user_satisfaction,
    record_query_latency,
    record_iterations,
    record_agent_latency,
    record_tokens_used,
    record_tokens_by_agent,
    record_cost,
    record_rag_retrieval,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# Global orchestrator instance (initialized on app startup)
_orchestrator: Optional[any] = None


def set_orchestrator(orchestrator):
    """Set the global orchestrator instance (called from app startup)."""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator():
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError(
            "Orchestrator not initialized. Make sure to call set_orchestrator() "
            "during app startup."
        )
    return _orchestrator


@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Process natural language query",
    description="Convert natural language to executable database query using multi-agent system",
)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a natural language query and generate executable database query.

    This endpoint orchestrates the multi-agent system to:
    1. Retrieve relevant schema context
    2. Fetch similar examples from RAG store
    3. Generate query using LLM
    4. Validate generated query
    5. Optionally execute query if enabled

    Args:
        request: Query request with natural language input

    Returns:
        QueryResponse with generated query and metadata

    Raises:
        HTTPException: For various error conditions
    """
    # Track request start time for metrics
    start_time = time.time()
    provider_type = "unknown"  # Will be determined from provider_id lookup

    try:
        # Generate IDs first for logging context
        conversation_id = request.conversation_id or uuid4()
        turn_id = uuid4()

        # Use async log context to enrich all logs in this request
        async with async_log_context(
            conversation_id=str(conversation_id),
            turn_id=str(turn_id),
            provider_id=request.provider_id,
        ):
            logger.info(
                f"Processing query for provider {request.provider_id}, "
                f"conversation_id={conversation_id}"
            )

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

            # Get orchestrator and process query
            orchestrator = get_orchestrator()

            # Prepare input for orchestrator
            orchestrator_input = {
                "user_query": request.query,
                "provider_id": request.provider_id,
                "conversation_id": conversation_id,
                "user_id": "api_user",  # TODO: Extract from authentication context
                "enable_execution": enable_execution,
                "trace_level": request.options.trace_level.value,
                "annotations": {},  # TODO: Add support for schema annotations
            }

            # Process query through orchestrator
            orchestrator_result = await orchestrator.process(orchestrator_input)

            # Extract results from orchestrator
            query_response: QueryResponse = orchestrator_result["query_response"]
            actual_conversation_id = orchestrator_result["conversation_id"]
            actual_turn_id = orchestrator_result["turn_id"]
            all_traces = orchestrator_result.get("all_traces", [])

            # Convert domain QueryResponse to API QueryResponse
            from text2x.api.models import (
                AgentTrace,
                ExecutionResult as APIExecutionResult,
                ReasoningTrace as APIReasoningTrace,
                ValidationResult as APIValidationResult,
            )

            # Convert ValidationStatus from domain to API
            api_validation_status = ValidationStatus.VALID
            if query_response.validation_status.value == "passed":
                api_validation_status = ValidationStatus.VALID
            elif query_response.validation_status.value == "failed":
                api_validation_status = ValidationStatus.INVALID
            elif query_response.validation_status.value == "pending":
                api_validation_status = ValidationStatus.UNKNOWN

            # Build validation result
            api_validation_result = APIValidationResult(
                status=api_validation_status,
                errors=[query_response.validation_result.error] if query_response.validation_result.error else [],
                warnings=[],
                suggestions=query_response.validation_result.suggestions or [],
            )

            # Build execution result if available
            api_execution_result = None
            if query_response.execution_result:
                api_execution_result = APIExecutionResult(
                    success=query_response.execution_result.success,
                    row_count=query_response.execution_result.row_count,
                    data=None,  # Don't return full data in API response
                    error_message=query_response.execution_result.error,
                    execution_time_ms=int(query_response.execution_result.execution_time_ms),
                )

            # Build reasoning trace if requested
            api_reasoning_trace = None
            if request.options.trace_level != "none" and all_traces:
                # Aggregate traces by agent
                agent_traces = {}
                total_input_tokens = 0
                total_output_tokens = 0
                total_latency = 0

                for trace in all_traces:
                    agent_name = trace.agent_name
                    if agent_name not in agent_traces:
                        agent_traces[agent_name] = {
                            "latency_ms": 0,
                            "tokens_input": 0,
                            "tokens_output": 0,
                            "iterations": 0,
                            "details": {}
                        }

                    agent_traces[agent_name]["latency_ms"] += trace.duration_ms
                    # Tokens would be extracted from trace data if available
                    total_latency += trace.duration_ms

                # Build API trace structure
                api_reasoning_trace = APIReasoningTrace(
                    schema_agent=AgentTrace(
                        agent_name="SchemaExpert",
                        latency_ms=int(agent_traces.get("SchemaExpertAgent", {}).get("latency_ms", 0)),
                        tokens_input=0,  # TODO: Extract from trace
                        tokens_output=0,
                        details=agent_traces.get("SchemaExpertAgent", {}).get("details", {}),
                    ) if "SchemaExpertAgent" in agent_traces else None,
                    rag_agent=AgentTrace(
                        agent_name="RAGRetrieval",
                        latency_ms=int(agent_traces.get("RAGRetrievalAgent", {}).get("latency_ms", 0)),
                        tokens_input=0,
                        tokens_output=0,
                        details=agent_traces.get("RAGRetrievalAgent", {}).get("details", {}),
                    ) if "RAGRetrievalAgent" in agent_traces else None,
                    query_builder_agent=AgentTrace(
                        agent_name="QueryBuilder",
                        latency_ms=int(agent_traces.get("QueryBuilderAgent", {}).get("latency_ms", 0)),
                        tokens_input=0,
                        tokens_output=0,
                        iterations=query_response.iterations,
                        details=agent_traces.get("QueryBuilderAgent", {}).get("details", {}),
                    ) if "QueryBuilderAgent" in agent_traces else None,
                    validator_agent=AgentTrace(
                        agent_name="Validator",
                        latency_ms=int(agent_traces.get("ValidatorAgent", {}).get("latency_ms", 0)),
                        tokens_input=0,
                        tokens_output=0,
                        details=agent_traces.get("ValidatorAgent", {}).get("details", {}),
                    ) if "ValidatorAgent" in agent_traces else None,
                    orchestrator_latency_ms=int(total_latency),
                    total_tokens_input=total_input_tokens,
                    total_tokens_output=total_output_tokens,
                    total_cost_usd=0.0,  # TODO: Calculate from tokens
                )

            # Build final API response
            api_response = QueryResponse(
                conversation_id=actual_conversation_id,
                turn_id=actual_turn_id,
                generated_query=query_response.generated_query,
                confidence_score=query_response.confidence_score,
                validation_status=api_validation_status,
                validation_result=api_validation_result,
                execution_result=api_execution_result,
                reasoning_trace=api_reasoning_trace,
                needs_clarification=query_response.clarification_needed,
                clarification_questions=[query_response.clarification_question] if query_response.clarification_question else [],
                iterations=query_response.iterations,
            )

            logger.info(
                f"Query processed successfully: turn_id={actual_turn_id}, "
                f"confidence={api_response.confidence_score}"
            )

            # Record metrics
            query_duration = time.time() - start_time
            provider_type = "postgresql"  # TODO: Extract from provider_id lookup

            # Success metrics
            record_query_success(provider_type)
            record_query_latency(provider_type, query_duration)
            record_iterations(provider_type, api_response.iterations)

            # Validation metrics
            is_valid = api_response.validation_status == ValidationStatus.VALID
            record_validation_result(provider_type, is_valid)

            # Cost metrics (from trace if available)
            if api_response.reasoning_trace:
                trace = api_response.reasoning_trace
                record_tokens_used("input", trace.total_tokens_input, provider_type)
                record_tokens_used("output", trace.total_tokens_output, provider_type)
                record_cost(provider_type, trace.total_cost_usd)

                # Agent-specific metrics
                if trace.schema_agent:
                    record_agent_latency("schema", trace.schema_agent.latency_ms / 1000)
                    record_tokens_by_agent(
                        "schema", "input", trace.schema_agent.tokens_input
                    )
                    record_tokens_by_agent(
                        "schema", "output", trace.schema_agent.tokens_output
                    )

                if trace.rag_agent:
                    record_agent_latency("rag", trace.rag_agent.latency_ms / 1000)
                    record_tokens_by_agent("rag", "input", trace.rag_agent.tokens_input)
                    record_tokens_by_agent("rag", "output", trace.rag_agent.tokens_output)
                    record_rag_retrieval(provider_type)

                if trace.query_builder_agent:
                    record_agent_latency(
                        "query_builder", trace.query_builder_agent.latency_ms / 1000
                    )
                    record_tokens_by_agent(
                        "query_builder", "input", trace.query_builder_agent.tokens_input
                    )
                    record_tokens_by_agent(
                        "query_builder", "output", trace.query_builder_agent.tokens_output
                    )

                if trace.validator_agent:
                    record_agent_latency(
                        "validator", trace.validator_agent.latency_ms / 1000
                    )
                    record_tokens_by_agent(
                        "validator", "input", trace.validator_agent.tokens_input
                    )
                    record_tokens_by_agent(
                        "validator", "output", trace.validator_agent.tokens_output
                    )

            # Queue for expert review if confidence is low
            if (
                settings.auto_queue_low_confidence
                and api_response.confidence_score < settings.low_confidence_threshold
            ):
                logger.info(f"Queuing turn {actual_turn_id} for expert review (low confidence)")
                # TODO: Add to review queue
                # await add_to_review_queue(actual_turn_id, "low_confidence")

            return api_response

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        record_query_failure(provider_type, "invalid_request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="invalid_request",
                message=str(e),
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        record_query_failure(provider_type, "processing_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="processing_error",
                message="Failed to process query",
                details={"error": str(e)} if settings.debug else None,
            ).model_dump(),
        )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
)
async def get_conversation(conversation_id: UUID) -> ConversationResponse:
    """
    Retrieve conversation details including all turns.

    Args:
        conversation_id: Conversation identifier

    Returns:
        Conversation details with all turns

    Raises:
        HTTPException: If conversation not found
    """
    try:
        logger.info(f"Fetching conversation {conversation_id}")

        # TODO: Fetch from database
        # from text2x.db.repositories import ConversationRepository
        # repo = ConversationRepository()
        # conversation = await repo.get_by_id(conversation_id)
        # if not conversation:
        #     raise HTTPException(status_code=404, detail="Conversation not found")

        # Mock response
        mock_response = ConversationResponse(
            id=conversation_id,
            provider_id="postgres-main",
            status="active",
            turn_count=2,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            turns=[
                ConversationTurnResponse(
                    id=uuid4(),
                    turn_number=1,
                    user_input="Show me all users",
                    generated_query="SELECT * FROM users",
                    confidence_score=0.95,
                    validation_status=ValidationStatus.VALID,
                    created_at=datetime.utcnow(),
                ),
                ConversationTurnResponse(
                    id=uuid4(),
                    turn_number=2,
                    user_input="Filter by age over 18",
                    generated_query="SELECT * FROM users WHERE age > 18",
                    confidence_score=0.92,
                    validation_status=ValidationStatus.VALID,
                    created_at=datetime.utcnow(),
                ),
            ],
        )

        return mock_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch conversation",
            ).model_dump(),
        )


@router.get(
    "/conversations/{conversation_id}/turns",
    response_model=list[ConversationTurnResponse],
    summary="Get conversation turns",
)
async def get_conversation_turns(
    conversation_id: UUID,
) -> list[ConversationTurnResponse]:
    """
    Retrieve all turns for a conversation.

    Args:
        conversation_id: Conversation identifier

    Returns:
        List of conversation turns

    Raises:
        HTTPException: If conversation not found
    """
    try:
        logger.info(f"Fetching turns for conversation {conversation_id}")

        # TODO: Fetch from database
        # Mock response
        mock_turns = [
            ConversationTurnResponse(
                id=uuid4(),
                turn_number=1,
                user_input="Show me all users",
                generated_query="SELECT * FROM users",
                confidence_score=0.95,
                validation_status=ValidationStatus.VALID,
                created_at=datetime.utcnow(),
            ),
        ]

        return mock_turns

    except Exception as e:
        logger.error(f"Error fetching turns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch conversation turns",
            ).model_dump(),
        )


@router.post(
    "/conversations/{conversation_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Submit user feedback",
)
async def submit_feedback(
    conversation_id: UUID,
    feedback: FeedbackRequest,
) -> None:
    """
    Submit user feedback for a conversation/turn.

    Args:
        conversation_id: Conversation identifier
        feedback: User feedback data

    Raises:
        HTTPException: If conversation not found or feedback submission fails
    """
    try:
        async with async_log_context(conversation_id=str(conversation_id)):
            logger.info(f"Submitting feedback for conversation {conversation_id}")

            # Record user satisfaction metrics
            record_user_satisfaction(feedback.rating, feedback.is_query_correct)

            # TODO: Store feedback in database
            # If corrected query provided and is_query_correct=False, add to RAG as negative example
            if not feedback.is_query_correct and feedback.corrected_query:
                logger.info("Adding corrected query to RAG store as learning example")
                # TODO: Add to RAG store
                # await rag_service.add_example(
                #     conversation_id=conversation_id,
                #     corrected_query=feedback.corrected_query,
                #     is_good_example=True,
                # )

            logger.info(
                f"Feedback submitted successfully for conversation {conversation_id}"
            )

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="feedback_error",
                message="Failed to submit feedback",
            ).model_dump(),
        )
