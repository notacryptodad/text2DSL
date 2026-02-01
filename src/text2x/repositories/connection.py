"""
Repository for Connection model CRUD operations.

This module provides async database operations for managing connections
to various database providers.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update as sql_update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.base import get_db
from text2x.models.workspace import Connection, ConnectionStatus, Provider


class ConnectionRepository:
    """
    Repository for managing Connection entities.

    Provides async CRUD operations for database connections including
    creation, retrieval, updates, and status management.
    """

    async def create(
        self,
        provider_id: UUID,
        name: str,
        host: str,
        database: str,
        port: Optional[int] = None,
        schema_name: Optional[str] = None,
        credentials: Optional[dict] = None,
        connection_options: Optional[dict] = None,
        status: ConnectionStatus = ConnectionStatus.PENDING,
    ) -> Optional[Connection]:
        """
        Create a new connection.

        Args:
            provider_id: UUID of the parent provider
            name: Human-readable connection name
            host: Database host/endpoint
            database: Database/catalog name
            port: Database port (optional)
            schema_name: Schema/namespace within the database (optional)
            credentials: Encrypted credentials blob (optional)
            connection_options: Additional connection parameters (optional)
            status: Initial connection status (default: PENDING)

        Returns:
            The created Connection object, or None if provider_id is invalid
        """
        db = get_db()

        async with db.session() as session:
            # Validate that provider exists
            provider_exists = await self._provider_exists(session, provider_id)
            if not provider_exists:
                return None

            # Create the connection
            connection = Connection(
                provider_id=provider_id,
                name=name,
                host=host,
                port=port,
                database=database,
                schema_name=schema_name,
                credentials=credentials or {},
                connection_options=connection_options or {},
                status=status,
            )

            session.add(connection)
            await session.flush()
            await session.refresh(connection)

            return connection

    async def get_by_id(self, connection_id: UUID) -> Optional[Connection]:
        """
        Retrieve a connection by its ID.

        Args:
            connection_id: UUID of the connection to retrieve

        Returns:
            The Connection object if found, None otherwise
        """
        db = get_db()

        async with db.session() as session:
            result = await session.execute(
                select(Connection).where(Connection.id == connection_id)
            )
            return result.scalar_one_or_none()

    async def list_by_provider(self, provider_id: UUID) -> List[Connection]:
        """
        List all connections for a specific provider.

        Args:
            provider_id: UUID of the provider

        Returns:
            List of Connection objects (empty list if none found)
        """
        db = get_db()

        async with db.session() as session:
            result = await session.execute(
                select(Connection)
                .where(Connection.provider_id == provider_id)
                .order_by(Connection.created_at)
            )
            return list(result.scalars().all())

    async def update(
        self,
        connection_id: UUID,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        schema_name: Optional[str] = None,
        credentials: Optional[dict] = None,
        connection_options: Optional[dict] = None,
        status: Optional[ConnectionStatus] = None,
    ) -> Optional[Connection]:
        """
        Update an existing connection.

        Only provided fields will be updated. None values are ignored.

        Args:
            connection_id: UUID of the connection to update
            name: New connection name (optional)
            host: New database host (optional)
            port: New database port (optional)
            database: New database name (optional)
            schema_name: New schema name (optional)
            credentials: New credentials (optional)
            connection_options: New connection options (optional)
            status: New connection status (optional)

        Returns:
            The updated Connection object if found, None otherwise
        """
        db = get_db()

        async with db.session() as session:
            # First check if connection exists
            connection = await session.get(Connection, connection_id)
            if connection is None:
                return None

            # Update only provided fields
            if name is not None:
                connection.name = name
            if host is not None:
                connection.host = host
            if port is not None:
                connection.port = port
            if database is not None:
                connection.database = database
            if schema_name is not None:
                connection.schema_name = schema_name
            if credentials is not None:
                connection.credentials = credentials
            if connection_options is not None:
                connection.connection_options = connection_options
            if status is not None:
                connection.status = status

            await session.flush()
            await session.refresh(connection)

            return connection

    async def delete(self, connection_id: UUID) -> bool:
        """
        Delete a connection.

        Args:
            connection_id: UUID of the connection to delete

        Returns:
            True if the connection was deleted, False if not found
        """
        db = get_db()

        async with db.session() as session:
            result = await session.execute(
                sql_delete(Connection).where(Connection.id == connection_id)
            )
            return result.rowcount > 0

    async def update_status(
        self,
        connection_id: UUID,
        status: ConnectionStatus,
        status_message: Optional[str] = None,
    ) -> Optional[Connection]:
        """
        Update the connection status and health check timestamp.

        Args:
            connection_id: UUID of the connection to update
            status: New connection status
            status_message: Optional status message (error details, etc.)

        Returns:
            The updated Connection object if found, None otherwise
        """
        db = get_db()

        async with db.session() as session:
            connection = await session.get(Connection, connection_id)
            if connection is None:
                return None

            connection.status = status
            connection.status_message = status_message
            connection.last_health_check = datetime.utcnow()

            await session.flush()
            await session.refresh(connection)

            return connection

    async def update_schema_refresh_time(
        self,
        connection_id: UUID,
        schema_cache_key: Optional[str] = None,
    ) -> Optional[Connection]:
        """
        Update the schema refresh timestamp and cache key.

        Args:
            connection_id: UUID of the connection to update
            schema_cache_key: Optional Redis key for cached schema

        Returns:
            The updated Connection object if found, None otherwise
        """
        db = get_db()

        async with db.session() as session:
            connection = await session.get(Connection, connection_id)
            if connection is None:
                return None

            connection.schema_last_refreshed = datetime.utcnow()
            if schema_cache_key is not None:
                connection.schema_cache_key = schema_cache_key

            await session.flush()
            await session.refresh(connection)

            return connection

    async def _provider_exists(self, session: AsyncSession, provider_id: UUID) -> bool:
        """
        Check if a provider exists.

        Args:
            session: Active database session
            provider_id: UUID of the provider to check

        Returns:
            True if the provider exists, False otherwise
        """
        result = await session.execute(
            select(Provider.id).where(Provider.id == provider_id)
        )
        return result.scalar_one_or_none() is not None
