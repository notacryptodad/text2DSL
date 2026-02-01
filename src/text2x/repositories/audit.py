"""
Repository for AuditLog CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.base import get_db
from text2x.models.audit import AuditLog


class AuditLogRepository:
    """Repository for managing AuditLog entities."""

    async def create(
        self,
        conversation_id: UUID,
        turn_id: UUID,
        user_input: str,
        provider_id: str,
        schema_context_used: dict,
        final_query: str,
        confidence_score: float,
        validation_status: str,
        model_used: str,
        total_latency_ms: int,
        iterations: int = 1,
        rag_examples_retrieved: Optional[List[UUID]] = None,
        execution_success: bool = False,
        execution_error: Optional[str] = None,
        total_tokens_input: int = 0,
        total_tokens_output: int = 0,
        total_cost_usd: float = 0.0,
        schema_agent_latency_ms: Optional[int] = None,
        rag_retrieval_latency_ms: Optional[int] = None,
        query_builder_latency_ms: Optional[int] = None,
        validator_latency_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            conversation_id: The conversation UUID
            turn_id: The conversation turn UUID
            user_input: The user's natural language input
            provider_id: The provider ID
            schema_context_used: Schema context JSON
            final_query: The final generated query
            confidence_score: Confidence score (0-1)
            validation_status: Validation status
            model_used: LLM model used
            total_latency_ms: Total processing latency
            iterations: Number of iterations
            rag_examples_retrieved: List of RAG example UUIDs used
            execution_success: Whether execution succeeded
            execution_error: Error message if execution failed
            total_tokens_input: Input tokens used
            total_tokens_output: Output tokens used
            total_cost_usd: Cost in USD
            schema_agent_latency_ms: Schema agent latency
            rag_retrieval_latency_ms: RAG retrieval latency
            query_builder_latency_ms: Query builder latency
            validator_latency_ms: Validator latency
            metadata: Optional extra metadata

        Returns:
            The newly created AuditLog
        """
        db = get_db()
        async with db.session() as session:
            audit_log = AuditLog(
                conversation_id=conversation_id,
                turn_id=turn_id,
                user_input=user_input,
                provider_id=provider_id,
                schema_context_used=schema_context_used,
                final_query=final_query,
                confidence_score=confidence_score,
                validation_status=validation_status,
                model_used=model_used,
                total_latency_ms=total_latency_ms,
                iterations=iterations,
                rag_examples_retrieved=rag_examples_retrieved,
                execution_success=execution_success,
                execution_error=execution_error,
                total_tokens_input=total_tokens_input,
                total_tokens_output=total_tokens_output,
                total_cost_usd=total_cost_usd,
                schema_agent_latency_ms=schema_agent_latency_ms,
                rag_retrieval_latency_ms=rag_retrieval_latency_ms,
                query_builder_latency_ms=query_builder_latency_ms,
                validator_latency_ms=validator_latency_ms,
                extra_metadata=metadata,
            )
            session.add(audit_log)
            await session.flush()
            await session.refresh(audit_log)
            return audit_log

    async def get_by_id(self, audit_id: UUID) -> Optional[AuditLog]:
        """
        Get an audit log by ID.

        Args:
            audit_id: The audit log UUID

        Returns:
            The audit log if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(AuditLog).where(AuditLog.id == audit_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_turn_id(self, turn_id: UUID) -> Optional[AuditLog]:
        """
        Get an audit log by turn ID.

        Args:
            turn_id: The conversation turn UUID

        Returns:
            The audit log if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(AuditLog).where(AuditLog.turn_id == turn_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_conversation(self, conversation_id: UUID) -> List[AuditLog]:
        """
        List audit logs for a conversation.

        Args:
            conversation_id: The conversation UUID

        Returns:
            List of audit logs
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(AuditLog)
                .where(AuditLog.conversation_id == conversation_id)
                .order_by(AuditLog.created_at.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_provider(
        self, provider_id: str, limit: int = 100
    ) -> List[AuditLog]:
        """
        List audit logs for a provider.

        Args:
            provider_id: The provider ID
            limit: Maximum number of results

        Returns:
            List of audit logs
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(AuditLog)
                .where(AuditLog.provider_id == provider_id)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_recent(
        self,
        limit: int = 100,
        execution_success: Optional[bool] = None,
    ) -> List[AuditLog]:
        """
        List recent audit logs.

        Args:
            limit: Maximum number of results
            execution_success: Optional success filter

        Returns:
            List of audit logs
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            )
            if execution_success is not None:
                stmt = stmt.where(AuditLog.execution_success == execution_success)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def add_agent_trace(
        self,
        audit_id: UUID,
        agent_name: str,
        trace_data: dict,
        latency_ms: Optional[int] = None,
    ) -> Optional[AuditLog]:
        """
        Add agent trace data to an audit log.

        Args:
            audit_id: The audit log UUID
            agent_name: Agent name (schema, query_builder, validator)
            trace_data: Trace data JSON
            latency_ms: Agent latency in ms

        Returns:
            The updated audit log if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(AuditLog).where(AuditLog.id == audit_id)
            result = await session.execute(stmt)
            audit_log = result.scalar_one_or_none()

            if audit_log is None:
                return None

            if agent_name == "schema":
                audit_log.schema_agent_trace = trace_data
                if latency_ms:
                    audit_log.schema_agent_latency_ms = latency_ms
            elif agent_name == "query_builder":
                audit_log.query_builder_trace = trace_data
                if latency_ms:
                    audit_log.query_builder_latency_ms = latency_ms
            elif agent_name == "validator":
                audit_log.validator_trace = trace_data
                if latency_ms:
                    audit_log.validator_latency_ms = latency_ms

            await session.flush()
            await session.refresh(audit_log)
            return audit_log

    async def add_cost(
        self,
        audit_id: UUID,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> Optional[AuditLog]:
        """
        Add cost information to an audit log.

        Args:
            audit_id: The audit log UUID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD

        Returns:
            The updated audit log if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(AuditLog).where(AuditLog.id == audit_id)
            result = await session.execute(stmt)
            audit_log = result.scalar_one_or_none()

            if audit_log is None:
                return None

            audit_log.total_tokens_input += input_tokens
            audit_log.total_tokens_output += output_tokens
            audit_log.total_cost_usd += cost_usd

            await session.flush()
            await session.refresh(audit_log)
            return audit_log

    async def delete(self, audit_id: UUID) -> bool:
        """
        Delete an audit log.

        Args:
            audit_id: The audit log UUID

        Returns:
            True if deleted, False if not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(AuditLog).where(AuditLog.id == audit_id)
            result = await session.execute(stmt)
            audit_log = result.scalar_one_or_none()

            if audit_log is None:
                return False

            await session.delete(audit_log)
            return True
