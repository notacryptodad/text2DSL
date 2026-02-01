"""
Repository for Conversation and ConversationTurn CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from text2x.models.base import get_db
from text2x.models.conversation import (
    Conversation,
    ConversationStatus,
    ConversationTurn,
)


class ConversationRepository:
    """Repository for managing Conversation entities."""

    async def create(
        self,
        user_id: str,
        connection_id: Optional[UUID] = None,
        provider_id: Optional[str] = None,
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: The user ID
            connection_id: Optional connection UUID
            provider_id: Optional provider ID (for backward compatibility)

        Returns:
            The newly created Conversation
        """
        db = get_db()
        async with db.session() as session:
            conversation = Conversation(
                user_id=user_id,
                connection_id=connection_id,
                provider_id=provider_id,
                status=ConversationStatus.ACTIVE,
            )
            session.add(conversation)
            await session.flush()
            await session.refresh(conversation)
            return conversation

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get a conversation by ID with turns loaded.

        Args:
            conversation_id: The conversation UUID

        Returns:
            The conversation if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .options(selectinload(Conversation.turns))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        status: Optional[ConversationStatus] = None,
        limit: int = 50,
    ) -> List[Conversation]:
        """
        List conversations for a user.

        Args:
            user_id: The user ID
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of conversations
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .options(selectinload(Conversation.turns))
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            if status:
                stmt = stmt.where(Conversation.status == status)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_connection(
        self, connection_id: UUID, limit: int = 50
    ) -> List[Conversation]:
        """
        List conversations for a connection.

        Args:
            connection_id: The connection UUID
            limit: Maximum number of results

        Returns:
            List of conversations
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.connection_id == connection_id)
                .options(selectinload(Conversation.turns))
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_status(
        self, conversation_id: UUID, status: ConversationStatus
    ) -> Optional[Conversation]:
        """
        Update conversation status.

        Args:
            conversation_id: The conversation UUID
            status: New status

        Returns:
            The updated conversation if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .options(selectinload(Conversation.turns))
            )
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation is None:
                return None

            conversation.status = status
            await session.flush()
            await session.refresh(conversation)
            return conversation

    async def delete(self, conversation_id: UUID) -> bool:
        """
        Delete a conversation and all its turns.

        Args:
            conversation_id: The conversation UUID

        Returns:
            True if deleted, False if not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation is None:
                return False

            await session.delete(conversation)
            return True


class ConversationTurnRepository:
    """Repository for managing ConversationTurn entities."""

    async def create(
        self,
        conversation_id: UUID,
        turn_number: int,
        user_input: str,
        generated_query: str,
        confidence_score: float,
        reasoning_trace: dict,
        iterations: int = 1,
        clarification_needed: bool = False,
        clarification_question: Optional[str] = None,
        validation_result: Optional[dict] = None,
        execution_result: Optional[dict] = None,
        schema_context: Optional[dict] = None,
        rag_examples_used: Optional[dict] = None,
    ) -> ConversationTurn:
        """
        Create a new conversation turn.

        Args:
            conversation_id: The conversation UUID
            turn_number: The turn number (1-based)
            user_input: The user's natural language input
            generated_query: The generated query
            confidence_score: Confidence score (0-1)
            reasoning_trace: Reasoning trace JSON
            iterations: Number of iterations
            clarification_needed: Whether clarification is needed
            clarification_question: Clarification question if needed
            validation_result: Validation result JSON
            execution_result: Execution result JSON
            schema_context: Schema context JSON
            rag_examples_used: RAG examples JSON

        Returns:
            The newly created ConversationTurn
        """
        db = get_db()
        async with db.session() as session:
            turn = ConversationTurn(
                conversation_id=conversation_id,
                turn_number=turn_number,
                user_input=user_input,
                generated_query=generated_query,
                confidence_score=confidence_score,
                reasoning_trace=reasoning_trace,
                iterations=iterations,
                clarification_needed=clarification_needed,
                clarification_question=clarification_question,
                validation_result=validation_result,
                execution_result=execution_result,
                schema_context=schema_context,
                rag_examples_used=rag_examples_used,
            )
            session.add(turn)
            await session.flush()
            await session.refresh(turn)
            return turn

    async def get_by_id(self, turn_id: UUID) -> Optional[ConversationTurn]:
        """
        Get a turn by ID.

        Args:
            turn_id: The turn UUID

        Returns:
            The turn if found, None otherwise
        """
        from sqlalchemy.orm import selectinload

        db = get_db()
        async with db.session() as session:
            stmt = (
                select(ConversationTurn)
                .where(ConversationTurn.id == turn_id)
                .options(selectinload(ConversationTurn.conversation))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_conversation(
        self, conversation_id: UUID
    ) -> List[ConversationTurn]:
        """
        List all turns for a conversation.

        Args:
            conversation_id: The conversation UUID

        Returns:
            List of turns ordered by turn number
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(ConversationTurn)
                .where(ConversationTurn.conversation_id == conversation_id)
                .order_by(ConversationTurn.turn_number)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        turn_id: UUID,
        generated_query: Optional[str] = None,
        confidence_score: Optional[float] = None,
        iterations: Optional[int] = None,
        validation_result: Optional[dict] = None,
        execution_result: Optional[dict] = None,
    ) -> Optional[ConversationTurn]:
        """
        Update a conversation turn.

        Args:
            turn_id: The turn UUID
            generated_query: New generated query
            confidence_score: New confidence score
            iterations: New iteration count
            validation_result: New validation result
            execution_result: New execution result

        Returns:
            The updated turn if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(ConversationTurn).where(ConversationTurn.id == turn_id)
            result = await session.execute(stmt)
            turn = result.scalar_one_or_none()

            if turn is None:
                return None

            if generated_query is not None:
                turn.generated_query = generated_query
            if confidence_score is not None:
                turn.confidence_score = confidence_score
            if iterations is not None:
                turn.iterations = iterations
            if validation_result is not None:
                turn.validation_result = validation_result
            if execution_result is not None:
                turn.execution_result = execution_result

            await session.flush()
            await session.refresh(turn)
            return turn
