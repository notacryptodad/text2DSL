"""
Repository for RAGExample CRUD operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.base import get_db
from text2x.models.rag import RAGExample, ExampleStatus


class RAGExampleRepository:
    """Repository for managing RAGExample entities."""

    async def create(
        self,
        provider_id: str,
        natural_language_query: str,
        generated_query: str,
        involved_tables: List[str],
        query_intent: str,
        complexity_level: str,
        is_good_example: bool = True,
        source_conversation_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> RAGExample:
        """
        Create a new RAG example.

        Args:
            provider_id: The provider ID
            natural_language_query: The natural language query
            generated_query: The generated query
            involved_tables: List of tables involved
            query_intent: Query intent (aggregation, filter, join, etc.)
            complexity_level: Complexity level (simple, medium, complex)
            is_good_example: Whether this is a good example
            source_conversation_id: Optional source conversation UUID
            metadata: Optional extra metadata

        Returns:
            The newly created RAGExample
        """
        db = get_db()
        async with db.session() as session:
            example = RAGExample(
                provider_id=provider_id,
                natural_language_query=natural_language_query,
                generated_query=generated_query,
                involved_tables=involved_tables,
                query_intent=query_intent,
                complexity_level=complexity_level,
                is_good_example=is_good_example,
                source_conversation_id=source_conversation_id,
                extra_metadata=metadata,
                status=ExampleStatus.PENDING_REVIEW,
            )
            session.add(example)
            await session.flush()
            await session.refresh(example)
            return example

    async def get_by_id(self, example_id: UUID) -> Optional[RAGExample]:
        """
        Get an example by ID.

        Args:
            example_id: The example UUID

        Returns:
            The example if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(RAGExample.id == example_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_provider(
        self,
        provider_id: str,
        status: Optional[ExampleStatus] = None,
        is_good_example: Optional[bool] = None,
        limit: int = 100,
    ) -> List[RAGExample]:
        """
        List examples for a provider.

        Args:
            provider_id: The provider ID
            status: Optional status filter
            is_good_example: Optional good/bad filter
            limit: Maximum number of results

        Returns:
            List of examples
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(RAGExample)
                .where(RAGExample.provider_id == provider_id)
                .order_by(RAGExample.created_at.desc())
                .limit(limit)
            )
            if status is not None:
                stmt = stmt.where(RAGExample.status == status)
            if is_good_example is not None:
                stmt = stmt.where(RAGExample.is_good_example == is_good_example)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_pending_review(
        self, provider_id: Optional[str] = None, limit: int = 50
    ) -> List[RAGExample]:
        """
        List examples pending review.

        Args:
            provider_id: Optional provider filter
            limit: Maximum number of results

        Returns:
            List of examples pending review
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(RAGExample)
                .where(RAGExample.status == ExampleStatus.PENDING_REVIEW)
                .order_by(RAGExample.created_at.asc())
                .limit(limit)
            )
            if provider_id:
                stmt = stmt.where(RAGExample.provider_id == provider_id)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_approved(
        self,
        provider_id: str,
        query_intent: Optional[str] = None,
        limit: int = 100,
    ) -> List[RAGExample]:
        """
        List approved examples for RAG retrieval.

        Args:
            provider_id: The provider ID
            query_intent: Optional intent filter
            limit: Maximum number of results

        Returns:
            List of approved examples
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(RAGExample)
                .where(
                    RAGExample.provider_id == provider_id,
                    RAGExample.status == ExampleStatus.APPROVED,
                    RAGExample.is_good_example == True,
                )
                .order_by(RAGExample.created_at.desc())
                .limit(limit)
            )
            if query_intent:
                stmt = stmt.where(RAGExample.query_intent == query_intent)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def mark_reviewed(
        self,
        example_id: UUID,
        reviewer: str,
        approved: bool,
        corrected_query: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[RAGExample]:
        """
        Mark an example as reviewed.

        Args:
            example_id: The example UUID
            reviewer: Username of the reviewer
            approved: Whether the example was approved
            corrected_query: Optional corrected query
            notes: Optional review notes

        Returns:
            The updated example if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(RAGExample.id == example_id)
            result = await session.execute(stmt)
            example = result.scalar_one_or_none()

            if example is None:
                return None

            example.reviewed_by = reviewer
            example.reviewed_at = datetime.utcnow()
            example.status = ExampleStatus.APPROVED if approved else ExampleStatus.REJECTED
            if corrected_query:
                example.expert_corrected_query = corrected_query
            if notes:
                example.review_notes = notes

            await session.flush()
            await session.refresh(example)
            return example

    async def update(
        self,
        example_id: UUID,
        natural_language_query: Optional[str] = None,
        generated_query: Optional[str] = None,
        involved_tables: Optional[List[str]] = None,
        query_intent: Optional[str] = None,
        complexity_level: Optional[str] = None,
        is_good_example: Optional[bool] = None,
    ) -> Optional[RAGExample]:
        """
        Update an example.

        Args:
            example_id: The example UUID
            natural_language_query: New natural language query
            generated_query: New generated query
            involved_tables: New involved tables
            query_intent: New query intent
            complexity_level: New complexity level
            is_good_example: New good/bad flag

        Returns:
            The updated example if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(RAGExample.id == example_id)
            result = await session.execute(stmt)
            example = result.scalar_one_or_none()

            if example is None:
                return None

            if natural_language_query is not None:
                example.natural_language_query = natural_language_query
            if generated_query is not None:
                example.generated_query = generated_query
            if involved_tables is not None:
                example.involved_tables = involved_tables
            if query_intent is not None:
                example.query_intent = query_intent
            if complexity_level is not None:
                example.complexity_level = complexity_level
            if is_good_example is not None:
                example.is_good_example = is_good_example

            await session.flush()
            await session.refresh(example)
            return example

    async def delete(self, example_id: UUID) -> bool:
        """
        Delete an example.

        Args:
            example_id: The example UUID

        Returns:
            True if deleted, False if not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(RAGExample.id == example_id)
            result = await session.execute(stmt)
            example = result.scalar_one_or_none()

            if example is None:
                return False

            await session.delete(example)
            return True
