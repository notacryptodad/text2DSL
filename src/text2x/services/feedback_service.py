"""
Feedback service for handling user feedback and auto-queuing logic.

This service implements the business logic for:
- Submitting user feedback on generated queries
- Auto-queuing items for review based on feedback + confidence
- Tracking feedback statistics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.base import get_db
from text2x.models.conversation import ConversationTurn
from text2x.models.feedback import FeedbackCategory, FeedbackRating, UserFeedback
from text2x.models.rag import ExampleStatus, RAGExample
from text2x.repositories.feedback import FeedbackRepository
from text2x.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class FeedbackStats:
    """Statistics about user feedback."""

    def __init__(
        self,
        total_feedback: int,
        thumbs_up: int,
        thumbs_down: int,
        by_category: Dict[str, int],
        approval_rate: float,
        avg_confidence_thumbs_up: float,
        avg_confidence_thumbs_down: float,
    ):
        self.total_feedback = total_feedback
        self.thumbs_up = thumbs_up
        self.thumbs_down = thumbs_down
        self.by_category = by_category
        self.approval_rate = approval_rate
        self.avg_confidence_thumbs_up = avg_confidence_thumbs_up
        self.avg_confidence_thumbs_down = avg_confidence_thumbs_down

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "total_feedback": self.total_feedback,
            "thumbs_up": self.thumbs_up,
            "thumbs_down": self.thumbs_down,
            "by_category": self.by_category,
            "approval_rate": self.approval_rate,
            "avg_confidence_thumbs_up": self.avg_confidence_thumbs_up,
            "avg_confidence_thumbs_down": self.avg_confidence_thumbs_down,
        }


class FeedbackService:
    """Service for handling user feedback operations."""

    def __init__(self):
        self.feedback_repo = FeedbackRepository()
        self.rag_service = RAGService()

    async def submit_feedback(
        self,
        turn_id: UUID,
        rating: FeedbackRating,
        category: FeedbackCategory,
        user_id: str,
        feedback_text: Optional[str] = None,
    ) -> UserFeedback:
        """
        Submit user feedback and trigger auto-queue logic.

        Auto-queue logic:
        - thumbs_up + confidence >= 0.9 -> auto_approve_to_rag
        - thumbs_up + confidence < 0.9 -> queue_for_review(low_priority)
        - thumbs_down -> queue_for_review(high_priority)

        Args:
            turn_id: The conversation turn being rated
            rating: User rating (UP or DOWN)
            category: Feedback category
            user_id: User who provided feedback
            feedback_text: Optional detailed feedback

        Returns:
            The created UserFeedback object

        Raises:
            ValueError: If turn not found or feedback already exists
        """
        logger.info(
            f"Submitting feedback for turn {turn_id}: rating={rating.value}, "
            f"category={category.value}"
        )

        # Create the feedback record
        feedback = await self.feedback_repo.create(
            turn_id=turn_id,
            rating=rating,
            feedback_category=category,
            user_id=user_id,
            feedback_text=feedback_text,
        )

        # Trigger auto-queue logic
        await self._auto_queue_for_review(turn_id, rating, category, feedback_text)

        logger.info(f"Feedback submitted successfully: {feedback.id}")
        return feedback

    async def _auto_queue_for_review(
        self,
        turn_id: UUID,
        rating: FeedbackRating,
        category: FeedbackCategory,
        feedback_text: Optional[str],
    ) -> None:
        """
        Auto-queue logic based on feedback and confidence.

        This implements the decision tree:
        - Thumbs up + high confidence (>=0.9): Auto-approve to RAG
        - Thumbs up + medium confidence (<0.9): Queue for review (low priority)
        - Thumbs down: Queue for review (high priority)

        Args:
            turn_id: The conversation turn
            rating: User rating
            category: Feedback category
            feedback_text: Optional feedback text
        """
        from sqlalchemy.orm import selectinload

        db = get_db()
        async with db.session() as session:
            # Fetch the turn to get confidence score and query details
            # Eagerly load conversation to avoid lazy-loading issues
            stmt = (
                select(ConversationTurn)
                .where(ConversationTurn.id == turn_id)
                .options(selectinload(ConversationTurn.conversation))
            )
            result = await session.execute(stmt)
            turn = result.scalar_one_or_none()

            if not turn:
                logger.warning(f"Turn {turn_id} not found for auto-queue")
                return

            confidence = turn.confidence_score
            logger.info(
                f"Auto-queue evaluation: rating={rating.value}, confidence={confidence:.2f}"
            )

            # Check if RAG example already exists for this turn
            stmt = select(RAGExample).where(
                RAGExample.source_conversation_id == turn.conversation_id,
                RAGExample.natural_language_query == turn.user_input,
            )
            result = await session.execute(stmt)
            existing_example = result.scalar_one_or_none()

            if rating == FeedbackRating.UP:
                if confidence >= 0.9:
                    # Auto-approve to RAG
                    logger.info(
                        f"Auto-approving turn {turn_id} to RAG (confidence={confidence:.2f})"
                    )
                    await self._auto_approve_to_rag(session, turn, existing_example, feedback_text)
                else:
                    # Queue for review with low priority
                    logger.info(
                        f"Queuing turn {turn_id} for review (low priority, "
                        f"confidence={confidence:.2f})"
                    )
                    await self._queue_for_review(
                        session,
                        turn,
                        existing_example,
                        priority="low",
                        reason="thumbs_up_medium_confidence",
                        feedback_text=feedback_text,
                    )
            else:  # thumbs_down
                # Queue for review with high priority
                logger.info(f"Queuing turn {turn_id} for review (high priority)")
                await self._queue_for_review(
                    session,
                    turn,
                    existing_example,
                    priority="high",
                    reason="thumbs_down",
                    feedback_text=feedback_text,
                )

            await session.commit()

    async def _auto_approve_to_rag(
        self,
        session: AsyncSession,
        turn: ConversationTurn,
        existing_example: Optional[RAGExample],
        feedback_text: Optional[str],
    ) -> None:
        """
        Auto-approve a query to the RAG system.

        Args:
            session: Database session
            turn: The conversation turn
            existing_example: Existing RAG example if any
            feedback_text: Optional feedback text
        """
        if existing_example:
            # Update existing example to approved
            existing_example.status = ExampleStatus.APPROVED
            existing_example.is_good_example = True
            existing_example.reviewed_by = "auto_approved"
            existing_example.reviewed_at = datetime.utcnow()
            if feedback_text:
                existing_example.review_notes = feedback_text
            logger.info(f"Updated existing RAG example {existing_example.id}")
            rag_example = existing_example
        else:
            # Create new approved RAG example
            rag_example = RAGExample(
                provider_id=turn.conversation.provider_id or "default",
                natural_language_query=turn.user_input,
                generated_query=turn.generated_query,
                is_good_example=True,
                status=ExampleStatus.APPROVED,
                involved_tables=self._extract_tables(turn),
                query_intent=self._extract_intent(turn),
                complexity_level=self._calculate_complexity(turn),
                reviewed_by="auto_approved",
                reviewed_at=datetime.utcnow(),
                source_conversation_id=turn.conversation_id,
                extra_metadata={
                    "original_confidence": turn.confidence_score,
                    "auto_approved": True,
                    "feedback_text": feedback_text,
                },
                embeddings_generated=False,
            )
            session.add(rag_example)
            logger.info(f"Created new auto-approved RAG example")

        # Flush to get the ID if it's a new example
        await session.flush()

        # Index in OpenSearch for vector similarity search
        try:
            await self.rag_service._index_in_opensearch(rag_example)
            logger.info(
                f"Successfully indexed auto-approved example {rag_example.id} in OpenSearch"
            )
        except Exception as e:
            logger.error(f"Failed to index in OpenSearch: {e}")
            # Continue - example is still saved in DB

    async def _queue_for_review(
        self,
        session: AsyncSession,
        turn: ConversationTurn,
        existing_example: Optional[RAGExample],
        priority: str,
        reason: str,
        feedback_text: Optional[str],
    ) -> None:
        """
        Queue a query for expert review.

        Args:
            session: Database session
            turn: The conversation turn
            existing_example: Existing RAG example if any
            priority: Priority level ("high" or "low")
            reason: Reason for review
            feedback_text: Optional feedback text
        """
        if existing_example:
            # Update existing example status
            existing_example.status = ExampleStatus.PENDING_REVIEW
            if feedback_text:
                existing_example.review_notes = (
                    existing_example.review_notes or ""
                ) + f"\n[User feedback]: {feedback_text}"
            logger.info(f"Updated existing RAG example {existing_example.id} to pending review")
        else:
            # Create new RAG example pending review
            rag_example = RAGExample(
                provider_id=turn.conversation.provider_id or "default",
                natural_language_query=turn.user_input,
                generated_query=turn.generated_query,
                is_good_example=(priority == "low"),  # Low priority = likely good
                status=ExampleStatus.PENDING_REVIEW,
                involved_tables=self._extract_tables(turn),
                query_intent=self._extract_intent(turn),
                complexity_level=self._calculate_complexity(turn),
                source_conversation_id=turn.conversation_id,
                review_notes=feedback_text,
                extra_metadata={
                    "original_confidence": turn.confidence_score,
                    "review_priority": priority,
                    "review_reason": reason,
                },
                embeddings_generated=False,
            )
            session.add(rag_example)
            logger.info(f"Created new RAG example for review (priority={priority})")

    def _extract_tables(self, turn: ConversationTurn) -> List[str]:
        """Extract involved tables from turn metadata."""
        if turn.schema_context and "tables" in turn.schema_context:
            return turn.schema_context["tables"]
        return []

    def _extract_intent(self, turn: ConversationTurn) -> str:
        """Extract query intent from turn metadata."""
        if turn.reasoning_trace and "intent" in turn.reasoning_trace:
            return turn.reasoning_trace["intent"]
        return "unknown"

    def _calculate_complexity(self, turn: ConversationTurn) -> str:
        """Calculate query complexity based on turn metadata."""
        # Simple heuristic based on iterations
        if turn.iterations > 3:
            return "complex"
        elif turn.iterations > 1:
            return "medium"
        return "simple"

    async def get_stats(
        self,
        workspace_id: Optional[UUID] = None,
        days: int = 30,
    ) -> FeedbackStats:
        """
        Get feedback statistics.

        Args:
            workspace_id: Optional workspace filter (not implemented yet)
            days: Number of days to look back

        Returns:
            FeedbackStats object with aggregated statistics
        """
        logger.info(f"Fetching feedback stats for last {days} days")

        db = get_db()
        async with db.session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Count total feedback
            stmt = (
                select(func.count())
                .select_from(UserFeedback)
                .where(UserFeedback.created_at >= cutoff_date)
            )
            result = await session.execute(stmt)
            total_feedback = result.scalar() or 0

            # Count by rating
            stmt = (
                select(UserFeedback.rating, func.count())
                .where(UserFeedback.created_at >= cutoff_date)
                .group_by(UserFeedback.rating)
            )
            result = await session.execute(stmt)
            rating_counts = {rating.value: count for rating, count in result}

            thumbs_up = rating_counts.get(FeedbackRating.UP.value, 0)
            thumbs_down = rating_counts.get(FeedbackRating.DOWN.value, 0)

            # Count by category
            stmt = (
                select(UserFeedback.feedback_category, func.count())
                .where(UserFeedback.created_at >= cutoff_date)
                .group_by(UserFeedback.feedback_category)
            )
            result = await session.execute(stmt)
            by_category = {category.value: count for category, count in result}

            # Calculate approval rate
            approval_rate = thumbs_up / total_feedback if total_feedback > 0 else 0.0

            # Calculate average confidence for thumbs up
            stmt = (
                select(func.avg(ConversationTurn.confidence_score))
                .select_from(UserFeedback)
                .join(ConversationTurn, UserFeedback.turn_id == ConversationTurn.id)
                .where(
                    UserFeedback.created_at >= cutoff_date,
                    UserFeedback.rating == FeedbackRating.UP,
                )
            )
            result = await session.execute(stmt)
            avg_confidence_up = result.scalar() or 0.0

            # Calculate average confidence for thumbs down
            stmt = (
                select(func.avg(ConversationTurn.confidence_score))
                .select_from(UserFeedback)
                .join(ConversationTurn, UserFeedback.turn_id == ConversationTurn.id)
                .where(
                    UserFeedback.created_at >= cutoff_date,
                    UserFeedback.rating == FeedbackRating.DOWN,
                )
            )
            result = await session.execute(stmt)
            avg_confidence_down = result.scalar() or 0.0

            stats = FeedbackStats(
                total_feedback=total_feedback,
                thumbs_up=thumbs_up,
                thumbs_down=thumbs_down,
                by_category=by_category,
                approval_rate=approval_rate,
                avg_confidence_thumbs_up=float(avg_confidence_up),
                avg_confidence_thumbs_down=float(avg_confidence_down),
            )

            logger.info(
                f"Fetched feedback stats: {total_feedback} total, "
                f"{thumbs_up} up, {thumbs_down} down"
            )
            return stats

    async def get_recent_feedback(
        self,
        limit: int = 50,
        rating_filter: Optional[FeedbackRating] = None,
    ) -> List[UserFeedback]:
        """
        Get recent feedback items.

        Args:
            limit: Maximum number of items to return
            rating_filter: Optional filter by rating

        Returns:
            List of recent UserFeedback objects
        """
        logger.info(f"Fetching recent feedback (limit={limit}, filter={rating_filter})")

        if rating_filter:
            return await self.feedback_repo.list_by_rating(rating_filter, limit)
        else:
            return await self.feedback_repo.list_recent(limit)

    async def get_feedback_list(
        self,
        page: int = 1,
        page_size: int = 20,
        days: Optional[int] = None,
        rating_filter: Optional[FeedbackRating] = None,
        workspace_id: Optional[str] = None,
    ) -> tuple[List[UserFeedback], int]:
        """
        Get paginated feedback list with optional filters.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            days: Optional filter by days ago
            rating_filter: Optional filter by rating
            workspace_id: Optional filter by workspace (requires join)

        Returns:
            Tuple of (list of feedback items, total count)
        """
        logger.info(
            f"Fetching feedback list (page={page}, page_size={page_size}, "
            f"days={days}, rating={rating_filter}, workspace={workspace_id})"
        )

        items, total = await self.feedback_repo.list_paginated(
            page=page,
            page_size=page_size,
            days=days,
            rating_filter=rating_filter,
        )

        logger.info(f"Fetched feedback list: {len(items)} items, total {total}")
        return items, total
