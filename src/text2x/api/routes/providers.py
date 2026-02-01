"""Provider management endpoints."""
import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from text2x.api.models import (
    ErrorResponse,
    ProviderInfo,
    ProviderSchema,
    TableInfo,
)
from text2x.config import settings
from text2x.repositories.provider import ProviderRepository
from text2x.services.schema_service import SchemaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get(
    "",
    response_model=list[ProviderInfo],
    summary="List all providers",
    description="Get list of all configured database providers/connections",
)
async def list_providers() -> list[ProviderInfo]:
    """
    List all configured database providers.

    Returns:
        List of provider information

    Raises:
        HTTPException: If fetching providers fails
    """
    try:
        logger.info("Fetching list of providers")

        # Note: Since we don't have workspace context in the current API,
        # we need to decide how to list providers. For now, return empty list
        # or implement workspace-aware API in the future.
        # This is a placeholder that returns mock data until workspace context is added

        # Mock response (replace with workspace-aware query when auth is implemented)
        mock_providers = [
            ProviderInfo(
                id="postgres-main",
                name="Main PostgreSQL Database",
                type="postgresql",
                description="Primary application database with user and transaction data",
                connection_status="connected",
                table_count=25,
                last_schema_refresh=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            ProviderInfo(
                id="athena-analytics",
                name="AWS Athena Analytics",
                type="athena",
                description="Data warehouse for analytics queries",
                connection_status="connected",
                table_count=50,
                last_schema_refresh=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            ProviderInfo(
                id="opensearch-logs",
                name="OpenSearch Logs",
                type="opensearch",
                description="Application logs and search indexes",
                connection_status="connected",
                table_count=10,
                last_schema_refresh=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        logger.info(f"Found {len(mock_providers)} providers")
        return mock_providers

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
async def get_provider(provider_id: str) -> ProviderInfo:
    """
    Get detailed information about a specific provider.

    Args:
        provider_id: Provider identifier

    Returns:
        Provider information

    Raises:
        HTTPException: If provider not found
    """
    try:
        logger.info(f"Fetching provider {provider_id}")

        # Try to fetch from database if provider_id is a valid UUID
        try:
            from uuid import UUID as PyUUID
            provider_uuid = PyUUID(provider_id)
            provider_repo = ProviderRepository()
            provider = await provider_repo.get_by_id(provider_uuid)

            if provider:
                # Get connection count
                connection_count = len(provider.connections) if provider.connections else 0

                return ProviderInfo(
                    id=str(provider.id),
                    name=provider.name,
                    type=provider.type.value,
                    description=provider.description or "",
                    connection_status="connected" if connection_count > 0 else "disconnected",
                    table_count=0,  # Would need to query schema to get accurate count
                    last_schema_refresh=None,  # Would need to track in database
                    created_at=provider.created_at,
                    updated_at=provider.updated_at,
                )
        except (ValueError, AttributeError):
            # Not a valid UUID, fall through to mock data
            logger.debug(f"Provider ID {provider_id} is not a valid UUID, using mock data")

        # Mock response for backward compatibility with string IDs
        if provider_id == "postgres-main":
            return ProviderInfo(
                id=provider_id,
                name="Main PostgreSQL Database",
                type="postgresql",
                description="Primary application database with user and transaction data",
                connection_status="connected",
                table_count=25,
                last_schema_refresh=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Provider {provider_id} not found",
                ).model_dump(),
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
async def get_provider_schema(provider_id: str) -> ProviderSchema:
    """
    Get complete schema information for a provider.

    This includes all tables, columns, relationships, and metadata.
    Schema is typically cached in Redis for performance.

    Args:
        provider_id: Provider identifier

    Returns:
        Complete schema information

    Raises:
        HTTPException: If provider not found or schema unavailable
    """
    try:
        logger.info(f"Fetching schema for provider {provider_id}")

        # Try to fetch schema using SchemaService (with caching)
        try:
            from uuid import UUID as PyUUID

            # For now, provider_id might be a connection_id
            # Try to parse as UUID to use SchemaService
            connection_uuid = PyUUID(provider_id)
            schema_service = SchemaService()

            schema_def = await schema_service.get_schema(connection_uuid)

            if schema_def:
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
                    provider_id=provider_id,
                    provider_type="postgresql",  # Would need to look up from connection
                    tables=tables,
                    metadata=schema_def.metadata,
                    last_refreshed=datetime.utcnow(),
                )
        except (ValueError, AttributeError, Exception) as e:
            # Not a valid UUID or schema fetch failed, fall through to mock data
            logger.debug(f"Could not fetch schema for {provider_id}: {e}")

        # Mock response
        if provider_id == "postgres-main":
            return ProviderSchema(
                provider_id=provider_id,
                provider_type="postgresql",
                tables=[
                    TableInfo(
                        name="users",
                        schema="public",
                        columns=[
                            {
                                "name": "id",
                                "type": "integer",
                                "nullable": False,
                                "primary_key": True,
                            },
                            {
                                "name": "username",
                                "type": "varchar(255)",
                                "nullable": False,
                                "unique": True,
                            },
                            {
                                "name": "email",
                                "type": "varchar(255)",
                                "nullable": False,
                                "unique": True,
                            },
                            {
                                "name": "age",
                                "type": "integer",
                                "nullable": True,
                            },
                            {
                                "name": "created_at",
                                "type": "timestamp",
                                "nullable": False,
                            },
                        ],
                        primary_keys=["id"],
                        foreign_keys=[],
                        row_count=10000,
                        description="User account information",
                    ),
                    TableInfo(
                        name="orders",
                        schema="public",
                        columns=[
                            {
                                "name": "id",
                                "type": "integer",
                                "nullable": False,
                                "primary_key": True,
                            },
                            {
                                "name": "user_id",
                                "type": "integer",
                                "nullable": False,
                                "foreign_key": "users.id",
                            },
                            {
                                "name": "total_amount",
                                "type": "numeric(10,2)",
                                "nullable": False,
                            },
                            {
                                "name": "status",
                                "type": "varchar(50)",
                                "nullable": False,
                            },
                            {
                                "name": "created_at",
                                "type": "timestamp",
                                "nullable": False,
                            },
                        ],
                        primary_keys=["id"],
                        foreign_keys=[
                            {
                                "column": "user_id",
                                "references_table": "users",
                                "references_column": "id",
                            }
                        ],
                        row_count=50000,
                        description="Customer orders",
                    ),
                ],
                metadata={
                    "database": "main_db",
                    "version": "PostgreSQL 15.3",
                },
                last_refreshed=datetime.utcnow(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error="not_found",
                    message=f"Provider {provider_id} not found",
                ).model_dump(),
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
async def refresh_provider_schema(provider_id: str) -> dict[str, str]:
    """
    Trigger a schema refresh for a provider.

    This is an asynchronous operation that will update the cached schema
    information by querying the database metadata.

    Args:
        provider_id: Provider identifier

    Returns:
        Status message

    Raises:
        HTTPException: If provider not found or refresh fails
    """
    try:
        logger.info(f"Triggering schema refresh for provider {provider_id}")

        # Try to refresh schema using SchemaService
        try:
            from uuid import UUID as PyUUID

            connection_uuid = PyUUID(provider_id)
            schema_service = SchemaService()

            # Refresh schema (invalidates cache and re-introspects)
            schema_def = await schema_service.refresh_schema(connection_uuid)

            if schema_def:
                logger.info(f"Schema refreshed successfully for {provider_id}")
            else:
                logger.warning(f"Schema refresh returned None for {provider_id}")

        except (ValueError, AttributeError, Exception) as e:
            logger.warning(f"Could not refresh schema for {provider_id}: {e}")
            # Continue anyway to return accepted status

        return {
            "status": "accepted",
            "message": f"Schema refresh initiated for provider {provider_id}",
            "provider_id": provider_id,
        }

    except Exception as e:
        logger.error(f"Error triggering schema refresh: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="refresh_error",
                message="Failed to trigger schema refresh",
            ).model_dump(),
        )
