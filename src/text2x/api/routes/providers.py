"""Provider management endpoints."""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from text2x.api.models import (
    ErrorResponse,
    ProviderInfo,
    ProviderSchema,
    TableInfo,
)
from text2x.api.state import app_state
from text2x.models.workspace import Provider, Connection
from text2x.services.schema_service import SchemaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


async def get_session() -> AsyncSession:
    """Get database session from app state."""
    session_maker = async_sessionmaker(
        app_state.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session_maker()


@router.get(
    "",
    response_model=list[ProviderInfo],
    summary="List all providers",
    description="Get list of all configured database providers/connections",
)
async def list_providers(
    workspace_id: Optional[UUID] = Query(None, description="Filter by workspace ID")
) -> list[ProviderInfo]:
    """
    List all configured database providers.

    Args:
        workspace_id: Optional workspace ID to filter providers

    Returns:
        List of provider information

    Raises:
        HTTPException: If fetching providers fails
    """
    try:
        logger.info(f"Fetching list of providers for workspace: {workspace_id}")

        async with await get_session() as session:
            # Build query for providers with connection count
            query = select(
                Provider,
                func.count(Connection.id).label("connection_count")
            ).outerjoin(Connection).group_by(Provider.id)

            # Filter by workspace if provided
            if workspace_id:
                query = query.where(Provider.workspace_id == workspace_id)

            result = await session.execute(query)
            rows = result.all()

            # Build response models
            providers = []
            for provider, connection_count in rows:
                # Determine connection status based on connections
                connection_status = "connected" if connection_count > 0 else "disconnected"

                providers.append(
                    ProviderInfo(
                        id=str(provider.id),
                        name=provider.name,
                        type=provider.type.value,
                        description=provider.description or "",
                        connection_status=connection_status,
                        table_count=0,  # Would require schema introspection
                        last_schema_refresh=None,  # Would need to track in database
                        created_at=provider.created_at,
                        updated_at=provider.updated_at,
                    )
                )

            logger.info(f"Found {len(providers)} providers")
            return providers

    except Exception as e:
        logger.error(f"Error fetching providers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch providers",
            ).model_dump(),
        )


@router.get(
    "/{provider_id}",
    response_model=ProviderInfo,
    summary="Get provider details",
)
async def get_provider(provider_id: UUID) -> ProviderInfo:
    """
    Get detailed information about a specific provider.

    Args:
        provider_id: Provider UUID

    Returns:
        Provider information

    Raises:
        HTTPException: If provider not found
    """
    try:
        logger.info(f"Fetching provider {provider_id}")

        async with await get_session() as session:
            # Query provider with connection count
            query = select(
                Provider,
                func.count(Connection.id).label("connection_count")
            ).outerjoin(Connection).where(Provider.id == provider_id).group_by(Provider.id)

            result = await session.execute(query)
            row = result.one_or_none()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found",
                    ).model_dump(),
                )

            provider, connection_count = row

            # Determine connection status
            connection_status = "connected" if connection_count > 0 else "disconnected"

            return ProviderInfo(
                id=str(provider.id),
                name=provider.name,
                type=provider.type.value,
                description=provider.description or "",
                connection_status=connection_status,
                table_count=0,  # Would require schema introspection
                last_schema_refresh=None,  # Would need to track in database
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


@router.get(
    "/{provider_id}/schema",
    response_model=ProviderSchema,
    summary="Get provider schema",
    description="Retrieve complete schema information for a provider including all tables and columns",
)
async def get_provider_schema(
    provider_id: UUID,
    connection_id: Optional[UUID] = Query(None, description="Specific connection ID to introspect")
) -> ProviderSchema:
    """
    Get complete schema information for a provider.

    This includes all tables, columns, relationships, and metadata.
    Schema is typically cached in Redis for performance.

    Args:
        provider_id: Provider UUID
        connection_id: Optional connection UUID to use for schema introspection.
                      If not provided, uses the first active connection.

    Returns:
        Complete schema information

    Raises:
        HTTPException: If provider not found or schema unavailable
    """
    try:
        logger.info(f"Fetching schema for provider {provider_id}, connection {connection_id}")

        async with await get_session() as session:
            # Verify provider exists
            provider_stmt = select(Provider).where(Provider.id == provider_id)
            provider_result = await session.execute(provider_stmt)
            provider = provider_result.scalar_one_or_none()

            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found",
                    ).model_dump(),
                )

            # Find a connection to use for schema introspection
            if connection_id:
                # Use specified connection
                conn_stmt = select(Connection).where(
                    Connection.id == connection_id,
                    Connection.provider_id == provider_id
                )
                conn_result = await session.execute(conn_stmt)
                connection = conn_result.scalar_one_or_none()

                if not connection:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ErrorResponse(
                            error="not_found",
                            message=f"Connection {connection_id} not found for provider {provider_id}",
                        ).model_dump(),
                    )
            else:
                # Use first available connection for this provider
                conn_stmt = select(Connection).where(Connection.provider_id == provider_id).limit(1)
                conn_result = await session.execute(conn_stmt)
                connection = conn_result.scalar_one_or_none()

                if not connection:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ErrorResponse(
                            error="not_found",
                            message=f"No connections found for provider {provider_id}",
                        ).model_dump(),
                    )

            # Fetch schema using SchemaService
            schema_service = SchemaService()
            schema_def = await schema_service.get_schema(connection.id)

            if not schema_def:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="schema_unavailable",
                        message=f"Schema not available for provider {provider_id}. Try refreshing the schema first.",
                    ).model_dump(),
                )

            # Convert SchemaDefinition to ProviderSchema API model
            tables = [
                TableInfo(
                    name=table.name,
                    schema=table.schema,
                    columns=[
                        {
                            "name": col.name,
                            "type": col.type,
                            "nullable": col.nullable,
                            "primary_key": col.primary_key,
                            "unique": col.unique,
                            "comment": col.comment,
                        }
                        for col in table.columns
                    ],
                    primary_keys=table.primary_key or [],
                    foreign_keys=[
                        {
                            "column": fk.constrained_columns[0] if fk.constrained_columns else "",
                            "references_table": fk.referred_table,
                            "references_column": fk.referred_columns[0] if fk.referred_columns else "",
                        }
                        for fk in table.foreign_keys
                    ],
                    row_count=table.row_count,
                    description=table.comment or "",
                )
                for table in schema_def.tables
            ]

            return ProviderSchema(
                provider_id=str(provider_id),
                provider_type=provider.type.value,
                tables=tables,
                metadata=schema_def.metadata,
                last_refreshed=datetime.utcnow(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="fetch_error",
                message="Failed to fetch provider schema",
            ).model_dump(),
        )


@router.post(
    "/{provider_id}/schema/refresh",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Refresh provider schema",
    description="Trigger schema refresh for a provider (async operation)",
)
async def refresh_provider_schema(
    provider_id: UUID,
    connection_id: Optional[UUID] = Query(None, description="Specific connection ID to refresh")
) -> dict[str, str]:
    """
    Trigger a schema refresh for a provider.

    This is an asynchronous operation that will update the cached schema
    information by querying the database metadata.

    Args:
        provider_id: Provider UUID
        connection_id: Optional connection UUID to refresh.
                      If not provided, refreshes all connections for the provider.

    Returns:
        Status message

    Raises:
        HTTPException: If provider not found or refresh fails
    """
    try:
        logger.info(f"Triggering schema refresh for provider {provider_id}, connection {connection_id}")

        async with await get_session() as session:
            # Verify provider exists
            provider_stmt = select(Provider).where(Provider.id == provider_id)
            provider_result = await session.execute(provider_stmt)
            provider = provider_result.scalar_one_or_none()

            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error="not_found",
                        message=f"Provider {provider_id} not found",
                    ).model_dump(),
                )

            # Get connections to refresh
            if connection_id:
                # Refresh specific connection
                conn_stmt = select(Connection).where(
                    Connection.id == connection_id,
                    Connection.provider_id == provider_id
                )
                conn_result = await session.execute(conn_stmt)
                connections = [conn_result.scalar_one_or_none()]

                if not connections[0]:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ErrorResponse(
                            error="not_found",
                            message=f"Connection {connection_id} not found for provider {provider_id}",
                        ).model_dump(),
                    )
            else:
                # Refresh all connections for provider
                conn_stmt = select(Connection).where(Connection.provider_id == provider_id)
                conn_result = await session.execute(conn_stmt)
                connections = list(conn_result.scalars().all())

                if not connections:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ErrorResponse(
                            error="not_found",
                            message=f"No connections found for provider {provider_id}",
                        ).model_dump(),
                    )

            # Refresh schema for each connection
            schema_service = SchemaService()
            refreshed_count = 0

            for connection in connections:
                try:
                    schema_def = await schema_service.refresh_schema(connection.id)
                    if schema_def:
                        refreshed_count += 1
                        logger.info(f"Schema refreshed successfully for connection {connection.id}")
                    else:
                        logger.warning(f"Schema refresh returned None for connection {connection.id}")
                except Exception as e:
                    logger.warning(f"Could not refresh schema for connection {connection.id}: {e}")

            return {
                "status": "accepted",
                "message": f"Schema refresh completed for {refreshed_count} connection(s)",
                "provider_id": str(provider_id),
                "connections_refreshed": refreshed_count,
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
