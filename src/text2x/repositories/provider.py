"""
Provider repository for async CRUD operations.

This module provides data access methods for the Provider model,
including relationship loading and workspace validation.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from text2x.models import Provider, ProviderType, Workspace
from text2x.models.base import get_db


class ProviderRepository:
    """
    Repository for Provider model with async CRUD operations.

    This repository handles all database operations for providers,
    including relationship loading and validation.
    """

    async def create(
        self,
        workspace_id: UUID,
        name: str,
        type: ProviderType,
        description: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> Optional[Provider]:
        """
        Create a new provider in a workspace.

        Args:
            workspace_id: UUID of the parent workspace
            name: Human-readable provider name
            type: Database provider type (postgresql, mysql, etc.)
            description: Optional description of the provider
            settings: Optional provider-specific settings

        Returns:
            Created Provider instance with connections loaded, or None if workspace doesn't exist

        Raises:
            IntegrityError: If a provider with this name already exists in the workspace
        """
        db = get_db()

        async with db.session() as session:
            # Validate workspace exists
            workspace_query = select(Workspace).where(Workspace.id == workspace_id)
            workspace_result = await session.execute(workspace_query)
            workspace = workspace_result.scalar_one_or_none()

            if workspace is None:
                return None

            # Create provider
            provider = Provider(
                workspace_id=workspace_id,
                name=name,
                type=type,
                description=description,
                settings=settings or {},
            )

            session.add(provider)
            await session.flush()
            await session.refresh(provider)

            # Load connections relationship to include connection_count
            await session.execute(
                select(Provider)
                .options(selectinload(Provider.connections))
                .where(Provider.id == provider.id)
            )

            return provider

    async def get_by_id(self, provider_id: UUID) -> Optional[Provider]:
        """
        Get a provider by ID with connections loaded.

        Args:
            provider_id: UUID of the provider

        Returns:
            Provider instance with connections loaded, or None if not found
        """
        db = get_db()

        async with db.session() as session:
            query = (
                select(Provider)
                .options(selectinload(Provider.connections))
                .where(Provider.id == provider_id)
            )

            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        provider_type: Optional[ProviderType] = None,
    ) -> List[Provider]:
        """
        List all providers in a workspace with connections loaded.

        Args:
            workspace_id: UUID of the workspace
            provider_type: Optional filter by provider type

        Returns:
            List of Provider instances with connections loaded
        """
        db = get_db()

        async with db.session() as session:
            query = (
                select(Provider)
                .options(selectinload(Provider.connections))
                .where(Provider.workspace_id == workspace_id)
            )

            if provider_type is not None:
                query = query.where(Provider.type == provider_type)

            query = query.order_by(Provider.created_at)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def update(
        self,
        provider_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> Optional[Provider]:
        """
        Update a provider's attributes.

        Args:
            provider_id: UUID of the provider to update
            name: New name (if provided)
            description: New description (if provided)
            settings: New settings (if provided, will replace existing settings)

        Returns:
            Updated Provider instance with connections loaded, or None if not found

        Raises:
            IntegrityError: If the new name conflicts with another provider in the workspace
        """
        db = get_db()

        async with db.session() as session:
            # Get existing provider
            query = (
                select(Provider)
                .options(selectinload(Provider.connections))
                .where(Provider.id == provider_id)
            )

            result = await session.execute(query)
            provider = result.scalar_one_or_none()

            if provider is None:
                return None

            # Update fields if provided
            if name is not None:
                provider.name = name

            if description is not None:
                provider.description = description

            if settings is not None:
                provider.settings = settings

            await session.flush()
            await session.refresh(provider)

            return provider

    async def delete(self, provider_id: UUID) -> bool:
        """
        Delete a provider and all its connections (cascade).

        Args:
            provider_id: UUID of the provider to delete

        Returns:
            True if provider was deleted, False if not found
        """
        db = get_db()

        async with db.session() as session:
            # Get provider
            query = select(Provider).where(Provider.id == provider_id)
            result = await session.execute(query)
            provider = result.scalar_one_or_none()

            if provider is None:
                return False

            await session.delete(provider)
            return True
