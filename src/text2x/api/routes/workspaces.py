"""Workspace management endpoints."""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from text2x.api.state import app_state
from text2x.api.models import ErrorResponse
from text2x.models.workspace import Workspace, Provider, Connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


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

class WorkspaceCreate(BaseModel):
    """Request model for creating a workspace."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$", description="URL-friendly identifier")
    description: Optional[str] = Field(None, description="Workspace description")
    settings: Optional[dict] = Field(default_factory=dict, description="Workspace-specific settings")


class WorkspaceUpdate(BaseModel):
    """Request model for updating a workspace."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[dict] = None


class WorkspaceResponse(BaseModel):
    """Response model for workspace."""
    
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    settings: Optional[dict]
    provider_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProviderCreate(BaseModel):
    """Request model for creating a provider."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Provider name")
    type: str = Field(..., description="Provider type (postgresql, mysql, athena, etc.)")
    description: Optional[str] = None
    settings: Optional[dict] = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    """Request model for updating a provider."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[dict] = None


class ProviderResponse(BaseModel):
    """Response model for provider."""
    
    id: UUID
    workspace_id: UUID
    name: str
    type: str
    description: Optional[str]
    settings: Optional[dict]
    connection_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConnectionCreate(BaseModel):
    """Request model for creating a connection."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Connection name (e.g., Production, Staging)")
    host: str = Field(..., min_length=1, max_length=512, description="Database host/endpoint")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Database port")
    database: str = Field(..., min_length=1, max_length=255, description="Database/catalog name")
    schema_name: Optional[str] = Field(None, max_length=255, description="Schema/namespace within database")
    credentials: Optional[dict] = Field(None, description="Connection credentials (username, password, etc.)")
    connection_options: Optional[dict] = Field(default_factory=dict, description="Additional connection parameters")


class ConnectionUpdate(BaseModel):
    """Request model for updating a connection."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    host: Optional[str] = Field(None, min_length=1, max_length=512)
    port: Optional[int] = Field(None, ge=1, le=65535)
    database: Optional[str] = Field(None, min_length=1, max_length=255)
    schema_name: Optional[str] = None
    credentials: Optional[dict] = None
    connection_options: Optional[dict] = None


class ConnectionResponse(BaseModel):
    """Response model for connection."""
    
    id: UUID
    provider_id: UUID
    name: str
    host: str
    port: Optional[int]
    database: str
    schema_name: Optional[str]
    status: str
    status_message: Optional[str]
    last_health_check: Optional[datetime]
    schema_last_refreshed: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConnectionTestResult(BaseModel):
    """Response model for connection test."""
    
    success: bool
    message: str
    latency_ms: Optional[float] = None


# ============================================================================
# Workspace Endpoints
# ============================================================================

@router.get(
    "",
    response_model=list[WorkspaceResponse],
    summary="List all workspaces",
)
async def list_workspaces() -> list[WorkspaceResponse]:
    """
    List all workspaces.

    Returns:
        List of workspaces
    """
    try:
        logger.info("Fetching list of workspaces")

        async with await get_session() as session:
            # Query workspaces with provider count
            stmt = select(
                Workspace,
                func.count(Provider.id).label("provider_count")
            ).outerjoin(Provider).group_by(Workspace.id)

            result = await session.execute(stmt)
            rows = result.all()

            # Build response models
            workspaces = [
                WorkspaceResponse(
                    id=workspace.id,
                    name=workspace.name,
                    slug=workspace.slug,
                    description=workspace.description,
                    settings=workspace.settings or {},
                    provider_count=provider_count,
                    created_at=workspace.created_at,
                    updated_at=workspace.updated_at,
                )
                for workspace, provider_count in rows
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
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
async def create_workspace(workspace: WorkspaceCreate) -> WorkspaceResponse:
    """
    Create a new workspace.

    Args:
        workspace: Workspace creation data

    Returns:
        Created workspace
    """
    try:
        logger.info(f"Creating workspace: {workspace.name}")

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
            await session.commit()
            await session.refresh(db_workspace)

            return WorkspaceResponse(
                id=db_workspace.id,
                name=db_workspace.name,
                slug=db_workspace.slug,
                description=db_workspace.description,
                settings=db_workspace.settings or {},
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
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace details",
)
async def get_workspace(workspace_id: UUID) -> WorkspaceResponse:
    """
    Get workspace details by ID.

    Args:
        workspace_id: Workspace UUID

    Returns:
        Workspace details
    """
    try:
        logger.info(f"Fetching workspace: {workspace_id}")

        async with await get_session() as session:
            # Query workspace with provider count
            stmt = select(
                Workspace,
                func.count(Provider.id).label("provider_count")
            ).outerjoin(Provider).where(Workspace.id == workspace_id).group_by(Workspace.id)

            result = await session.execute(stmt)
            row = result.one_or_none()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(),
                )

            workspace, provider_count = row

            return WorkspaceResponse(
                id=workspace.id,
                name=workspace.name,
                slug=workspace.slug,
                description=workspace.description,
                settings=workspace.settings or {},
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


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update workspace",
)
async def update_workspace(workspace_id: UUID, update: WorkspaceUpdate) -> WorkspaceResponse:
    """
    Update workspace details.

    Args:
        workspace_id: Workspace UUID
        update: Fields to update

    Returns:
        Updated workspace
    """
    try:
        logger.info(f"Updating workspace: {workspace_id}")

        async with await get_session() as session:
            # Fetch workspace
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

            # Update fields
            if update.name is not None:
                workspace.name = update.name
            if update.description is not None:
                workspace.description = update.description
            if update.settings is not None:
                workspace.settings = update.settings

            await session.commit()
            await session.refresh(workspace)

            # Get provider count
            count_stmt = select(func.count(Provider.id)).where(Provider.workspace_id == workspace_id)
            count_result = await session.execute(count_stmt)
            provider_count = count_result.scalar() or 0

            return WorkspaceResponse(
                id=workspace.id,
                name=workspace.name,
                slug=workspace.slug,
                description=workspace.description,
                settings=workspace.settings or {},
                provider_count=provider_count,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workspace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="update_error",
                message="Failed to update workspace",
            ).model_dump(),
        )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace",
)
async def delete_workspace(workspace_id: UUID) -> None:
    """
    Delete a workspace and all its providers/connections.

    Args:
        workspace_id: Workspace UUID
    """
    try:
        logger.info(f"Deleting workspace: {workspace_id}")

        async with await get_session() as session:
            # Check if workspace exists
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

            # Delete workspace (cascades to providers and connections)
            await session.delete(workspace)
            await session.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="delete_error",
                message="Failed to delete workspace",
            ).model_dump(),
        )


# ============================================================================
# Provider Endpoints (nested under workspace)
# ============================================================================

@router.get(
    "/{workspace_id}/providers",
    response_model=list[ProviderResponse],
    summary="List providers in workspace",
)
async def list_workspace_providers(workspace_id: UUID) -> list[ProviderResponse]:
    """
    List all providers in a workspace.

    Args:
        workspace_id: Workspace UUID

    Returns:
        List of providers
    """
    try:
        logger.info(f"Fetching providers for workspace: {workspace_id}")

        async with await get_session() as session:
            # Verify workspace exists
            workspace_stmt = select(Workspace).where(Workspace.id == workspace_id)
            workspace_result = await session.execute(workspace_stmt)
            if not workspace_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(),
                )

            # Query providers with connection count
            stmt = select(
                Provider,
                func.count(Connection.id).label("connection_count")
            ).outerjoin(Connection).where(Provider.workspace_id == workspace_id).group_by(Provider.id)

            result = await session.execute(stmt)
            rows = result.all()

            # Build response models
            providers = [
                ProviderResponse(
                    id=provider.id,
                    workspace_id=provider.workspace_id,
                    name=provider.name,
                    type=provider.type.value,
                    description=provider.description,
                    settings=provider.settings or {},
                    connection_count=connection_count,
                    created_at=provider.created_at,
                    updated_at=provider.updated_at,
                )
                for provider, connection_count in rows
            ]

            return providers

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching providers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch providers",
            ).model_dump(),
        )


@router.post(
    "/{workspace_id}/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create provider in workspace",
)
async def create_provider(workspace_id: UUID, provider: ProviderCreate) -> ProviderResponse:
    """
    Create a new provider in a workspace.

    Args:
        workspace_id: Workspace UUID
        provider: Provider creation data

    Returns:
        Created provider
    """
    try:
        logger.info(f"Creating provider in workspace {workspace_id}: {provider.name}")

        async with await get_session() as session:
            # Verify workspace exists
            workspace_stmt = select(Workspace).where(Workspace.id == workspace_id)
            workspace_result = await session.execute(workspace_stmt)
            if not workspace_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Workspace {workspace_id} not found",
                    ).model_dump(),
                )

            # Check if provider name already exists in workspace
            check_stmt = select(Provider).where(
                Provider.workspace_id == workspace_id,
                Provider.name == provider.name
            )
            check_result = await session.execute(check_stmt)
            if check_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="validation_error",
                        message=f"Provider with name '{provider.name}' already exists in this workspace",
                    ).model_dump(),
                )

            # Import ProviderType enum
            from text2x.models.workspace import ProviderType

            # Create provider
            db_provider = Provider(
                workspace_id=workspace_id,
                name=provider.name,
                type=ProviderType(provider.type),
                description=provider.description,
                settings=provider.settings or {},
            )
            session.add(db_provider)
            await session.commit()
            await session.refresh(db_provider)

            return ProviderResponse(
                id=db_provider.id,
                workspace_id=db_provider.workspace_id,
                name=db_provider.name,
                type=db_provider.type.value,
                description=db_provider.description,
                settings=db_provider.settings or {},
                connection_count=0,
                created_at=db_provider.created_at,
                updated_at=db_provider.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating provider: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="create_error",
                message="Failed to create provider",
            ).model_dump(),
        )


@router.get(
    "/{workspace_id}/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Get provider details",
)
async def get_provider(workspace_id: UUID, provider_id: UUID) -> ProviderResponse:
    """
    Get provider details.

    Args:
        workspace_id: Workspace UUID
        provider_id: Provider UUID

    Returns:
        Provider details
    """
    try:
        async with await get_session() as session:
            # Query provider with connection count
            stmt = select(
                Provider,
                func.count(Connection.id).label("connection_count")
            ).outerjoin(Connection).where(
                Provider.id == provider_id,
                Provider.workspace_id == workspace_id
            ).group_by(Provider.id)

            result = await session.execute(stmt)
            row = result.one_or_none()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found in workspace {workspace_id}",
                    ).model_dump(),
                )

            provider, connection_count = row

            return ProviderResponse(
                id=provider.id,
                workspace_id=provider.workspace_id,
                name=provider.name,
                type=provider.type.value,
                description=provider.description,
                settings=provider.settings or {},
                connection_count=connection_count,
                created_at=provider.created_at,
                updated_at=provider.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching provider: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch provider",
            ).model_dump(),
        )


@router.patch(
    "/{workspace_id}/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="Update provider",
)
async def update_provider(
    workspace_id: UUID,
    provider_id: UUID,
    update: ProviderUpdate
) -> ProviderResponse:
    """
    Update provider details.
    """
    try:
        async with await get_session() as session:
            # Fetch provider
            stmt = select(Provider).where(
                Provider.id == provider_id,
                Provider.workspace_id == workspace_id
            )
            result = await session.execute(stmt)
            provider = result.scalar_one_or_none()

            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found in workspace {workspace_id}",
                    ).model_dump(),
                )

            # Update fields
            if update.name is not None:
                provider.name = update.name
            if update.description is not None:
                provider.description = update.description
            if update.settings is not None:
                provider.settings = update.settings

            await session.commit()
            await session.refresh(provider)

            # Get connection count
            count_stmt = select(func.count(Connection.id)).where(Connection.provider_id == provider_id)
            count_result = await session.execute(count_stmt)
            connection_count = count_result.scalar() or 0

            return ProviderResponse(
                id=provider.id,
                workspace_id=provider.workspace_id,
                name=provider.name,
                type=provider.type.value,
                description=provider.description,
                settings=provider.settings or {},
                connection_count=connection_count,
                created_at=provider.created_at,
                updated_at=provider.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating provider: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="update_error",
                message="Failed to update provider",
            ).model_dump(),
        )


@router.delete(
    "/{workspace_id}/providers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete provider",
)
async def delete_provider(workspace_id: UUID, provider_id: UUID) -> None:
    """
    Delete a provider and all its connections.
    """
    try:
        logger.info(f"Deleting provider {provider_id} from workspace {workspace_id}")

        async with await get_session() as session:
            # Check if provider exists
            stmt = select(Provider).where(
                Provider.id == provider_id,
                Provider.workspace_id == workspace_id
            )
            result = await session.execute(stmt)
            provider = result.scalar_one_or_none()

            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found in workspace {workspace_id}",
                    ).model_dump(),
                )

            # Delete provider (cascades to connections)
            await session.delete(provider)
            await session.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting provider: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="delete_error",
                message="Failed to delete provider",
            ).model_dump(),
        )


# ============================================================================
# Connection Endpoints (nested under provider)
# ============================================================================

@router.get(
    "/{workspace_id}/providers/{provider_id}/connections",
    response_model=list[ConnectionResponse],
    summary="List connections for provider",
)
async def list_connections(workspace_id: UUID, provider_id: UUID) -> list[ConnectionResponse]:
    """
    List all connections for a provider.

    Args:
        workspace_id: Workspace UUID
        provider_id: Provider UUID

    Returns:
        List of connections
    """
    try:
        logger.info(f"Fetching connections for provider: {provider_id}")

        async with await get_session() as session:
            # Verify provider exists and belongs to workspace
            provider_stmt = select(Provider).where(
                Provider.id == provider_id,
                Provider.workspace_id == workspace_id
            )
            provider_result = await session.execute(provider_stmt)
            if not provider_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found in workspace {workspace_id}",
                    ).model_dump(),
                )

            # Query connections
            stmt = select(Connection).where(Connection.provider_id == provider_id)
            result = await session.execute(stmt)
            connections = result.scalars().all()

            return [
                ConnectionResponse(
                    id=conn.id,
                    provider_id=conn.provider_id,
                    name=conn.name,
                    host=conn.host,
                    port=conn.port,
                    database=conn.database,
                    schema_name=conn.schema_name,
                    status=conn.status.value,
                    status_message=conn.status_message,
                    last_health_check=conn.last_health_check,
                    schema_last_refreshed=conn.schema_last_refreshed,
                    created_at=conn.created_at,
                    updated_at=conn.updated_at,
                )
                for conn in connections
            ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching connections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch connections",
            ).model_dump(),
        )


@router.post(
    "/{workspace_id}/providers/{provider_id}/connections",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create connection",
)
async def create_connection(
    workspace_id: UUID,
    provider_id: UUID,
    connection: ConnectionCreate
) -> ConnectionResponse:
    """
    Create a new connection for a provider.

    Args:
        workspace_id: Workspace UUID
        provider_id: Provider UUID
        connection: Connection creation data

    Returns:
        Created connection
    """
    try:
        logger.info(f"Creating connection for provider {provider_id}: {connection.name}")

        async with await get_session() as session:
            # Verify provider exists and belongs to workspace
            provider_stmt = select(Provider).where(
                Provider.id == provider_id,
                Provider.workspace_id == workspace_id
            )
            provider_result = await session.execute(provider_stmt)
            if not provider_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found in workspace {workspace_id}",
                    ).model_dump(),
                )

            # Check if connection name already exists for this provider
            check_stmt = select(Connection).where(
                Connection.provider_id == provider_id,
                Connection.name == connection.name
            )
            check_result = await session.execute(check_stmt)
            if check_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="validation_error",
                        message=f"Connection with name '{connection.name}' already exists for this provider",
                    ).model_dump(),
                )

            # Create connection
            db_connection = Connection(
                provider_id=provider_id,
                name=connection.name,
                host=connection.host,
                port=connection.port,
                database=connection.database,
                schema_name=connection.schema_name,
                credentials=connection.credentials,
                connection_options=connection.connection_options or {},
            )
            session.add(db_connection)
            await session.commit()
            await session.refresh(db_connection)

            return ConnectionResponse(
                id=db_connection.id,
                provider_id=db_connection.provider_id,
                name=db_connection.name,
                host=db_connection.host,
                port=db_connection.port,
                database=db_connection.database,
                schema_name=db_connection.schema_name,
                status=db_connection.status.value,
                status_message=db_connection.status_message,
                last_health_check=db_connection.last_health_check,
                schema_last_refreshed=db_connection.schema_last_refreshed,
                created_at=db_connection.created_at,
                updated_at=db_connection.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="create_error",
                message="Failed to create connection",
            ).model_dump(),
        )


@router.get(
    "/{workspace_id}/providers/{provider_id}/connections/{connection_id}",
    response_model=ConnectionResponse,
    summary="Get connection details",
)
async def get_connection(
    workspace_id: UUID, 
    provider_id: UUID, 
    connection_id: UUID
) -> ConnectionResponse:
    """
    Get connection details.
    """
    try:
        return ConnectionResponse(
            id=connection_id,
            provider_id=provider_id,
            name="Production",
            host="prod-db.example.com",
            port=5432,
            database="ecommerce",
            schema_name="public",
            status="connected",
            status_message=None,
            last_health_check=datetime.utcnow(),
            schema_last_refreshed=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Error fetching connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch connection",
            ).model_dump(),
        )


@router.patch(
    "/{workspace_id}/providers/{provider_id}/connections/{connection_id}",
    response_model=ConnectionResponse,
    summary="Update connection",
)
async def update_connection(
    workspace_id: UUID,
    provider_id: UUID,
    connection_id: UUID,
    update: ConnectionUpdate,
) -> ConnectionResponse:
    """
    Update connection details.
    """
    try:
        return ConnectionResponse(
            id=connection_id,
            provider_id=provider_id,
            name=update.name or "Production",
            host=update.host or "prod-db.example.com",
            port=update.port or 5432,
            database=update.database or "ecommerce",
            schema_name=update.schema_name,
            status="connected",
            status_message=None,
            last_health_check=datetime.utcnow(),
            schema_last_refreshed=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Error updating connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="update_error",
                message="Failed to update connection",
            ).model_dump(),
        )


@router.delete(
    "/{workspace_id}/providers/{provider_id}/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete connection",
)
async def delete_connection(
    workspace_id: UUID, 
    provider_id: UUID, 
    connection_id: UUID
) -> None:
    """
    Delete a connection.
    """
    try:
        logger.info(f"Deleting connection {connection_id}")
        # TODO: Delete from database
        
    except Exception as e:
        logger.error(f"Error deleting connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="delete_error",
                message="Failed to delete connection",
            ).model_dump(),
        )


@router.post(
    "/{workspace_id}/providers/{provider_id}/connections/{connection_id}/test",
    response_model=ConnectionTestResult,
    summary="Test connection",
)
async def test_connection(
    workspace_id: UUID,
    provider_id: UUID,
    connection_id: UUID
) -> ConnectionTestResult:
    """
    Test a connection to verify connectivity.

    This will attempt to connect to the database and run a simple
    health check query, then update the connection status.
    """
    try:
        logger.info(f"Testing connection {connection_id}")

        async with await get_session() as session:
            # Fetch connection with provider relationship
            stmt = (
                select(Connection)
                .options(selectinload(Connection.provider))
                .where(
                    Connection.id == connection_id,
                    Connection.provider_id == provider_id,
                )
            )
            result = await session.execute(stmt)
            connection = result.scalar_one_or_none()

            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Connection {connection_id} not found",
                    ).model_dump(),
                )

            # Verify provider belongs to workspace
            if connection.provider.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Connection not found in workspace {workspace_id}",
                    ).model_dump(),
                )

            # Test the connection using service
            from text2x.services.connection_service import ConnectionService

            test_result = await ConnectionService.test_connection(connection)

            # Update connection status in database
            connection.status = test_result.status
            connection.last_health_check = datetime.utcnow()
            connection.status_message = test_result.message if not test_result.success else None

            await session.commit()

            return ConnectionTestResult(
                success=test_result.success,
                message=test_result.message,
                latency_ms=test_result.latency_ms,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection: {e}", exc_info=True)
        return ConnectionTestResult(
            success=False,
            message=f"Connection test failed: {str(e)}",
            latency_ms=None,
        )


@router.post(
    "/{workspace_id}/providers/{provider_id}/connections/{connection_id}/schema/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh connection schema",
)
async def refresh_connection_schema(
    workspace_id: UUID,
    provider_id: UUID,
    connection_id: UUID,
) -> dict[str, str]:
    """
    Trigger schema refresh for a connection.

    This will re-introspect the database schema and update the cache.
    """
    try:
        logger.info(f"Triggering schema refresh for connection {connection_id}")

        async with await get_session() as session:
            # Fetch connection with provider relationship
            stmt = (
                select(Connection)
                .options(selectinload(Connection.provider))
                .where(
                    Connection.id == connection_id,
                    Connection.provider_id == provider_id,
                )
            )
            result = await session.execute(stmt)
            connection = result.scalar_one_or_none()

            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Connection {connection_id} not found",
                    ).model_dump(),
                )

            # Verify provider belongs to workspace
            if connection.provider.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Connection not found in workspace {workspace_id}",
                    ).model_dump(),
                )

            # Introspect schema using service
            from text2x.services.connection_service import ConnectionService

            introspection_result = await ConnectionService.introspect_schema(connection)

            if introspection_result.success:
                # Update connection with schema cache info
                # In a production system, you'd store the schema in Redis or similar
                # For now, just update the timestamp and store a cache key
                connection.schema_cache_key = f"schema:{connection_id}"
                connection.schema_last_refreshed = datetime.utcnow()

                await session.commit()

                return {
                    "status": "success",
                    "message": f"Schema refreshed successfully: {introspection_result.table_count} tables found",
                    "connection_id": str(connection_id),
                    "table_count": introspection_result.table_count,
                    "introspection_time_ms": introspection_result.introspection_time_ms,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Schema refresh failed: {introspection_result.error}",
                    "connection_id": str(connection_id),
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering schema refresh: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="refresh_error",
                message="Failed to trigger schema refresh",
            ).model_dump(),
        )
