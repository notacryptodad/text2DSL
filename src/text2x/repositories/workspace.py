"""
Repository for Workspace CRUD operations.

This module provides async database operations for the Workspace model,
handling common patterns like eager loading of relationships and
proper session management.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from text2x.models.base import get_db
from text2x.models.workspace import Workspace


class WorkspaceRepository:
    """
    Repository for managing Workspace entities.

    Provides async CRUD operations for workspaces with proper relationship
    loading and error handling. All methods that query by ID return None
    when the workspace is not found rather than raising exceptions.
    """

    async def create(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> Workspace:
        """
        Create a new workspace.

        Args:
            name: Human-readable workspace name
            slug: URL-friendly unique identifier
            description: Optional description of the workspace
            settings: Optional JSON settings for the workspace

        Returns:
            The newly created workspace with providers relationship loaded

        Raises:
            IntegrityError: If slug already exists
        """
        db = get_db()
        async with db.session() as session:
            workspace = Workspace(
                name=name,
                slug=slug,
                description=description,
                settings=settings or {},
            )
            session.add(workspace)
            await session.flush()
            await session.refresh(workspace)
            return workspace

    async def get_by_id(self, workspace_id: UUID) -> Optional[Workspace]:
        """
        Retrieve a workspace by its ID.

        Args:
            workspace_id: The workspace UUID

        Returns:
            The workspace if found, None otherwise. Includes providers
            relationship loaded for calculating provider_count.
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Workspace)
                .where(Workspace.id == workspace_id)
                .options(selectinload(Workspace.providers))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Workspace]:
        """
        Retrieve a workspace by its slug.

        Args:
            slug: The workspace slug (URL-friendly identifier)

        Returns:
            The workspace if found, None otherwise. Includes providers
            relationship loaded for calculating provider_count.
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Workspace)
                .where(Workspace.slug == slug)
                .options(selectinload(Workspace.providers))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_all(self) -> List[Workspace]:
        """
        List all workspaces.

        Returns:
            List of all workspaces, ordered by created_at descending.
            Each workspace includes providers relationship loaded for
            calculating provider_count.
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Workspace)
                .options(selectinload(Workspace.providers))
                .order_by(Workspace.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        workspace_id: UUID,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> Optional[Workspace]:
        """
        Update an existing workspace.

        Only provided fields will be updated. None values are ignored
        unless you want to explicitly set a field to None (for nullable fields).

        Args:
            workspace_id: The workspace UUID
            name: New name (optional)
            slug: New slug (optional)
            description: New description (optional, can be set to None)
            settings: New settings dict (optional)

        Returns:
            The updated workspace if found, None if workspace doesn't exist.
            Includes providers relationship loaded.

        Raises:
            IntegrityError: If slug conflicts with existing workspace
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(Workspace)
                .where(Workspace.id == workspace_id)
                .options(selectinload(Workspace.providers))
            )
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if workspace is None:
                return None

            # Update only provided fields
            if name is not None:
                workspace.name = name
            if slug is not None:
                workspace.slug = slug
            if description is not None:
                workspace.description = description
            if settings is not None:
                workspace.settings = settings

            await session.flush()
            await session.refresh(workspace)
            return workspace

    async def delete(self, workspace_id: UUID) -> bool:
        """
        Delete a workspace by ID.

        This will cascade delete all related providers and connections
        due to the cascade settings on the relationships.

        Args:
            workspace_id: The workspace UUID

        Returns:
            True if workspace was deleted, False if workspace was not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if workspace is None:
                return False

            await session.delete(workspace)
            return True
