"""Admin endpoints for super admin operations."""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from text2x.api.models import ErrorResponse
from text2x.models.admin import AdminRole, WorkspaceAdmin
from text2x.models.workspace import Workspace
from text2x.repositories.admin import WorkspaceAdminRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


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
    owner_user_id: str = Field(
        ..., description="User ID of the workspace owner"
    )


class WorkspaceListResponse(BaseModel):
    """Response model for workspace list."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    admin_count: int = 0
    provider_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InviteAdminRequest(BaseModel):
    """Request model for inviting a workspace admin."""

    user_id: str = Field(..., description="User ID to invite")
    role: AdminRole = Field(
        default=AdminRole.ADMIN, description="Role to assign (admin or member)"
    )
    invited_by: str = Field(..., description="User ID of the inviter")


class AdminResponse(BaseModel):
    """Response model for workspace admin."""

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

    class Config:
        from_attributes = True


class AcceptInvitationResponse(BaseModel):
    """Response model for accepting an invitation."""

    success: bool
    message: str
    admin: Optional[AdminResponse] = None


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.post(
    "/workspaces",
    response_model=WorkspaceListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workspace (super admin only)",
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

        from text2x.models.base import get_db
        from sqlalchemy import select, func
        from text2x.models.workspace import Provider

        db = get_db()

        async with db.session() as session:
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
                    ).model_dump(),
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
            admin_repo = WorkspaceAdminRepository()
            await admin_repo.create(
                workspace_id=db_workspace.id,
                user_id=workspace.owner_user_id,
                invited_by="system",
                role=AdminRole.OWNER,
                accepted_at=datetime.utcnow(),
            )

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

        from text2x.models.base import get_db
        from sqlalchemy import select, func
        from text2x.models.workspace import Provider

        db = get_db()

        async with db.session() as session:
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


@router.post(
    "/workspaces/{workspace_id}/admins",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite workspace admin",
)
async def invite_admin(
    workspace_id: UUID, invite: InviteAdminRequest
) -> AdminResponse:
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

        from text2x.models.base import get_db
        from sqlalchemy import select

        db = get_db()

        # Verify workspace exists
        async with db.session() as session:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(),
                )

        # Check if user already has access
        admin_repo = WorkspaceAdminRepository()
        existing = await admin_repo.get_by_workspace_and_user(
            workspace_id, invite.user_id
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error="validation_error",
                    message=f"User {invite.user_id} already has access to this workspace",
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
    "/invitations/{invitation_id}/accept",
    response_model=AcceptInvitationResponse,
    summary="Accept workspace invitation",
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

        admin_repo = WorkspaceAdminRepository()

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

        from text2x.models.base import get_db
        from sqlalchemy import select

        db = get_db()

        # Verify workspace exists
        async with db.session() as session:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await session.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(),
                )

        # Get admin record
        admin_repo = WorkspaceAdminRepository()
        admin = await admin_repo.get_by_workspace_and_user(workspace_id, user_id)

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"User {user_id} is not a member of workspace {workspace_id}",
                ).model_dump(),
            )

        # Prevent removing the last owner
        if admin.role == AdminRole.OWNER:
            owner_count = await admin_repo.count_by_workspace(
                workspace_id, role=AdminRole.OWNER
            )
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="validation_error",
                        message="Cannot remove the last owner from a workspace",
                    ).model_dump(),
                )

        # Delete admin
        success = await admin_repo.delete_by_workspace_and_user(workspace_id, user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error="delete_error",
                    message="Failed to remove admin",
                ).model_dump(),
            )

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
