"""Query processing endpoints."""
import logging
import time
from datetime import datetime
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

        # TODO: Integrate with actual orchestrator
        # from text2x.agents.orchestrator import QueryOrchestrator
        # orchestrator = QueryOrchestrator()
        # result = await orchestrator.process_query(
        #     provider_id=request.provider_id,
        #     query=request.query,
        #     conversation_id=conversation_id,
        #     max_iterations=max_iterations,
        #     confidence_threshold=confidence_threshold,
        #     enable_execution=enable_execution,
        #     trace_level=request.options.trace_level,
        # )

        # Mock response for now (replace with actual orchestrator integration)
        from text2x.api.models import (
            AgentTrace,
            ExecutionResult,
            ReasoningTrace,
            ValidationResult,
        )

        mock_response = QueryResponse(
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
                    data=None,  # Actual data would be included if needed
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
                if request.options.trace_level != "none"
                else None
            ),
            needs_clarification=False,
            clarification_questions=[],
            iterations=1,
        )

            logger.info(
                f"Query processed successfully: turn_id={turn_id}, "
                f"confidence={mock_response.confidence_score}"
            )

            # Record metrics
            query_duration = time.time() - start_time
            provider_type = "postgresql"  # Extract from provider_id in real implementation

            # Success metrics
            record_query_success(provider_type)
            record_query_latency(provider_type, query_duration)
            record_iterations(provider_type, mock_response.iterations)

            # Validation metrics
            is_valid = mock_response.validation_status == ValidationStatus.VALID
            record_validation_result(provider_type, is_valid)

            # Cost metrics (from trace if available)
            if mock_response.reasoning_trace:
                trace = mock_response.reasoning_trace
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
                and mock_response.confidence_score < settings.low_confidence_threshold
            ):
                logger.info(f"Queuing turn {turn_id} for expert review (low confidence)")
                # TODO: Add to review queue
                # await add_to_review_queue(turn_id, "low_confidence")

            return mock_response

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
