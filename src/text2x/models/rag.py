"""
RAG (Retrieval-Augmented Generation) example models for Text2DSL.

This module defines the database models for storing and managing
query examples used in the RAG system. These examples help the
system generate better queries by providing reference patterns.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class ExampleStatus(str, PyEnum):
    """Status of a RAG example in the review pipeline."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RAGExample(Base, UUIDMixin, TimestampMixin):
    """
    Represents a query example for RAG retrieval.

    RAG examples are stored pairs of natural language queries and their
    corresponding generated queries. They can be:
    - Good examples: Successfully generated queries to learn from
    - Bad examples: Failed queries to avoid repeating mistakes

    Examples go through a review pipeline where they can be approved
    or rejected, and experts can provide corrected queries.
    """

    __tablename__ = "rag_examples"

    provider_id = Column(String(255), nullable=False, index=True)
    natural_language_query = Column(Text, nullable=False)
    generated_query = Column(Text, nullable=False)
    is_good_example = Column(Boolean, nullable=False, default=True, index=True)
    status = Column(
        Enum(ExampleStatus, native_enum=False),
        nullable=False,
        default=ExampleStatus.PENDING_REVIEW,
        index=True,
    )

    # Metadata for retrieval and filtering
    involved_tables = Column(ARRAY(String), nullable=False, index=True)
    query_intent = Column(String(100), nullable=False, index=True)
    complexity_level = Column(String(50), nullable=False, index=True)

    # Review information
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    expert_corrected_query = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Source tracking
    source_conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Additional metadata stored as JSON (named extra_metadata to avoid SQLAlchemy reserved 'metadata')
    extra_metadata = Column("metadata", JSON, nullable=True)

    # Note: Question embeddings are stored in OpenSearch/vector DB
    # This field just tracks if embeddings have been generated
    embeddings_generated = Column(Boolean, nullable=False, default=False)

    # Relationships
    source_conversation = relationship("Conversation")

    def __repr__(self) -> str:
        return (
            f"<RAGExample(id={self.id}, provider_id={self.provider_id}, "
            f"intent={self.query_intent}, status={self.status})>"
        )

    def mark_reviewed(
        self,
        reviewer: str,
        approved: bool,
        corrected_query: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """
        Mark this example as reviewed.

        Args:
            reviewer: Username or ID of the reviewer
            approved: Whether the example was approved
            corrected_query: Expert-corrected query if the original was wrong
            notes: Review notes
        """
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()
        self.status = ExampleStatus.APPROVED if approved else ExampleStatus.REJECTED

        if corrected_query:
            self.expert_corrected_query = corrected_query

        if notes:
            self.review_notes = notes

    def get_query_for_rag(self) -> str:
        """
        Get the best query to use for RAG retrieval.

        Returns the expert-corrected query if available, otherwise
        returns the originally generated query.

        Returns:
            Query string to use for RAG
        """
        return self.expert_corrected_query or self.generated_query

    @property
    def is_approved(self) -> bool:
        """Check if this example has been approved."""
        return self.status == ExampleStatus.APPROVED

    @property
    def needs_correction(self) -> bool:
        """Check if this example has been corrected by an expert."""
        return self.expert_corrected_query is not None


class QueryIntent(str, PyEnum):
    """Common query intents for categorization."""

    AGGREGATION = "aggregation"
    FILTER = "filter"
    JOIN = "join"
    SORT = "sort"
    GROUP_BY = "group_by"
    SUBQUERY = "subquery"
    WINDOW_FUNCTION = "window_function"
    CTE = "cte"
    UNION = "union"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    OTHER = "other"


class ComplexityLevel(str, PyEnum):
    """Query complexity levels."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
