"""Provider repository for database operations."""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from text2x.api.state import app_state
from text2x.models.workspace import Provider

logger = logging.getLogger(__name__)


class ProviderRepository:
    """Repository for provider database operations."""

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

    async def get_by_id(self, provider_id: UUID) -> Optional[Provider]:
        """
        Get provider by ID.

        Args:
            provider_id: UUID of the provider

        Returns:
            Provider if found, None otherwise
        """
        async with await self._get_session() as session:
            stmt = select(Provider).where(Provider.id == provider_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
