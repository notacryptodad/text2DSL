"""Admin endpoints for super admin operations."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from text2x.api.auth import get_current_active_user, require_role, require_any_role
from text2x.api.state import app_state
from text2x.api.models import ErrorResponse
from text2x.api.auth import User, get_current_active_user, require_role
from text2x.models.admin import AdminRole, WorkspaceAdmin
from text2x.models.workspace import Workspace
from text2x.repositories.admin import WorkspaceAdminRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


async def get_session() -> AsyncSession:
    """Get database session from app state."""
    session_maker = async_sessionmaker(
        app_state.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session_maker()


# ============================================================================
# Pydantic Models for API
# ============================================================================


class WorkspaceCreateAdmin(BaseModel):
    """Request model for creating a workspace (admin endpoint)."""

    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly identifier",
    )
    description: Optional[str] = Field(None, description="Workspace description")
    settings: Optional[dict] = Field(
        default_factory=dict, description="Workspace-specific settings"
    )
    owner_user_id: str = Field(..., description="User ID of the workspace owner")


class WorkspaceListResponse(BaseModel):
    """Response model for workspace list."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    admin_count: int = 0
    provider_count: int = 0
    created_at: datetime
    updated_at: datetime


class InviteAdminRequest(BaseModel):
    """Request model for inviting a workspace admin."""

    user_id: str = Field(..., description="User ID to invite")
    role: AdminRole = Field(default=AdminRole.ADMIN, description="Role to assign (admin or member)")
    invited_by: str = Field(..., description="User ID of the inviter")


class AssignAdminRequest(BaseModel):
    """Request model for directly assigning a workspace admin (no invitation)."""

    user_id: str = Field(..., description="User ID to assign")
    role: AdminRole = Field(
        default=AdminRole.ADMIN, description="Role to assign (owner, admin, or member)"
    )


class AdminResponse(BaseModel):
    """Response model for workspace admin."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: str
    role: str
    invited_by: str
    invited_at: datetime
    accepted_at: Optional[datetime]
    is_pending: bool
    created_at: datetime
    updated_at: datetime


class AcceptInvitationResponse(BaseModel):
    """Response model for accepting an invitation."""

    success: bool
    message: str
    admin: Optional[AdminResponse] = None


class AdminStatsResponse(BaseModel):
    """Response model for admin dashboard statistics."""

    total_workspaces: int = Field(description="Total number of workspaces")
    total_users: int = Field(description="Total number of users")
    queries_today: int = Field(description="Number of queries made today")
    active_connections: int = Field(description="Number of active database connections")


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get admin dashboard statistics",
    dependencies=[Depends(require_role("super_admin"))],
)
async def get_admin_stats() -> AdminStatsResponse:
    """
    Get statistics for the admin dashboard.

    Returns counts of workspaces, users, today's queries, and active connections.
    """
    try:
        from sqlalchemy import select, func
        from datetime import date
        from text2x.models.workspace import Provider, Connection
        from text2x.models.user import User as UserModel

        async with await get_session() as session:
            # Count workspaces
            workspace_count = await session.scalar(select(func.count()).select_from(Workspace))

            # Count users
            user_count = await session.scalar(select(func.count()).select_from(UserModel))

            # Count active connections
            active_connections = await session.scalar(
                select(func.count()).select_from(Connection).where(Connection.status == "connected")
            )

            # Count queries today (placeholder - would need query log table)
            queries_today = 0

            return AdminStatsResponse(
                total_workspaces=workspace_count or 0,
                total_users=user_count or 0,
                queries_today=queries_today,
                active_connections=active_connections or 0,
            )

    except Exception as e:
        logger.exception(f"Failed to get admin stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="internal_error",
                message="Failed to retrieve admin statistics",
            ).model_dump(mode="json"),
        )


@router.post(
    "/workspaces",
    response_model=WorkspaceListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workspace (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def create_workspace(workspace: WorkspaceCreateAdmin) -> WorkspaceListResponse:
    """
    Create a new workspace with an initial owner.

    This endpoint is for super admins only. It creates a workspace and
    automatically assigns the specified user as the owner.

    Args:
        workspace: Workspace creation data including owner

    Returns:
        Created workspace details
    """
    try:
        logger.info(f"Creating workspace: {workspace.name} with owner: {workspace.owner_user_id}")

        from sqlalchemy import select, func
        from text2x.models.workspace import Provider

        async with await get_session() as session:
            # Check if slug already exists
            stmt = select(Workspace).where(Workspace.slug == workspace.slug)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="validation_error",
                        message=f"Workspace with slug '{workspace.slug}' already exists",
                    ).model_dump(mode="json"),
                )

            # Create workspace
            db_workspace = Workspace(
                name=workspace.name,
                slug=workspace.slug,
                description=workspace.description,
                settings=workspace.settings or {},
            )
            session.add(db_workspace)
            await session.flush()
            await session.refresh(db_workspace)

            # Create owner admin record
            admin_repo = WorkspaceAdminRepository(session)
            await admin_repo.create(
                workspace_id=db_workspace.id,
                user_id=workspace.owner_user_id,
                invited_by="system",
                role=AdminRole.OWNER,
                accepted_at=datetime.utcnow(),
            )

            await session.commit()

            return WorkspaceListResponse(
                id=db_workspace.id,
                name=db_workspace.name,
                slug=db_workspace.slug,
                description=db_workspace.description,
                admin_count=1,
                provider_count=0,
                created_at=db_workspace.created_at,
                updated_at=db_workspace.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workspace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="create_error",
                message="Failed to create workspace",
            ).model_dump(),
        )


@router.get(
    "/workspaces",
    response_model=list[WorkspaceListResponse],
    summary="List all workspaces (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def list_workspaces() -> list[WorkspaceListResponse]:
    """
    List all workspaces in the system.

    This endpoint is for super admins only.

    Returns:
        List of all workspaces with admin and provider counts
    """
    try:
        logger.info("Fetching all workspaces (admin)")

        from sqlalchemy import select, func
        from text2x.models.workspace import Provider

        async with await get_session() as session:
            # Query workspaces with admin and provider counts
            stmt = (
                select(
                    Workspace,
                    func.count(func.distinct(WorkspaceAdmin.id)).label("admin_count"),
                    func.count(func.distinct(Provider.id)).label("provider_count"),
                )
                .outerjoin(WorkspaceAdmin, WorkspaceAdmin.workspace_id == Workspace.id)
                .outerjoin(Provider, Provider.workspace_id == Workspace.id)
                .group_by(Workspace.id)
            )

            result = await session.execute(stmt)
            rows = result.all()

            # Build response models
            workspaces = [
                WorkspaceListResponse(
                    id=workspace.id,
                    name=workspace.name,
                    slug=workspace.slug,
                    description=workspace.description,
                    admin_count=admin_count,
                    provider_count=provider_count,
                    created_at=workspace.created_at,
                    updated_at=workspace.updated_at,
                )
                for workspace, admin_count, provider_count in rows
            ]

            return workspaces

    except Exception as e:
        logger.error(f"Error fetching workspaces: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch workspaces",
            ).model_dump(),
        )


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceListResponse,
    summary="Get workspace details (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def get_workspace(workspace_id: UUID) -> WorkspaceListResponse:
    """
    Get details for a specific workspace.

    Args:
        workspace_id: Workspace UUID

    Returns:
        Workspace details with admin and provider counts
    """
    try:
        logger.info(f"Fetching workspace {workspace_id}")

        from sqlalchemy import select, func
        from text2x.models.workspace import Provider

        async with await get_session() as session:
            stmt = (
                select(
                    Workspace,
                    func.count(func.distinct(WorkspaceAdmin.id)).label("admin_count"),
                    func.count(func.distinct(Provider.id)).label("provider_count"),
                )
                .where(Workspace.id == workspace_id)
                .outerjoin(WorkspaceAdmin, WorkspaceAdmin.workspace_id == Workspace.id)
                .outerjoin(Provider, Provider.workspace_id == Workspace.id)
                .group_by(Workspace.id)
            )

            result = await session.execute(stmt)
            row = result.first()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(),
                )

            workspace, admin_count, provider_count = row

            return WorkspaceListResponse(
                id=workspace.id,
                name=workspace.name,
                slug=workspace.slug,
                description=workspace.description,
                admin_count=admin_count,
                provider_count=provider_count,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch workspace",
            ).model_dump(),
        )


@router.post(
    "/workspaces/{workspace_id}/admins",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite workspace admin",
    dependencies=[Depends(require_role("super_admin"))],
)
async def invite_admin(workspace_id: UUID, invite: InviteAdminRequest) -> AdminResponse:
    """
    Invite a user to be an admin or member of a workspace.

    Creates a pending invitation that the user must accept.

    Args:
        workspace_id: Workspace UUID
        invite: Invitation details (user_id, role, invited_by)

    Returns:
        Created admin invitation
    """
    try:
        logger.info(
            f"Inviting user {invite.user_id} to workspace {workspace_id} as {invite.role.value}"
        )

        from sqlalchemy import select

        # Verify workspace exists and create invitation
        async with await get_session() as session:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(mode="json"),
                )

            # Check if user already has this specific role
            admin_repo = WorkspaceAdminRepository(session)
            existing = await admin_repo.get_by_workspace_user_and_role(
                workspace_id, invite.user_id, invite.role
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="validation_error",
                        message=f"User {invite.user_id} already has the {invite.role.value} role in this workspace",
                    ).model_dump(),
                )

            # Validate role - cannot invite as owner through this endpoint
            if invite.role == AdminRole.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="validation_error",
                        message="Cannot invite users as OWNER. Use admin workspace creation instead.",
                    ).model_dump(),
                )

            # Create invitation
            admin = await admin_repo.create(
                workspace_id=workspace_id,
                user_id=invite.user_id,
                invited_by=invite.invited_by,
                role=invite.role,
            )

            await session.commit()

        return AdminResponse(
            id=admin.id,
            workspace_id=admin.workspace_id,
            user_id=admin.user_id,
            role=admin.role.value,
            invited_by=admin.invited_by,
            invited_at=admin.invited_at,
            accepted_at=admin.accepted_at,
            is_pending=admin.is_pending,
            created_at=admin.created_at,
            updated_at=admin.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting admin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="invite_error",
                message="Failed to invite admin",
            ).model_dump(),
        )


@router.post(
    "/workspaces/{workspace_id}/admins/assign",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Directly assign workspace admin (super admin only)",
    dependencies=[Depends(require_role("super_admin"))],
)
async def assign_admin(workspace_id: UUID, assign: AssignAdminRequest) -> AdminResponse:
    """
    Directly assign a user as workspace admin without invitation.

    This endpoint is for super admins only. It immediately grants
    access to the workspace without requiring the user to accept
    an invitation.

    Args:
        workspace_id: Workspace UUID
        assign: Assignment details (user_id, role)

    Returns:
        Created admin assignment
    """
    try:
        logger.info(
            f"Assigning user {assign.user_id} to workspace {workspace_id} as {assign.role.value}"
        )

        from sqlalchemy import select

        # Verify workspace exists
        async with await get_session() as session:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(mode="json"),
                )

            # Check if user already has this specific role
            admin_repo = WorkspaceAdminRepository(session)
            existing = await admin_repo.get_by_workspace_user_and_role(
                workspace_id, assign.user_id, assign.role
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="validation_error",
                        message=f"User {assign.user_id} already has the {assign.role.value} role in this workspace",
                    ).model_dump(),
                )

            # Create admin assignment with immediate acceptance
            admin = await admin_repo.create(
                workspace_id=workspace_id,
                user_id=assign.user_id,
                invited_by="system",
                role=assign.role,
                accepted_at=datetime.utcnow(),  # Immediate access
            )

            await session.commit()

        return AdminResponse(
            id=admin.id,
            workspace_id=admin.workspace_id,
            user_id=admin.user_id,
            role=admin.role.value,
            invited_by=admin.invited_by,
            invited_at=admin.invited_at,
            accepted_at=admin.accepted_at,
            is_pending=admin.is_pending,
            created_at=admin.created_at,
            updated_at=admin.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning admin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="assign_error",
                message="Failed to assign admin",
            ).model_dump(),
        )


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=AcceptInvitationResponse,
    summary="Accept workspace invitation",
    dependencies=[Depends(get_current_active_user)],
)
async def accept_invitation(invitation_id: UUID) -> AcceptInvitationResponse:
    """
    Accept a pending workspace invitation.

    Args:
        invitation_id: Invitation UUID

    Returns:
        Acceptance confirmation with updated admin details
    """
    try:
        logger.info(f"Accepting invitation {invitation_id}")

        async with await get_session() as session:
            admin_repo = WorkspaceAdminRepository(session)

            # Get invitation
            admin = await admin_repo.get_by_id(invitation_id)

            if not admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Invitation {invitation_id} not found",
                    ).model_dump(),
                )

            # Check if already accepted
            if admin.is_accepted:
                return AcceptInvitationResponse(
                    success=True,
                    message="Invitation already accepted",
                    admin=AdminResponse(
                        id=admin.id,
                        workspace_id=admin.workspace_id,
                        user_id=admin.user_id,
                        role=admin.role.value,
                        invited_by=admin.invited_by,
                        invited_at=admin.invited_at,
                        accepted_at=admin.accepted_at,
                        is_pending=admin.is_pending,
                        created_at=admin.created_at,
                        updated_at=admin.updated_at,
                    ),
                )

            # Accept invitation
            updated_admin = await admin_repo.accept_invitation(invitation_id)

            if not updated_admin:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=ErrorResponse(
                        error="accept_error",
                        message="Failed to accept invitation",
                    ).model_dump(),
                )

            await session.commit()

            return AcceptInvitationResponse(
                success=True,
                message="Invitation accepted successfully",
                admin=AdminResponse(
                    id=updated_admin.id,
                    workspace_id=updated_admin.workspace_id,
                    user_id=updated_admin.user_id,
                    role=updated_admin.role.value,
                    invited_by=updated_admin.invited_by,
                    invited_at=updated_admin.invited_at,
                    accepted_at=updated_admin.accepted_at,
                    is_pending=updated_admin.is_pending,
                    created_at=updated_admin.created_at,
                    updated_at=updated_admin.updated_at,
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="accept_error",
                message="Failed to accept invitation",
            ).model_dump(),
        )


@router.delete(
    "/workspaces/{workspace_id}/admins/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove workspace admin",
    dependencies=[Depends(require_role("super_admin"))],
)
async def remove_admin(workspace_id: UUID, user_id: str) -> None:
    """
    Remove a user's access to a workspace.

    Deletes the admin/member record for the specified user.

    Args:
        workspace_id: Workspace UUID
        user_id: User ID to remove
    """
    try:
        logger.info(f"Removing user {user_id} from workspace {workspace_id}")

        from sqlalchemy import select

        # Verify workspace exists and remove admin
        async with await get_session() as session:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(mode="json"),
                )

            # Get all admin roles for the user
            admin_repo = WorkspaceAdminRepository(session)
            admin_roles = await admin_repo.get_by_workspace_and_user(workspace_id, user_id)

            if not admin_roles:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"User {user_id} is not a member of workspace {workspace_id}",
                    ).model_dump(),
                )

            # Check if user has OWNER role and prevent removing last owner
            has_owner_role = any(admin.role == AdminRole.OWNER for admin in admin_roles)
            if has_owner_role:
                owner_count = await admin_repo.count_by_workspace(
                    workspace_id, role=AdminRole.OWNER
                )
                if owner_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=ErrorResponse(
                            error="validation_error",
                            message="Cannot remove the last owner from a workspace",
                        ).model_dump(mode="json"),
                    )

            # Delete all admin roles for the user
            deleted_count = await admin_repo.delete_by_workspace_and_user(workspace_id, user_id)

            if deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=ErrorResponse(
                        error="delete_error",
                        message="Failed to remove admin",
                    ).model_dump(),
                )

            await session.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing admin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="delete_error",
                message="Failed to remove admin",
            ).model_dump(),
        )


@router.get(
    "/workspaces/{workspace_id}/admins",
    response_model=list[AdminResponse],
    summary="List workspace admins",
    dependencies=[Depends(require_role("super_admin"))],
)
async def list_workspace_admins(workspace_id: UUID) -> list[AdminResponse]:
    """
    List all admins for a workspace.

    This endpoint is for super admins only. Returns both pending
    invitations and accepted admins.

    Args:
        workspace_id: Workspace UUID

    Returns:
        List of workspace admins (both pending and accepted)
    """
    try:
        logger.info(f"Fetching admins for workspace {workspace_id}")

        from sqlalchemy import select

        async with await get_session() as session:
            # Verify workspace exists
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(mode="json"),
                )

            # Get all admins for the workspace
            admin_repo = WorkspaceAdminRepository(session)
            admins = await admin_repo.list_by_workspace(workspace_id)

            return [
                AdminResponse(
                    id=admin.id,
                    workspace_id=admin.workspace_id,
                    user_id=admin.user_id,
                    role=admin.role.value,
                    invited_by=admin.invited_by,
                    invited_at=admin.invited_at,
                    accepted_at=admin.accepted_at,
                    is_pending=admin.is_pending,
                    created_at=admin.created_at,
                    updated_at=admin.updated_at,
                )
                for admin in admins
            ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace admins: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch workspace admins",
            ).model_dump(),
        )


@router.get(
    "/invitations",
    response_model=list[AdminResponse],
    summary="List pending invitations for current user",
)
async def list_invitations(
    current_user: User = Depends(get_current_active_user),
) -> list[AdminResponse]:
    """
    List pending workspace invitations for the current user.

    Returns all pending invitations that the user has not yet accepted.

    Args:
        current_user: Current authenticated user

    Returns:
        List of pending workspace invitations
    """
    try:
        logger.info(f"Fetching pending invitations for user {current_user.id}")

        async with await get_session() as session:
            admin_repo = WorkspaceAdminRepository(session)
            invitations = await admin_repo.list_pending_for_user(current_user.id)

            return [
                AdminResponse(
                    id=invitation.id,
                    workspace_id=invitation.workspace_id,
                    user_id=invitation.user_id,
                    role=invitation.role.value,
                    invited_by=invitation.invited_by,
                    invited_at=invitation.invited_at,
                    accepted_at=invitation.accepted_at,
                    is_pending=invitation.is_pending,
                    created_at=invitation.created_at,
                    updated_at=invitation.updated_at,
                )
                for invitation in invitations
            ]

    except Exception as e:
        logger.error(f"Error fetching invitations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch invitations",
            ).model_dump(),
        )


@router.get(
    "/workspaces/{workspace_id}/invitations",
    response_model=list[AdminResponse],
    summary="List pending invitations for a workspace",
    dependencies=[Depends(require_role("super_admin"))],
)
async def list_workspace_invitations(workspace_id: UUID) -> list[AdminResponse]:
    """
    List pending invitations for a workspace.

    This endpoint is for super admins only. Returns only pending
    invitations that have not been accepted yet.

    Args:
        workspace_id: Workspace UUID

    Returns:
        List of pending workspace invitations
    """
    try:
        logger.info(f"Fetching pending invitations for workspace {workspace_id}")

        from sqlalchemy import select

        async with await get_session() as session:
            # Verify workspace exists
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(mode="json"),
                )

            # Get pending invitations for the workspace
            admin_repo = WorkspaceAdminRepository(session)
            invitations = await admin_repo.list_by_workspace(workspace_id, pending_only=True)

            return [
                AdminResponse(
                    id=invitation.id,
                    workspace_id=invitation.workspace_id,
                    user_id=invitation.user_id,
                    role=invitation.role.value,
                    invited_by=invitation.invited_by,
                    invited_at=invitation.invited_at,
                    accepted_at=invitation.accepted_at,
                    is_pending=invitation.is_pending,
                    created_at=invitation.created_at,
                    updated_at=invitation.updated_at,
                )
                for invitation in invitations
            ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace invitations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch workspace invitations",
            ).model_dump(),
        )


# ============================================================================
# Provider and Connection Admin Endpoints
# ============================================================================


@router.get(
    "/providers",
    summary="List all providers across all workspaces",
)
async def list_all_providers(
    current_user: User = Depends(require_any_role(["super_admin", "admin", "expert"])),
) -> list[dict]:
    """List all providers across all workspaces (admin only)."""
    try:
        from sqlalchemy import select
        from text2x.models.workspace import Provider

        async with await get_session() as session:
            stmt = select(Provider).order_by(Provider.created_at.desc())
            result = await session.execute(stmt)
            providers = result.scalars().all()

            return [
                {
                    "id": str(provider.id),
                    "workspace_id": str(provider.workspace_id),
                    "name": provider.name,
                    "provider_type": provider.type.value,
                    "description": provider.description,
                    "created_at": provider.created_at.isoformat(),
                    "updated_at": provider.updated_at.isoformat(),
                }
                for provider in providers
            ]

    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_error", "message": "Failed to list providers"},
        )


@router.get(
    "/connections",
    summary="List all connections across all providers",
)
async def list_all_connections(
    current_user: User = Depends(require_any_role(["super_admin", "admin", "expert"])),
    provider_id: Optional[str] = None,
) -> list[dict]:
    """List all connections across all providers (admin only)."""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from text2x.models.workspace import Connection, Provider

        async with await get_session() as session:
            stmt = select(Connection).options(selectinload(Connection.provider))

            if provider_id:
                stmt = stmt.where(Connection.provider_id == provider_id)

            stmt = stmt.order_by(Connection.created_at.desc())
            result = await session.execute(stmt)
            connections = result.scalars().all()

            return [
                {
                    "id": str(connection.id),
                    "provider_id": str(connection.provider_id),
                    "provider_name": connection.provider.name if connection.provider else "",
                    "name": connection.name,
                    "host": connection.host,
                    "port": connection.port,
                    "database": connection.database,
                    "status": connection.status.value,
                    "last_schema_refresh": connection.schema_last_refreshed.isoformat()
                    if connection.schema_last_refreshed
                    else None,
                    "created_at": connection.created_at.isoformat(),
                    "updated_at": connection.updated_at.isoformat(),
                }
                for connection in connections
            ]

    except Exception as e:
        logger.error(f"Error listing connections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_error", "message": "Failed to list connections"},
        )
