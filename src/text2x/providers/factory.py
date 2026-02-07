"""Provider factory for creating provider instances from database models."""

from typing import TYPE_CHECKING
from uuid import UUID

from text2x.providers.sql_provider import SQLProvider, SQLConnectionConfig
from text2x.providers.nosql_provider import NoSQLProvider, MongoDBConnectionConfig
from text2x.models.workspace import ProviderType

if TYPE_CHECKING:
    from text2x.providers.base import QueryProvider


async def get_provider_instance(provider_model) -> "QueryProvider":
    """Create a QueryProvider instance from a provider database model.

    Args:
        provider_model: Provider model from database with associated connection

    Returns:
        QueryProvider instance ready for queries

    Raises:
        ValueError: If provider type is not supported
    """
    provider_type = provider_model.type

    # Get connection details from the provider's connections (one-to-many)
    connections = provider_model.connections
    if not connections:
        raise ValueError(f"Provider {provider_model.id} has no associated connections")

    # Use the first connection
    connection = connections[0]

    credentials = connection.credentials or {}
    username = credentials.get("username", "")
    password = credentials.get("password", "")

    if provider_type == ProviderType.MONGODB:
        connection_string = (
            f"mongodb://{connection.host}:{connection.port}"
            if connection.host
            else "mongodb://localhost:27017"
        )
        config = MongoDBConnectionConfig(
            connection_string=connection_string,
            database=connection.database,
            username=username,
            password=password,
        )
        return NoSQLProvider(config)
    elif provider_type == ProviderType.POSTGRESQL:
        dialect = "postgresql"
    elif provider_type == ProviderType.MYSQL:
        dialect = "mysql"
    elif provider_type == ProviderType.SQLITE:
        dialect = "sqlite"
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")

    config = SQLConnectionConfig(
        host=connection.host or "localhost",
        port=connection.port or 5432,
        database=connection.database,
        username=username,
        password=password,
        dialect=dialect,
        extra_params=connection.connection_options or {},
    )

    return SQLProvider(config)


async def get_provider_by_connection_id(connection_id: UUID, workspace_id: UUID) -> "QueryProvider":
    """Create a QueryProvider instance from a connection ID.

    Args:
        connection_id: UUID of the connection
        workspace_id: UUID of the workspace (for validation)

    Returns:
        QueryProvider instance ready for queries

    Raises:
        ValueError: If connection not found or provider type not supported
    """
    from text2x.api.state import app_state
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from text2x.models.workspace import Connection, Provider

    # Create session
    session_maker = async_sessionmaker(
        app_state.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        # Get connection with its provider
        result = await session.execute(
            select(Connection)
            .options(selectinload(Connection.provider))
            .where(Connection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise ValueError(f"Connection {connection_id} not found")

        provider = connection.provider
        if not provider:
            raise ValueError(f"No provider found for connection {connection_id}")

        # Verify workspace matches
        if provider.workspace_id != workspace_id:
            raise ValueError(
                f"Connection {connection_id} does not belong to workspace {workspace_id}"
            )

        credentials = connection.credentials or {}
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        provider_type = provider.type
        if provider_type == ProviderType.POSTGRESQL:
            dialect = "postgresql"
        elif provider_type == ProviderType.MYSQL:
            dialect = "mysql"
        elif provider_type == ProviderType.SQLITE:
            dialect = "sqlite"
        elif provider_type == ProviderType.MONGODB:
            connection_string = (
                f"mongodb://{connection.host}:{connection.port}"
                if connection.host
                else "mongodb://localhost:27017"
            )
            config = MongoDBConnectionConfig(
                connection_string=connection_string,
                database=connection.database,
                username=username,
                password=password,
            )
            return NoSQLProvider(config)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        config = SQLConnectionConfig(
            host=connection.host or "localhost",
            port=connection.port or 5432,
            database=connection.database,
            username=username,
            password=password,
            dialect=dialect,
            extra_params=connection.connection_options or {},
        )

        return SQLProvider(config)
