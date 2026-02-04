"""
Repository for UserFeedback CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.base import get_db
from text2x.models.feedback import FeedbackCategory, FeedbackRating, UserFeedback


class FeedbackRepository:
    """Repository for managing UserFeedback entities."""

    async def create(
        self,
        turn_id: UUID,
        rating: FeedbackRating,
        feedback_category: FeedbackCategory,
        user_id: str,
        feedback_text: Optional[str] = None,
    ) -> UserFeedback:
        """
        Create a new user feedback entry.

        Args:
            turn_id: The conversation turn UUID being rated
            rating: User rating (UP or DOWN)
            feedback_category: Category of feedback
            user_id: User who provided the feedback
            feedback_text: Optional detailed feedback text

        Returns:
            The newly created UserFeedback

        Raises:
            IntegrityError: If feedback already exists for this turn
        """
        db = get_db()
        async with db.session() as session:
            feedback = UserFeedback(
                turn_id=turn_id,
                rating=rating,
                feedback_category=feedback_category,
                user_id=user_id,
                feedback_text=feedback_text,
            )
            session.add(feedback)
            await session.flush()
            await session.refresh(feedback)
            return feedback

    async def get_by_id(self, feedback_id: UUID) -> Optional[UserFeedback]:
        """
        Get feedback by ID.

        Args:
            feedback_id: The feedback UUID

        Returns:
            The feedback if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(UserFeedback).where(UserFeedback.id == feedback_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_turn_id(self, turn_id: UUID) -> Optional[UserFeedback]:
        """
        Get feedback for a specific turn.

        Args:
            turn_id: The conversation turn UUID

        Returns:
            The feedback if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(UserFeedback).where(UserFeedback.turn_id == turn_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        rating: Optional[FeedbackRating] = None,
        limit: int = 50,
    ) -> List[UserFeedback]:
        """
        List feedback provided by a user.

        Args:
            user_id: The user ID
            rating: Optional rating filter (UP or DOWN)
            limit: Maximum number of results

        Returns:
            List of feedback entries
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(UserFeedback)
                .where(UserFeedback.user_id == user_id)
                .order_by(UserFeedback.created_at.desc())
                .limit(limit)
            )
            if rating:
                stmt = stmt.where(UserFeedback.rating == rating)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_rating(
        self,
        rating: FeedbackRating,
        limit: int = 100,
    ) -> List[UserFeedback]:
        """
        List feedback by rating (for analysis).

        Args:
            rating: The rating to filter by (UP or DOWN)
            limit: Maximum number of results

        Returns:
            List of feedback entries
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(UserFeedback)
                .where(UserFeedback.rating == rating)
                .order_by(UserFeedback.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_category(
        self,
        category: FeedbackCategory,
        limit: int = 100,
    ) -> List[UserFeedback]:
        """
        List feedback by category (for analysis).

        Args:
            category: The feedback category
            limit: Maximum number of results

        Returns:
            List of feedback entries
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(UserFeedback)
                .where(UserFeedback.feedback_category == category)
                .order_by(UserFeedback.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_negative_feedback(
        self,
        category: Optional[FeedbackCategory] = None,
        limit: int = 100,
    ) -> List[UserFeedback]:
        """
        List negative feedback (thumbs down) for improvement analysis.

        Args:
            category: Optional category filter
            limit: Maximum number of results

        Returns:
            List of negative feedback entries
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(UserFeedback)
                .where(UserFeedback.rating == FeedbackRating.DOWN)
                .order_by(UserFeedback.created_at.desc())
                .limit(limit)
            )
            if category:
                stmt = stmt.where(UserFeedback.feedback_category == category)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> List[UserFeedback]:
        """
        List recent feedback across all users.

        Args:
            limit: Maximum number of results

        Returns:
            List of recent feedback entries
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(UserFeedback).order_by(UserFeedback.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        days: Optional[int] = None,
        rating_filter: Optional[FeedbackRating] = None,
    ) -> tuple[List[UserFeedback], int]:
        """
        List feedback with pagination and optional filters.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            days: Optional filter by days ago
            rating_filter: Optional filter by rating

        Returns:
            Tuple of (list of feedback items, total count)
        """
        db = get_db()
        async with db.session() as session:
            # Build count query
            count_stmt = select(UserFeedback)
            if days:
                from datetime import datetime, timedelta

                cutoff = datetime.utcnow() - timedelta(days=days)
                count_stmt = count_stmt.where(UserFeedback.created_at >= cutoff)
            if rating_filter:
                count_stmt = count_stmt.where(UserFeedback.rating == rating_filter)

            count_result = await session.execute(count_stmt)
            total = len(count_result.scalars().all())

            # Build main query with pagination
            offset = (page - 1) * page_size
            stmt = select(UserFeedback).offset(offset).limit(page_size)

            if days:
                from datetime import datetime, timedelta

                cutoff = datetime.utcnow() - timedelta(days=days)
                stmt = stmt.where(UserFeedback.created_at >= cutoff)
            if rating_filter:
                stmt = stmt.where(UserFeedback.rating == rating_filter)

            stmt = stmt.order_by(UserFeedback.created_at.desc())

            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def update(
        self,
        feedback_id: UUID,
        rating: Optional[FeedbackRating] = None,
        feedback_category: Optional[FeedbackCategory] = None,
        feedback_text: Optional[str] = None,
    ) -> Optional[UserFeedback]:
        """
        Update existing feedback.

        Args:
            feedback_id: The feedback UUID
            rating: New rating
            feedback_category: New category
            feedback_text: New feedback text

        Returns:
            The updated feedback if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(UserFeedback).where(UserFeedback.id == feedback_id)
            result = await session.execute(stmt)
            feedback = result.scalar_one_or_none()

            if feedback is None:
                return None

            if rating is not None:
                feedback.rating = rating
            if feedback_category is not None:
                feedback.feedback_category = feedback_category
            if feedback_text is not None:
                feedback.feedback_text = feedback_text

            await session.flush()
            await session.refresh(feedback)
            return feedback

    async def delete(self, feedback_id: UUID) -> bool:
        """
        Delete feedback.

        Args:
            feedback_id: The feedback UUID

        Returns:
            True if deleted, False if not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(UserFeedback).where(UserFeedback.id == feedback_id)
            result = await session.execute(stmt)
            feedback = result.scalar_one_or_none()

            if feedback is None:
                return False

            await session.delete(feedback)
            return True
