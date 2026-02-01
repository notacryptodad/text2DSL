"""
Repository for WorkspaceAdmin CRUD operations.

This module provides async database operations for the WorkspaceAdmin model,
handling admin invitations, role management, and access control.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.admin import AdminRole, WorkspaceAdmin
from text2x.models.base import get_db


class WorkspaceAdminRepository:
    """
    Repository for managing WorkspaceAdmin entities.

    Provides async CRUD operations for workspace admins with proper
    relationship loading and error handling. All methods that query by ID
    return None when the admin is not found rather than raising exceptions.
    """

    async def create(
        self,
        workspace_id: UUID,
        user_id: str,
        invited_by: str,
        role: AdminRole = AdminRole.MEMBER,
        invited_at: Optional[datetime] = None,
        accepted_at: Optional[datetime] = None,
    ) -> WorkspaceAdmin:
        """
        Create a new workspace admin record.

        Args:
            workspace_id: The workspace UUID
            user_id: User identifier
            invited_by: User ID who sent the invitation
            role: Admin role (default: MEMBER)
            invited_at: When the invitation was sent (default: now)
            accepted_at: When the invitation was accepted (default: None)

        Returns:
            The newly created workspace admin

        Raises:
            IntegrityError: If user already has a role in this workspace
        """
        db = get_db()
        async with db.session() as session:
            admin = WorkspaceAdmin(
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                invited_by=invited_by,
                invited_at=invited_at or datetime.utcnow(),
                accepted_at=accepted_at,
            )
            session.add(admin)
            await session.flush()
            await session.refresh(admin)
            return admin

    async def get_by_id(self, admin_id: UUID) -> Optional[WorkspaceAdmin]:
        """
        Retrieve a workspace admin by its ID.

        Args:
            admin_id: The workspace admin UUID

        Returns:
            The workspace admin if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_workspace_and_user(
        self, workspace_id: UUID, user_id: str
    ) -> Optional[WorkspaceAdmin]:
        """
        Retrieve a workspace admin by workspace and user.

        Args:
            workspace_id: The workspace UUID
            user_id: User identifier

        Returns:
            The workspace admin if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(
                and_(
                    WorkspaceAdmin.workspace_id == workspace_id,
                    WorkspaceAdmin.user_id == user_id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        role: Optional[AdminRole] = None,
        pending_only: bool = False,
    ) -> List[WorkspaceAdmin]:
        """
        List all admins for a workspace.

        Args:
            workspace_id: The workspace UUID
            role: Filter by role (optional)
            pending_only: Only return pending invitations (default: False)

        Returns:
            List of workspace admins, ordered by created_at descending
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(
                WorkspaceAdmin.workspace_id == workspace_id
            )

            if role is not None:
                stmt = stmt.where(WorkspaceAdmin.role == role)

            if pending_only:
                stmt = stmt.where(WorkspaceAdmin.accepted_at.is_(None))

            stmt = stmt.order_by(WorkspaceAdmin.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_user(self, user_id: str) -> List[WorkspaceAdmin]:
        """
        List all workspaces for a user.

        Args:
            user_id: User identifier

        Returns:
            List of workspace admins for the user, ordered by created_at descending
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(WorkspaceAdmin)
                .where(WorkspaceAdmin.user_id == user_id)
                .order_by(WorkspaceAdmin.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_pending_for_user(self, user_id: str) -> List[WorkspaceAdmin]:
        """
        List pending invitations for a user.

        Args:
            user_id: User identifier

        Returns:
            List of pending workspace invitations for the user
        """
        db = get_db()
        async with db.session() as session:
            stmt = (
                select(WorkspaceAdmin)
                .where(
                    and_(
                        WorkspaceAdmin.user_id == user_id,
                        WorkspaceAdmin.accepted_at.is_(None),
                    )
                )
                .order_by(WorkspaceAdmin.invited_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def accept_invitation(self, admin_id: UUID) -> Optional[WorkspaceAdmin]:
        """
        Accept a workspace invitation.

        Args:
            admin_id: The workspace admin UUID

        Returns:
            The updated workspace admin if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()

            if admin is None:
                return None

            admin.accept_invitation()
            await session.flush()
            await session.refresh(admin)
            return admin

    async def update_role(
        self, admin_id: UUID, role: AdminRole
    ) -> Optional[WorkspaceAdmin]:
        """
        Update an admin's role.

        Args:
            admin_id: The workspace admin UUID
            role: New admin role

        Returns:
            The updated workspace admin if found, None otherwise
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()

            if admin is None:
                return None

            admin.role = role
            await session.flush()
            await session.refresh(admin)
            return admin

    async def delete(self, admin_id: UUID) -> bool:
        """
        Delete a workspace admin by ID.

        Args:
            admin_id: The workspace admin UUID

        Returns:
            True if admin was deleted, False if admin was not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()

            if admin is None:
                return False

            await session.delete(admin)
            return True

    async def delete_by_workspace_and_user(
        self, workspace_id: UUID, user_id: str
    ) -> bool:
        """
        Delete a workspace admin by workspace and user.

        Args:
            workspace_id: The workspace UUID
            user_id: User identifier

        Returns:
            True if admin was deleted, False if admin was not found
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(
                and_(
                    WorkspaceAdmin.workspace_id == workspace_id,
                    WorkspaceAdmin.user_id == user_id,
                )
            )
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()

            if admin is None:
                return False

            await session.delete(admin)
            return True

    async def count_by_workspace(
        self, workspace_id: UUID, role: Optional[AdminRole] = None
    ) -> int:
        """
        Count admins in a workspace.

        Args:
            workspace_id: The workspace UUID
            role: Filter by role (optional)

        Returns:
            Number of admins matching the criteria
        """
        db = get_db()
        async with db.session() as session:
            stmt = select(WorkspaceAdmin).where(
                WorkspaceAdmin.workspace_id == workspace_id
            )

            if role is not None:
                stmt = stmt.where(WorkspaceAdmin.role == role)

            result = await session.execute(stmt)
            return len(list(result.scalars().all()))
