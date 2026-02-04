"""
User feedback models for Text2DSL.

This module defines the database models for capturing user feedback on
generated queries. Feedback helps improve query generation through the
feedback loop.
"""

from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .conversation import ConversationTurn


class FeedbackRating(str, PyEnum):
    """User rating for a generated query."""

    UP = "up"
    DOWN = "down"


class FeedbackCategory(str, PyEnum):
    """Category of feedback provided by the user."""

    INCORRECT_RESULT = "incorrect_result"
    SYNTAX_ERROR = "syntax_error"
    MISSING_CONTEXT = "missing_context"
    PERFORMANCE_ISSUE = "performance_issue"
    CLARIFICATION_NEEDED = "clarification_needed"
    GREAT_RESULT = "great_result"
    OTHER = "other"


class UserFeedback(Base, UUIDMixin, TimestampMixin):
    """
    Represents user feedback on a generated query.

    Feedback is linked to a specific ConversationTurn and captures:
    - Whether the user liked or disliked the result (thumbs up/down)
    - Free-form text feedback explaining their rating
    - A categorization of the feedback type

    This feedback is used to:
    - Improve RAG example selection
    - Identify common failure patterns
    - Track system improvement over time
    - Guide model fine-tuning
    """

    __tablename__ = "user_feedback"

    # Link to the conversation turn being rated
    turn_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation_turns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One feedback per turn
    )

    # Rating (thumbs up/down)
    rating = Column(
        Enum(FeedbackRating, native_enum=False),
        nullable=False,
        index=True,
    )

    # Optional detailed feedback text
    feedback_text = Column(Text, nullable=True)

    # Category of feedback
    feedback_category = Column(
        Enum(FeedbackCategory),
        nullable=False,
        index=True,
    )

    # User who provided feedback
    user_id = Column(Text, nullable=False, index=True)

    # Relationships
    turn: Mapped["ConversationTurn"] = relationship(
        "ConversationTurn",
        back_populates="feedback",
    )

    def __repr__(self) -> str:
        return (
            f"<UserFeedback(id={self.id}, turn_id={self.turn_id}, "
            f"rating={self.rating}, category={self.feedback_category})>"
        )

    @property
    def is_positive(self) -> bool:
        """Check if this is positive feedback (thumbs up)."""
        return self.rating == FeedbackRating.UP

    @property
    def is_negative(self) -> bool:
        """Check if this is negative feedback (thumbs down)."""
        return self.rating == FeedbackRating.DOWN

    def to_dict(self) -> dict:
        """
        Convert feedback to dictionary for API responses.

        Returns:
            Dictionary representation of the feedback
        """
        return {
            "id": str(self.id),
            "turn_id": str(self.turn_id),
            "rating": self.rating.value,
            "feedback_text": self.feedback_text,
            "feedback_category": self.feedback_category.value,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
