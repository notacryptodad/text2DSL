"""Connection repository for database operations."""
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from text2x.api.state import app_state
from text2x.models.workspace import Connection

logger = logging.getLogger(__name__)


class ConnectionRepository:
    """Repository for connection database operations."""

    def __init__(self, session: Optional[AsyncSession] = None):
        """Initialize repository with optional session."""
        self._session = session

    async def _get_session(self) -> AsyncSession:
        """Get database session."""
        if self._session:
            return self._session

        session_maker = async_sessionmaker(
            app_state.db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return session_maker()

    async def get_by_id(self, connection_id: UUID) -> Optional[Connection]:
        """
        Get connection by ID.

        Args:
            connection_id: UUID of the connection

        Returns:
            Connection if found, None otherwise
        """
        async with await self._get_session() as session:
            stmt = (
                select(Connection)
                .options(selectinload(Connection.provider))
                .where(Connection.id == connection_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_schema_refresh_time(
        self,
        connection_id: UUID,
        schema_cache_key: str
    ) -> bool:
        """
        Update schema refresh timestamp and cache key.

        Args:
            connection_id: UUID of the connection
            schema_cache_key: Redis cache key

        Returns:
            True if updated, False otherwise
        """
        try:
            async with await self._get_session() as session:
                stmt = (
                    update(Connection)
                    .where(Connection.id == connection_id)
                    .values(
                        schema_cache_key=schema_cache_key,
                        schema_last_refreshed=datetime.utcnow()
                    )
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update schema refresh time: {e}")
            return False
