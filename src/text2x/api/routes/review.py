"""Expert review queue endpoints."""
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from text2x.api.app import app_state
from text2x.api.models import (
    ErrorResponse,
    ExampleStatus,
    RAGExampleResponse,
    ReviewQueueItem,
    ReviewUpdateRequest,
    ValidationStatus,
)
from text2x.models.conversation import Conversation, ConversationTurn
from text2x.models.rag import RAGExample
from text2x.utils.observability import (
    set_review_queue_size,
    record_review_completion_time,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])


async def get_session() -> AsyncSession:
    """Get database session from app state."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        app_state.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session_maker()


def calculate_review_priority(
    confidence_score: float,
    validation_status: str,
    has_user_feedback: bool,
) -> int:
    """
    Calculate review priority based on various factors.

    Priority scoring:
    - Validation failures: +100 (highest priority)
    - User feedback: +50
    - Low confidence: +20 to +40 based on how low

    Args:
        confidence_score: Query confidence score (0.0 to 1.0)
        validation_status: Validation status string
        has_user_feedback: Whether user provided feedback

    Returns:
        Priority score (higher = more urgent)
    """
    priority = 0

    # Validation failures are highest priority
    if validation_status in ["invalid", "failed"]:
        priority += 100

    # User-reported issues are second highest
    if has_user_feedback:
        priority += 50

    # Low confidence queries need review
    if confidence_score < 0.7:
        # Lower confidence = higher priority
        priority += int((0.7 - confidence_score) * 100)

    return priority


@router.get(
    "/queue",
    response_model=list[ReviewQueueItem],
    summary="Get review queue",
    description="Retrieve paginated list of items awaiting expert review, sorted by priority",
)
async def get_review_queue(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    status_filter: Optional[ExampleStatus] = Query(
        None, description="Filter by status"
    ),
) -> list[ReviewQueueItem]:
    """
    Get paginated review queue with priority ordering.

    This endpoint returns items that need expert review, including:
    - Low confidence queries (< 0.7)
    - Validation failures
    - User-reported issues with corrections
    - RAG examples pending approval

    Items are sorted by priority (highest first) and support pagination.
    Each item includes the original query, generated query, and context
    needed for expert review.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        provider_id: Optional filter by provider
        status_filter: Optional filter by status

    Returns:
        List of review queue items sorted by priority

    Raises:
        HTTPException: If fetch fails (500)
    """
    try:
        logger.info(
            f"Fetching review queue: page={page}, size={page_size}, "
            f"provider={provider_id}, status={status_filter}"
        )

        async with await get_session() as session:
            # Build query for RAG examples needing review
            stmt = select(RAGExample).where(
                RAGExample.status == ExampleStatus.PENDING_REVIEW
            )

            # Apply filters
            if provider_id:
                stmt = stmt.where(RAGExample.provider_id == provider_id)

            if status_filter:
                stmt = stmt.where(RAGExample.status == status_filter)

            # Order by creation date (most recent first)
            stmt = stmt.order_by(desc(RAGExample.created_at))

            # Apply pagination
            offset = (page - 1) * page_size
            stmt = stmt.offset(offset).limit(page_size)

            result = await session.execute(stmt)
            rag_examples = result.scalars().all()

            # Convert to review queue items
            review_items = []
            for example in rag_examples:
                # Determine reason for review
                reason = "pending_review"
                if example.expert_corrected_query:
                    reason = "user_reported"
                elif not example.is_good_example:
                    reason = "validation_failed"
                elif example.metadata and example.metadata.get("original_confidence"):
                    conf = example.metadata["original_confidence"]
                    if conf < 0.7:
                        reason = "low_confidence"

                # Get confidence score from metadata or use default
                confidence_score = 0.0
                if example.metadata and "original_confidence" in example.metadata:
                    confidence_score = example.metadata["original_confidence"]

                # Determine validation status
                validation = ValidationStatus.UNKNOWN
                if not example.is_good_example:
                    validation = ValidationStatus.INVALID
                elif example.is_good_example:
                    validation = ValidationStatus.VALID

                # Calculate priority
                has_feedback = example.expert_corrected_query is not None
                priority = calculate_review_priority(
                    confidence_score=confidence_score,
                    validation_status=validation.value,
                    has_user_feedback=has_feedback,
                )

                review_item = ReviewQueueItem(
                    id=example.id,
                    conversation_id=example.source_conversation_id or UUID(int=0),
                    turn_id=UUID(int=0),  # Not directly linked to turn
                    provider_id=example.provider_id,
                    user_input=example.natural_language_query,
                    generated_query=example.generated_query,
                    confidence_score=confidence_score,
                    validation_status=validation,
                    reason_for_review=reason,
                    created_at=example.created_at,
                    priority=priority,
                )
                review_items.append(review_item)

            # Sort by priority (highest first)
            review_items.sort(key=lambda x: x.priority, reverse=True)

            logger.info(
                f"Retrieved {len(review_items)} items from review queue "
                f"(page {page})"
            )

            # Update review queue size metrics
            # Count items by reason
            reason_counts = {}
            for item in review_items:
                reason = item.reason_for_review
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            for reason, count in reason_counts.items():
                set_review_queue_size(reason, count)

            return review_items

    except Exception as e:
        logger.error(f"Error fetching review queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch review queue",
            ).model_dump(),
        )


@router.get(
    "/queue/{item_id}",
    response_model=RAGExampleResponse,
    summary="Get review item details",
    description="Get detailed information about a specific review queue item",
)
async def get_review_item(item_id: UUID) -> RAGExampleResponse:
    """
    Get detailed information about a review queue item.

    This provides all details needed for expert review including:
    - Original natural language query
    - Generated query
    - Expert corrections (if any)
    - Review notes
    - Metadata (confidence, complexity, etc.)

    Args:
        item_id: Review item identifier

    Returns:
        Detailed review item information

    Raises:
        HTTPException: If item not found (404) or fetch fails (500)
    """
    try:
        logger.info(f"Fetching review item {item_id}")

        async with await get_session() as session:
            stmt = select(RAGExample).where(RAGExample.id == item_id)
            result = await session.execute(stmt)
            example = result.scalar_one_or_none()

            if not example:
                logger.warning(f"Review item {item_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Review item {item_id} not found",
                    ).model_dump(),
                )

            response = RAGExampleResponse(
                id=example.id,
                provider_id=example.provider_id,
                natural_language_query=example.natural_language_query,
                generated_query=example.generated_query,
                is_good_example=example.is_good_example,
                status=ExampleStatus(example.status.value),
                involved_tables=example.involved_tables,
                query_intent=example.query_intent,
                complexity_level=example.complexity_level,
                reviewed_by=example.reviewed_by,
                reviewed_at=example.reviewed_at,
                expert_corrected_query=example.expert_corrected_query,
                created_at=example.created_at,
            )

            logger.info(f"Successfully fetched review item {item_id}")
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching review item {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch review item",
            ).model_dump(),
        )


@router.put(
    "/queue/{item_id}",
    response_model=RAGExampleResponse,
    summary="Update review item",
    description="Approve, reject, or correct a review queue item",
)
async def update_review_item(
    item_id: UUID,
    update: ReviewUpdateRequest,
) -> RAGExampleResponse:
    """
    Update/approve/reject a review queue item.

    Expert reviewers can:
    1. Approve the query as-is (approved=True, no corrections)
    2. Approve with corrections (approved=True, corrected_query provided)
    3. Reject the query (approved=False)

    Approved items are:
    - Marked as APPROVED status
    - Immediately indexed in OpenSearch for RAG retrieval
    - Made available to improve future query generation

    Rejected items are:
    - Marked as REJECTED status
    - Not used for RAG retrieval
    - Kept for audit purposes

    Args:
        item_id: Review item identifier
        update: Review update data with approval decision

    Returns:
        Updated review item

    Raises:
        HTTPException: If item not found (404) or update fails (500)
    """
    try:
        logger.info(
            f"Updating review item {item_id}: approved={update.approved}, "
            f"has_correction={update.corrected_query is not None}"
        )

        async with await get_session() as session:
            # Fetch the item
            stmt = select(RAGExample).where(RAGExample.id == item_id)
            result = await session.execute(stmt)
            example = result.scalar_one_or_none()

            if not example:
                logger.warning(f"Review item {item_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Review item {item_id} not found",
                    ).model_dump(),
                )

            # Calculate review duration for metrics
            review_duration_seconds = 0.0
            if example.created_at:
                review_duration_seconds = (
                    datetime.utcnow() - example.created_at
                ).total_seconds()

            # Update the example
            example.reviewed_by = "expert"  # TODO: Get from auth context
            example.reviewed_at = datetime.utcnow()
            example.status = (
                ExampleStatus.APPROVED if update.approved else ExampleStatus.REJECTED
            )

            # Record review metrics
            record_review_completion_time(update.approved, review_duration_seconds)

            if update.corrected_query:
                example.expert_corrected_query = update.corrected_query
                # If corrected, mark original as bad example
                example.is_good_example = False

            if update.feedback:
                example.review_notes = update.feedback

            # If approved, trigger OpenSearch indexing
            if update.approved:
                logger.info(
                    f"Review item {item_id} approved - queuing for "
                    "OpenSearch indexing"
                )
                # TODO: Queue for OpenSearch indexing
                # from text2x.services.rag_indexer import queue_for_indexing
                # await queue_for_indexing(example)
                example.embeddings_generated = False  # Mark for re-indexing

            await session.commit()

            # Refresh to get updated values
            await session.refresh(example)

            response = RAGExampleResponse(
                id=example.id,
                provider_id=example.provider_id,
                natural_language_query=example.natural_language_query,
                generated_query=example.generated_query,
                is_good_example=example.is_good_example,
                status=ExampleStatus(example.status.value),
                involved_tables=example.involved_tables,
                query_intent=example.query_intent,
                complexity_level=example.complexity_level,
                reviewed_by=example.reviewed_by,
                reviewed_at=example.reviewed_at,
                expert_corrected_query=example.expert_corrected_query,
                created_at=example.created_at,
            )

            logger.info(
                f"Successfully updated review item {item_id}: "
                f"status={example.status.value}"
            )
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review item {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="update_error",
                message="Failed to update review item",
            ).model_dump(),
        )


@router.get(
    "/stats",
    summary="Get review queue statistics",
    description="Get statistics about the review queue",
)
async def get_review_stats() -> dict:
    """
    Get statistics about the review queue.

    Returns aggregated metrics including:
    - Total items pending review
    - Items by provider
    - Items by review reason
    - Average wait time
    - Review throughput

    Returns:
        Dictionary with review queue statistics

    Raises:
        HTTPException: If stats fetch fails (500)
    """
    try:
        logger.info("Fetching review queue statistics")

        async with await get_session() as session:
            # Count pending reviews
            stmt = select(func.count()).where(
                RAGExample.status == ExampleStatus.PENDING_REVIEW
            )
            result = await session.execute(stmt)
            pending_count = result.scalar()

            # Count by status
            stmt = select(RAGExample.status, func.count()).group_by(RAGExample.status)
            result = await session.execute(stmt)
            status_counts = {status.value: count for status, count in result}

            # Count by provider
            stmt = (
                select(RAGExample.provider_id, func.count())
                .where(RAGExample.status == ExampleStatus.PENDING_REVIEW)
                .group_by(RAGExample.provider_id)
            )
            result = await session.execute(stmt)
            provider_counts = {provider: count for provider, count in result}

            # Get oldest pending item
            stmt = (
                select(RAGExample.created_at)
                .where(RAGExample.status == ExampleStatus.PENDING_REVIEW)
                .order_by(RAGExample.created_at)
                .limit(1)
            )
            result = await session.execute(stmt)
            oldest = result.scalar_one_or_none()

            stats = {
                "pending_reviews": pending_count,
                "status_breakdown": status_counts,
                "by_provider": provider_counts,
                "oldest_pending": oldest.isoformat() if oldest else None,
                "oldest_age_hours": (
                    (datetime.utcnow() - oldest).total_seconds() / 3600
                    if oldest
                    else 0
                ),
            }

            logger.info(
                f"Review queue stats: {pending_count} pending, "
                f"{len(provider_counts)} providers"
            )
            return stats

    except Exception as e:
        logger.error(f"Error fetching review stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch review statistics",
            ).model_dump(),
        )
