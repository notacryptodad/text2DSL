"""Conversation management endpoints."""
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from text2x.api.app import app_state
from text2x.api.models import (
    ConversationResponse,
    ConversationStatus,
    ConversationTurnResponse,
    ErrorResponse,
    FeedbackRequest,
    ValidationStatus,
)
from text2x.models.conversation import Conversation, ConversationTurn
from text2x.models.rag import RAGExample, ExampleStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def get_session() -> AsyncSession:
    """Get database session from app state."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        app_state.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session_maker()


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
    description="Retrieve complete conversation details including all turns and metadata",
)
async def get_conversation(conversation_id: UUID) -> ConversationResponse:
    """
    Retrieve conversation details including all turns.

    This endpoint returns:
    - Conversation metadata (ID, provider, status, timestamps)
    - All conversation turns in chronological order
    - Turn details including queries, confidence scores, and validation status

    Args:
        conversation_id: Conversation identifier

    Returns:
        Conversation details with all turns

    Raises:
        HTTPException: If conversation not found (404) or fetch fails (500)
    """
    try:
        logger.info(f"Fetching conversation {conversation_id}")

        async with await get_session() as session:
            # Query conversation with turns eagerly loaded
            stmt = (
                select(Conversation)
                .options(selectinload(Conversation.turns))
                .where(Conversation.id == conversation_id)
            )
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Conversation {conversation_id} not found",
                    ).model_dump(),
                )

            # Convert turns to response models
            turns = [
                ConversationTurnResponse(
                    id=turn.id,
                    turn_number=turn.turn_number,
                    user_input=turn.user_input,
                    generated_query=turn.generated_query,
                    confidence_score=turn.confidence_score,
                    validation_status=ValidationStatus(
                        turn.validation_result.get("status", "unknown")
                        if turn.validation_result
                        else ValidationStatus.UNKNOWN
                    ),
                    created_at=turn.created_at,
                )
                for turn in sorted(conversation.turns, key=lambda t: t.turn_number)
            ]

            response = ConversationResponse(
                id=conversation.id,
                provider_id=conversation.provider_id,
                status=ConversationStatus(conversation.status.value),
                turn_count=len(conversation.turns),
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                turns=turns,
            )

            logger.info(
                f"Successfully fetched conversation {conversation_id} "
                f"with {len(turns)} turns"
            )
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching conversation {conversation_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch conversation",
            ).model_dump(),
        )


@router.get(
    "/{conversation_id}/turns",
    response_model=list[ConversationTurnResponse],
    summary="Get conversation turns",
    description="Retrieve all turns for a specific conversation in chronological order",
)
async def get_conversation_turns(
    conversation_id: UUID,
) -> list[ConversationTurnResponse]:
    """
    Retrieve all turns for a conversation.

    This endpoint returns a list of all turns in the conversation,
    ordered by turn number. Each turn includes:
    - User input (natural language query)
    - Generated query
    - Confidence score
    - Validation status
    - Timestamp

    Args:
        conversation_id: Conversation identifier

    Returns:
        List of conversation turns in chronological order

    Raises:
        HTTPException: If conversation not found (404) or fetch fails (500)
    """
    try:
        logger.info(f"Fetching turns for conversation {conversation_id}")

        async with await get_session() as session:
            # Verify conversation exists
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Conversation {conversation_id} not found",
                    ).model_dump(),
                )

            # Query turns ordered by turn number
            stmt = (
                select(ConversationTurn)
                .where(ConversationTurn.conversation_id == conversation_id)
                .order_by(ConversationTurn.turn_number)
            )
            result = await session.execute(stmt)
            turns = result.scalars().all()

            # Convert to response models
            turn_responses = [
                ConversationTurnResponse(
                    id=turn.id,
                    turn_number=turn.turn_number,
                    user_input=turn.user_input,
                    generated_query=turn.generated_query,
                    confidence_score=turn.confidence_score,
                    validation_status=ValidationStatus(
                        turn.validation_result.get("status", "unknown")
                        if turn.validation_result
                        else ValidationStatus.UNKNOWN
                    ),
                    created_at=turn.created_at,
                )
                for turn in turns
            ]

            logger.info(
                f"Successfully fetched {len(turn_responses)} turns "
                f"for conversation {conversation_id}"
            )
            return turn_responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching turns for conversation {conversation_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch conversation turns",
            ).model_dump(),
        )


@router.post(
    "/{conversation_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Submit user feedback",
    description="Submit feedback for a conversation turn, optionally with corrected query",
)
async def submit_feedback(
    conversation_id: UUID,
    feedback: FeedbackRequest,
) -> None:
    """
    Submit user feedback for a conversation/turn.

    This endpoint processes user feedback including:
    - Satisfaction rating (1-5)
    - Correctness flag for generated query
    - Optional corrected query (if original was incorrect)
    - Optional comments

    If a corrected query is provided with is_query_correct=False,
    the system will:
    1. Store the feedback in the database
    2. Create a new RAG example with the corrected query
    3. Queue the correction for expert review

    Args:
        conversation_id: Conversation identifier
        feedback: User feedback data

    Raises:
        HTTPException: If conversation not found (404) or submission fails (500)
    """
    try:
        logger.info(
            f"Submitting feedback for conversation {conversation_id}, "
            f"rating={feedback.rating}, correct={feedback.is_query_correct}"
        )

        async with await get_session() as session:
            # Verify conversation exists
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Conversation {conversation_id} not found",
                    ).model_dump(),
                )

            # Get the latest turn for this conversation
            stmt = (
                select(ConversationTurn)
                .where(ConversationTurn.conversation_id == conversation_id)
                .order_by(ConversationTurn.turn_number.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            latest_turn = result.scalar_one_or_none()

            if not latest_turn:
                logger.warning(
                    f"No turns found for conversation {conversation_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message="No turns found for this conversation",
                    ).model_dump(),
                )

            # Store feedback in metadata (could be a separate table in production)
            feedback_data = {
                "rating": feedback.rating,
                "is_query_correct": feedback.is_query_correct,
                "comments": feedback.comments,
                "corrected_query": feedback.corrected_query,
            }

            # Update turn metadata to include feedback
            if not latest_turn.reasoning_trace:
                latest_turn.reasoning_trace = {}

            if isinstance(latest_turn.reasoning_trace, dict):
                latest_turn.reasoning_trace["user_feedback"] = feedback_data

            # If corrected query provided and original was incorrect, add to RAG
            if not feedback.is_query_correct and feedback.corrected_query:
                logger.info(
                    "User provided corrected query - creating RAG example "
                    "for expert review"
                )

                # Extract tables from schema context if available
                involved_tables = []
                if latest_turn.schema_context:
                    schema_tables = latest_turn.schema_context.get("tables", [])
                    involved_tables = [
                        t.get("name") for t in schema_tables if t.get("name")
                    ]

                # Create RAG example with corrected query
                rag_example = RAGExample(
                    provider_id=conversation.provider_id,
                    natural_language_query=latest_turn.user_input,
                    generated_query=latest_turn.generated_query,
                    is_good_example=False,  # Original was incorrect
                    status=ExampleStatus.PENDING_REVIEW,
                    involved_tables=involved_tables or ["unknown"],
                    query_intent="user_correction",
                    complexity_level="medium",
                    expert_corrected_query=feedback.corrected_query,
                    review_notes=f"User feedback: {feedback.comments or 'No comments'}",
                    source_conversation_id=conversation_id,
                    metadata={
                        "original_confidence": latest_turn.confidence_score,
                        "user_rating": feedback.rating,
                    },
                )

                session.add(rag_example)

                logger.info(
                    f"Created RAG example {rag_example.id} with user-corrected query"
                )

            await session.commit()

            logger.info(
                f"Feedback submitted successfully for conversation {conversation_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error submitting feedback for conversation {conversation_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="feedback_error",
                message="Failed to submit feedback",
            ).model_dump(),
        )
