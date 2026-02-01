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
    ValidationStatus,
)
from text2x.api.routes.feedback import SubmitFeedbackRequest, FeedbackResponse
from text2x.models.conversation import Conversation, ConversationTurn
from text2x.models.feedback import FeedbackCategory, FeedbackRating
from text2x.models.rag import RAGExample, ExampleStatus
from text2x.services.feedback_service import FeedbackService

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
    "/{conversation_id}/turns/{turn_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback",
    description="Submit thumbs up/down feedback for a generated query",
)
async def submit_feedback(
    conversation_id: UUID,
    turn_id: UUID,
    request: SubmitFeedbackRequest,
) -> FeedbackResponse:
    """
    Submit user feedback on a generated query.

    This endpoint allows users to provide feedback on generated queries with:
    - Thumbs up or thumbs down rating
    - Categorical feedback (e.g., incorrect_result, syntax_error, etc.)
    - Optional free-text comments

    Based on the feedback and confidence score, the system will:
    - Auto-approve high-confidence queries with thumbs up to RAG
    - Queue medium-confidence queries for expert review (low priority)
    - Queue all thumbs-down queries for expert review (high priority)

    Args:
        conversation_id: Conversation identifier
        turn_id: Turn identifier within conversation
        request: Feedback submission data

    Returns:
        Created feedback record

    Raises:
        HTTPException: If turn not found (404), feedback already exists (409),
                      or submission fails (500)
    """
    try:
        logger.info(
            f"Submitting feedback for turn {turn_id} in conversation "
            f"{conversation_id}: rating={request.rating}"
        )

        # Convert string rating to enum
        try:
            rating = FeedbackRating(request.rating)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error="invalid_rating",
                    message=f"Invalid rating: {request.rating}. Must be 'up' or 'down'",
                ).model_dump(),
            )

        # Convert string category to enum
        try:
            category = FeedbackCategory(request.category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error="invalid_category",
                    message=f"Invalid category: {request.category}",
                ).model_dump(),
            )

        # Submit feedback
        service = FeedbackService()
        feedback = await service.submit_feedback(
            turn_id=turn_id,
            rating=rating,
            category=category,
            user_id=request.user_id,
            feedback_text=request.feedback_text,
        )

        response = FeedbackResponse(
            id=str(feedback.id),
            turn_id=str(feedback.turn_id),
            conversation_id=str(conversation_id),
            rating=feedback.rating.value,
            category=feedback.feedback_category.value,
            feedback_text=feedback.feedback_text,
            user_id=feedback.user_id,
            created_at=feedback.created_at.isoformat() if feedback.created_at else "",
        )

        logger.info(
            f"Feedback submitted successfully: {feedback.id}, "
            f"rating={feedback.rating.value}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)

        # Check if it's an integrity error (duplicate feedback)
        error_msg = str(e).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ErrorResponse(
                    error="duplicate_feedback",
                    message="Feedback already exists for this turn",
                ).model_dump(),
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="submission_error",
                message="Failed to submit feedback",
            ).model_dump(),
        )
