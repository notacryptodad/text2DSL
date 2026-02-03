"""Query processing endpoints."""
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from text2x.api.auth import User, get_current_user
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
from text2x.repositories.annotation import SchemaAnnotationRepository
from text2x.repositories.conversation import ConversationRepository
from text2x.repositories.provider import ProviderRepository
from text2x.services.feedback_service import FeedbackService
from text2x.services.rag_service import RAGService
from text2x.services.review_service import ReviewService, ReviewTrigger
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
async def process_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user),
) -> QueryResponse:
    """
    Process a natural language query and generate executable database query using AgentCore.

    This endpoint uses the QueryAgent from AgentCore to:
    1. Retrieve relevant schema context
    2. Generate query using LLM
    3. Optionally execute query if enabled

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

            # Extract user ID from auth context if available
            user_id = current_user.id if current_user else "anonymous"

            # Use AgentCore QueryAgent
            from text2x.api.state import app_state
            from text2x.repositories.provider import ProviderRepository
            from uuid import UUID as PyUUID

            # Get provider to access schema
            provider_repo = ProviderRepository()
            provider_uuid = PyUUID(request.provider_id) if request.provider_id else None
            provider = await provider_repo.get_by_id(provider_uuid) if provider_uuid else None

            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="provider_not_found",
                        message=f"Provider {request.provider_id} not found",
                    ).model_dump(),
                )

            # Get or create QueryAgent instance
            runtime = app_state.agentcore
            agent_name = f"query_{request.provider_id}"

            # Check if agent already exists
            if agent_name not in runtime.agents:
                from text2x.agentcore.agents.query import QueryAgent

                # Create agent instance
                agent = QueryAgent(runtime, agent_name)

                # Set provider on agent
                from text2x.providers.factory import get_provider_instance
                query_provider = await get_provider_instance(provider)
                agent.set_provider(query_provider)

                # Register agent with runtime
                runtime.agents[agent_name] = agent
                logger.info(f"Created QueryAgent instance: {agent_name}")
            else:
                agent = runtime.agents[agent_name]

            # Get schema context
            schema_context = {}
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

            # Build API response from agent result
            generated_query = agent_result.get("generated_query", "")
            query_explanation = agent_result.get("query_explanation", "")
            execution_result = agent_result.get("execution_result")

            # Build validation result (simplified for AgentCore path)
            from text2x.api.models import (
                ValidationResult as APIValidationResult,
                ExecutionResult as APIExecutionResult,
            )

            api_validation_status = ValidationStatus.VALID if generated_query else ValidationStatus.UNKNOWN
            api_validation_result = APIValidationResult(
                status=api_validation_status,
                errors=[],
                warnings=[],
                suggestions=[],
            )

            # Build execution result if available
            api_execution_result = None
            if execution_result:
                api_execution_result = APIExecutionResult(
                    success=execution_result.get("success", False),
                    row_count=execution_result.get("row_count", 0),
                    data=execution_result.get("rows"),
                    error_message=execution_result.get("error"),
                    execution_time_ms=int(execution_result.get("execution_time_ms", 0)),
                )

            # Build final API response
            api_response = QueryResponse(
                conversation_id=conversation_id,
                turn_id=turn_id,
                generated_query=generated_query,
                confidence_score=1.0 if generated_query else 0.0,  # Simplified confidence
                validation_status=api_validation_status,
                validation_result=api_validation_result,
                execution_result=api_execution_result,
                reasoning_trace=None,
                needs_clarification=False,
                clarification_questions=[],
                iterations=1,
                query_explanation=query_explanation,  # Add explanation field
            )

            logger.info(
                f"Query processed via AgentCore: turn_id={turn_id}, "
                f"has_query={bool(generated_query)}"
            )

            # Record metrics
            query_duration = time.time() - start_time
            provider_type = provider.type.value if provider else "unknown"

            record_query_success(provider_type)
            record_query_latency(provider_type, query_duration)
            record_iterations(provider_type, 1)
            record_validation_result(provider_type, True)

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
async def get_conversation(
    conversation_id: UUID,
    current_user: Optional[User] = Depends(get_current_user),
) -> ConversationResponse:
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

        # Fetch from database
        conversation_repo = ConversationRepository()
        conversation = await conversation_repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Conversation {conversation_id} not found",
                ).model_dump(),
            )

        # Convert turns to API response format
        turns = [
            ConversationTurnResponse(
                id=turn.id,
                turn_number=turn.turn_number,
                user_input=turn.user_input,
                generated_query=turn.generated_query,
                confidence_score=turn.confidence_score,
                validation_status=(
                    ValidationStatus.VALID
                    if turn.validation_result and turn.validation_result.get("status") == "passed"
                    else ValidationStatus.INVALID
                    if turn.validation_result and turn.validation_result.get("status") == "failed"
                    else ValidationStatus.UNKNOWN
                ),
                created_at=turn.created_at,
            )
            for turn in conversation.turns
        ]

        response = ConversationResponse(
            id=conversation.id,
            provider_id=conversation.provider_id or "unknown",
            status=conversation.status.value,
            turn_count=len(conversation.turns),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            turns=turns,
        )

        return response

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
    current_user: Optional[User] = Depends(get_current_user),
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

        # Fetch from database
        conversation_repo = ConversationRepository()
        conversation = await conversation_repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Conversation {conversation_id} not found",
                ).model_dump(),
            )

        # Convert turns to API response format
        turns = [
            ConversationTurnResponse(
                id=turn.id,
                turn_number=turn.turn_number,
                user_input=turn.user_input,
                generated_query=turn.generated_query,
                confidence_score=turn.confidence_score,
                validation_status=(
                    ValidationStatus.VALID
                    if turn.validation_result and turn.validation_result.get("status") == "passed"
                    else ValidationStatus.INVALID
                    if turn.validation_result and turn.validation_result.get("status") == "failed"
                    else ValidationStatus.UNKNOWN
                ),
                created_at=turn.created_at,
            )
            for turn in conversation.turns
        ]

        return turns

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
    current_user: Optional[User] = Depends(get_current_user),
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

            # Get the turn_id from the feedback request (assumes it's provided)
            # If not provided, we'll need to get the latest turn for this conversation
            turn_id = feedback.turn_id if hasattr(feedback, 'turn_id') else None

            if not turn_id:
                # Get the latest turn for this conversation
                conversation_repo = ConversationRepository()
                conversation = await conversation_repo.get_by_id(conversation_id)
                if conversation and conversation.turns:
                    turn_id = conversation.turns[-1].id
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ErrorResponse(
                            error="not_found",
                            message=f"No turns found for conversation {conversation_id}",
                        ).model_dump(),
                    )

            # Store feedback using FeedbackService
            from text2x.models.feedback import FeedbackRating, FeedbackCategory

            feedback_service = FeedbackService()
            rating = FeedbackRating.UP if feedback.is_query_correct else FeedbackRating.DOWN
            category = FeedbackCategory.CORRECTNESS

            try:
                await feedback_service.submit_feedback(
                    turn_id=turn_id,
                    rating=rating,
                    category=category,
                    user_id="anonymous",  # Will be replaced with auth context
                    feedback_text=feedback.feedback_text if hasattr(feedback, 'feedback_text') else None,
                )
            except Exception as e:
                logger.error(f"Failed to submit feedback: {e}", exc_info=True)
                # Don't fail the request if feedback submission fails
                pass

            # If corrected query provided and is_query_correct=False, add to RAG as learning example
            if not feedback.is_query_correct and feedback.corrected_query:
                logger.info("Adding corrected query to RAG store as learning example")
                try:
                    rag_service = RAGService()

                    # Get conversation to extract provider_id and original query
                    conversation_repo = ConversationRepository()
                    conversation = await conversation_repo.get_by_id(conversation_id)

                    if conversation:
                        # Get the turn to get the original query
                        from text2x.repositories.conversation import ConversationTurnRepository
                        turn_repo = ConversationTurnRepository()
                        turn = await turn_repo.get_by_id(turn_id)

                        if turn:
                            # Add the corrected example to RAG (auto-approve good corrections)
                            await rag_service.add_example(
                                nl_query=turn.user_input,
                                generated_query=feedback.corrected_query,
                                is_good=True,
                                provider_id=conversation.provider_id or "unknown",
                                auto_approve=True,  # Auto-approve user corrections with high confidence
                                metadata={
                                    "source": "user_feedback",
                                    "original_query": turn.generated_query,
                                    "conversation_id": str(conversation_id),
                                    "turn_id": str(turn_id),
                                },
                            )
                            logger.info(f"Successfully added corrected query to RAG for turn {turn_id}")
                except Exception as e:
                    logger.error(f"Failed to add corrected query to RAG: {e}", exc_info=True)
                    # Don't fail the request if RAG addition fails
                    pass

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
