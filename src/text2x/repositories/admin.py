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


class WorkspaceAdminRepository:
    """
    Repository for managing WorkspaceAdmin entities.

    Provides async CRUD operations for workspace admins with proper
    relationship loading and error handling. All methods that query by ID
    return None when the admin is not found rather than raising exceptions.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize the repository.

        Args:
            session: Optional database session. If not provided, methods will
                    expect session to be passed in explicitly.
        """
        self.session = session

    async def create(
        self,
        workspace_id: UUID,
        user_id: str,
        invited_by: str,
        role: AdminRole = AdminRole.MEMBER,
        invited_at: Optional[datetime] = None,
        accepted_at: Optional[datetime] = None,
        session: Optional[AsyncSession] = None,
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
            session: Database session (uses instance session if not provided)

        Returns:
            The newly created workspace admin

        Raises:
            IntegrityError: If user already has a role in this workspace
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        admin = WorkspaceAdmin(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
            invited_at=invited_at or datetime.utcnow(),
            accepted_at=accepted_at,
        )
        sess.add(admin)
        await sess.flush()
        await sess.refresh(admin)
        return admin

    async def get_by_id(
        self, admin_id: UUID, session: Optional[AsyncSession] = None
    ) -> Optional[WorkspaceAdmin]:
        """
        Retrieve a workspace admin by its ID.

        Args:
            admin_id: The workspace admin UUID
            session: Database session (uses instance session if not provided)

        Returns:
            The workspace admin if found, None otherwise
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
        result = await sess.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_workspace_and_user(
        self,
        workspace_id: UUID,
        user_id: str,
        session: Optional[AsyncSession] = None,
    ) -> List[WorkspaceAdmin]:
        """
        Retrieve all workspace admin roles for a user in a workspace.

        Note: This now returns a list since users can have multiple roles.
        For single role lookup, use get_by_workspace_user_and_role.

        Args:
            workspace_id: The workspace UUID
            user_id: User identifier
            session: Database session (uses instance session if not provided)

        Returns:
            List of workspace admin records for the user (can have multiple roles)
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(
            and_(
                WorkspaceAdmin.workspace_id == workspace_id,
                WorkspaceAdmin.user_id == user_id,
            )
        )
        result = await sess.execute(stmt)
        return list(result.scalars().all())

    async def get_by_workspace_user_and_role(
        self,
        workspace_id: UUID,
        user_id: str,
        role: AdminRole,
        session: Optional[AsyncSession] = None,
    ) -> Optional[WorkspaceAdmin]:
        """
        Retrieve a specific role assignment for a user in a workspace.

        Args:
            workspace_id: The workspace UUID
            user_id: User identifier
            role: The specific role to lookup
            session: Database session (uses instance session if not provided)

        Returns:
            The workspace admin if found, None otherwise
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(
            and_(
                WorkspaceAdmin.workspace_id == workspace_id,
                WorkspaceAdmin.user_id == user_id,
                WorkspaceAdmin.role == role,
            )
        )
        result = await sess.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        role: Optional[AdminRole] = None,
        pending_only: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> List[WorkspaceAdmin]:
        """
        List all admins for a workspace.

        Args:
            workspace_id: The workspace UUID
            role: Filter by role (optional)
            pending_only: Only return pending invitations (default: False)
            session: Database session (uses instance session if not provided)

        Returns:
            List of workspace admins, ordered by created_at descending
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(
            WorkspaceAdmin.workspace_id == workspace_id
        )

        if role is not None:
            stmt = stmt.where(WorkspaceAdmin.role == role)

        if pending_only:
            stmt = stmt.where(WorkspaceAdmin.accepted_at.is_(None))

        stmt = stmt.order_by(WorkspaceAdmin.created_at.desc())
        result = await sess.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self, user_id: str, session: Optional[AsyncSession] = None
    ) -> List[WorkspaceAdmin]:
        """
        List all workspaces for a user.

        Args:
            user_id: User identifier
            session: Database session (uses instance session if not provided)

        Returns:
            List of workspace admins for the user, ordered by created_at descending
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = (
            select(WorkspaceAdmin)
            .where(WorkspaceAdmin.user_id == user_id)
            .order_by(WorkspaceAdmin.created_at.desc())
        )
        result = await sess.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_for_user(
        self, user_id: str, session: Optional[AsyncSession] = None
    ) -> List[WorkspaceAdmin]:
        """
        List pending invitations for a user.

        Args:
            user_id: User identifier
            session: Database session (uses instance session if not provided)

        Returns:
            List of pending workspace invitations for the user
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

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
        result = await sess.execute(stmt)
        return list(result.scalars().all())

    async def accept_invitation(
        self, admin_id: UUID, session: Optional[AsyncSession] = None
    ) -> Optional[WorkspaceAdmin]:
        """
        Accept a workspace invitation.

        Args:
            admin_id: The workspace admin UUID
            session: Database session (uses instance session if not provided)

        Returns:
            The updated workspace admin if found, None otherwise
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
        result = await sess.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None:
            return None

        admin.accept_invitation()
        await sess.flush()
        await sess.refresh(admin)
        return admin

    async def update_role(
        self, admin_id: UUID, role: AdminRole, session: Optional[AsyncSession] = None
    ) -> Optional[WorkspaceAdmin]:
        """
        Update an admin's role.

        Args:
            admin_id: The workspace admin UUID
            role: New admin role
            session: Database session (uses instance session if not provided)

        Returns:
            The updated workspace admin if found, None otherwise
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
        result = await sess.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None:
            return None

        admin.role = role
        await sess.flush()
        await sess.refresh(admin)
        return admin

    async def delete(
        self, admin_id: UUID, session: Optional[AsyncSession] = None
    ) -> bool:
        """
        Delete a workspace admin by ID.

        Args:
            admin_id: The workspace admin UUID
            session: Database session (uses instance session if not provided)

        Returns:
            True if admin was deleted, False if admin was not found
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(WorkspaceAdmin.id == admin_id)
        result = await sess.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None:
            return False

        await sess.delete(admin)
        return True

    async def delete_by_workspace_and_user(
        self, workspace_id: UUID, user_id: str, session: Optional[AsyncSession] = None
    ) -> int:
        """
        Delete all workspace admin roles for a user.

        Note: This now deletes ALL roles for the user in the workspace.
        For single role deletion, use delete_by_workspace_user_and_role.

        Args:
            workspace_id: The workspace UUID
            user_id: User identifier
            session: Database session (uses instance session if not provided)

        Returns:
            Number of admin records deleted (can be multiple if user has multiple roles)
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(
            and_(
                WorkspaceAdmin.workspace_id == workspace_id,
                WorkspaceAdmin.user_id == user_id,
            )
        )
        result = await sess.execute(stmt)
        admins = list(result.scalars().all())

        if not admins:
            return 0

        for admin in admins:
            await sess.delete(admin)

        return len(admins)

    async def delete_by_workspace_user_and_role(
        self,
        workspace_id: UUID,
        user_id: str,
        role: AdminRole,
        session: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Delete a specific role assignment for a user in a workspace.

        Args:
            workspace_id: The workspace UUID
            user_id: User identifier
            role: The specific role to delete
            session: Database session (uses instance session if not provided)

        Returns:
            True if admin was deleted, False if admin was not found
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(
            and_(
                WorkspaceAdmin.workspace_id == workspace_id,
                WorkspaceAdmin.user_id == user_id,
                WorkspaceAdmin.role == role,
            )
        )
        result = await sess.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None:
            return False

        await sess.delete(admin)
        return True

    async def count_by_workspace(
        self,
        workspace_id: UUID,
        role: Optional[AdminRole] = None,
        session: Optional[AsyncSession] = None,
    ) -> int:
        """
        Count admins in a workspace.

        Args:
            workspace_id: The workspace UUID
            role: Filter by role (optional)
            session: Database session (uses instance session if not provided)

        Returns:
            Number of admins matching the criteria
        """
        sess = session or self.session
        if sess is None:
            raise ValueError("Session must be provided")

        stmt = select(WorkspaceAdmin).where(
            WorkspaceAdmin.workspace_id == workspace_id
        )

        if role is not None:
            stmt = stmt.where(WorkspaceAdmin.role == role)

        result = await sess.execute(stmt)
        return len(list(result.scalars().all()))
