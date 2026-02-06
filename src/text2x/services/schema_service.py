"""Schema Service for caching and retrieving database schemas.

This service handles schema introspection and caching for database connections.
It supports:
- Getting schema from cache or introspecting from database
- Caching schemas in Redis with TTL
- Converting between database models and provider abstractions
"""

import json
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

import redis.asyncio as redis
from redis.asyncio import Redis

from text2x.config import settings
from text2x.models.workspace import Connection, ProviderType
from text2x.providers.base import SchemaDefinition, TableInfo, ColumnInfo, ForeignKeyInfo
from text2x.providers.sql_provider import SQLProvider, SQLConnectionConfig
from text2x.repositories.connection import ConnectionRepository
from text2x.repositories.provider import ProviderRepository

logger = logging.getLogger(__name__)


class SchemaService:
    """
    Service for managing database schema caching and retrieval.

    This service:
    - Retrieves schemas from cache (Redis) when available
    - Falls back to database introspection when cache misses
    - Caches schemas with configurable TTL
    - Manages schema refresh operations
    """

    def __init__(
        self,
        connection_repo: Optional[ConnectionRepository] = None,
        provider_repo: Optional[ProviderRepository] = None,
        redis_client: Optional[Redis] = None,
    ):
        """
        Initialize schema service.

        Args:
            connection_repo: Repository for connection operations
            provider_repo: Repository for provider operations
            redis_client: Redis client for caching (optional)
        """
        self.connection_repo = connection_repo or ConnectionRepository()
        self.provider_repo = provider_repo or ProviderRepository()
        self._redis_client = redis_client
        self.cache_ttl = settings.redis_schema_cache_ttl

    async def _get_redis_client(self) -> Redis:
        """Get or create Redis client."""
        if self._redis_client is None:
            self._redis_client = await redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis_client

    def _make_cache_key(self, connection_id: UUID) -> str:
        """Generate Redis cache key for a connection's schema."""
        return f"schema:{connection_id}"

    async def get_schema(self, connection_id: UUID) -> Optional[SchemaDefinition]:
        """
        Get schema for a connection.

        Checks cache first, then introspects database if needed.

        Args:
            connection_id: UUID of the connection

        Returns:
            SchemaDefinition if found, None if connection doesn't exist

        Raises:
            Exception: If schema introspection fails
        """
        # Get connection from database
        connection = await self.connection_repo.get_by_id(connection_id)
        if not connection:
            logger.warning(f"Connection {connection_id} not found")
            return None

        # Try to get from cache first
        cache_key = self._make_cache_key(connection_id)
        try:
            redis_client = await self._get_redis_client()
            cached_schema = await redis_client.get(cache_key)

            if cached_schema:
                logger.info(f"Schema cache HIT for connection {connection_id}")
                schema_dict = json.loads(cached_schema)
                return self._deserialize_schema(schema_dict)
        except Exception as e:
            logger.warning(f"Failed to get schema from cache: {e}")
            # Continue to introspection on cache failure

        # Cache miss - introspect from database
        logger.info(f"Schema cache MISS for connection {connection_id}, introspecting...")
        schema = await self._introspect_schema(connection)

        if schema:
            # Cache the result
            await self.cache_schema(connection_id, schema)

        return schema

    async def cache_schema(self, connection_id: UUID, schema: SchemaDefinition) -> str:
        """
        Cache schema in Redis.

        Args:
            connection_id: UUID of the connection
            schema: SchemaDefinition to cache

        Returns:
            Cache key used for storage

        Raises:
            Exception: If caching fails
        """
        cache_key = self._make_cache_key(connection_id)

        try:
            # Serialize schema to JSON
            schema_dict = self._serialize_schema(schema)
            schema_json = json.dumps(schema_dict)

            # Store in Redis with TTL
            redis_client = await self._get_redis_client()
            await redis_client.setex(cache_key, self.cache_ttl, schema_json)

            # Update connection's schema_cache_key and refresh time
            await self.connection_repo.update_schema_refresh_time(
                connection_id=connection_id, schema_cache_key=cache_key
            )

            logger.info(f"Cached schema for connection {connection_id} with TTL {self.cache_ttl}s")

            return cache_key

        except Exception as e:
            logger.error(f"Failed to cache schema: {e}", exc_info=True)
            raise

    async def invalidate_cache(self, connection_id: UUID) -> bool:
        """
        Invalidate cached schema for a connection.

        Args:
            connection_id: UUID of the connection

        Returns:
            True if cache was invalidated, False otherwise
        """
        cache_key = self._make_cache_key(connection_id)

        try:
            redis_client = await self._get_redis_client()
            result = await redis_client.delete(cache_key)

            if result > 0:
                logger.info(f"Invalidated schema cache for connection {connection_id}")
                return True
            else:
                logger.info(f"No cache to invalidate for connection {connection_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}", exc_info=True)
            return False

    async def refresh_schema(self, connection_id: UUID) -> Optional[SchemaDefinition]:
        """
        Refresh schema by invalidating cache and re-introspecting.

        Args:
            connection_id: UUID of the connection

        Returns:
            SchemaDefinition if successful, None otherwise
        """
        # Invalidate cache
        await self.invalidate_cache(connection_id)

        # Re-introspect
        return await self.get_schema(connection_id)

    async def _introspect_schema(self, connection: Connection) -> Optional[SchemaDefinition]:
        """
        Introspect schema from database.

        Args:
            connection: Connection object with database credentials

        Returns:
            SchemaDefinition from database introspection

        Raises:
            NotImplementedError: If provider type not supported
            Exception: If introspection fails
        """
        # Get provider to determine type
        provider = await self.provider_repo.get_by_id(connection.provider_id)
        if not provider:
            logger.error(f"Provider {connection.provider_id} not found")
            return None

        try:
            # Create provider based on type
            if provider.type in [
                ProviderType.POSTGRESQL,
                ProviderType.MYSQL,
                ProviderType.REDSHIFT,
            ]:
                query_provider = await self._create_sql_provider(connection, provider.type)
                schema = await query_provider.get_schema()
            elif provider.type == ProviderType.MONGODB:
                schema = await self._introspect_mongodb(connection)
            else:
                raise NotImplementedError(
                    f"Schema introspection not implemented for {provider.type}"
                )

            logger.info(
                f"Introspected schema for connection {connection.id}: "
                f"{len(schema.tables) if schema.tables else len(schema.collections or [])} tables/collections"
            )

            return schema

        except Exception as e:
            logger.error(
                f"Failed to introspect schema for connection {connection.id}: {e}", exc_info=True
            )
            raise

    async def _create_sql_provider(
        self, connection: Connection, provider_type: ProviderType
    ) -> SQLProvider:
        """
        Create SQL provider from connection.

        Args:
            connection: Connection object
            provider_type: Type of SQL provider

        Returns:
            Configured SQLProvider instance
        """
        # Map provider type to dialect
        dialect_map = {
            ProviderType.POSTGRESQL: "postgresql",
            ProviderType.MYSQL: "mysql",
            ProviderType.REDSHIFT: "postgresql",  # Redshift uses PostgreSQL dialect
        }

        dialect = dialect_map.get(provider_type, "postgresql")

        # Extract credentials
        credentials = connection.credentials or {}
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        # Create connection config
        sql_config = SQLConnectionConfig(
            host=connection.host,
            port=connection.port or 5432,
            database=connection.database,
            username=username,
            password=password,
            dialect=dialect,
            extra_params=connection.connection_options or {},
        )

        return SQLProvider(sql_config)

    async def _introspect_mongodb(self, connection: Connection) -> SchemaDefinition:
        """
        Introspect MongoDB database schema by listing collections and sampling documents.

        Args:
            connection: Connection object with database credentials

        Returns:
            SchemaDefinition with collections and sampled field info
        """
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure
        except ImportError:
            raise NotImplementedError("MongoDB client (pymongo) not installed")

        credentials = connection.credentials or {}
        username = credentials.get("username")
        password = credentials.get("password")

        if username and password:
            conn_str = (
                f"mongodb://{username}:{password}@{connection.host}:{connection.port or 27017}/"
            )
        else:
            conn_str = f"mongodb://{connection.host}:{connection.port or 27017}/"

        try:
            client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
        except ConnectionFailure as e:
            raise Exception(f"Failed to connect to MongoDB: {e}")

        try:
            db = client[connection.database]
            collection_names = db.list_collection_names()

            logger.info(
                f"Found {len(collection_names)} collections in MongoDB database '{connection.database}'"
            )

            collections_with_schema = []
            for coll_name in collection_names:
                collection = db[coll_name]
                sample_docs = list(collection.find().limit(10))

                fields = []
                seen_fields = set()
                for doc in sample_docs:
                    for key in doc.keys():
                        if key not in seen_fields:
                            seen_fields.add(key)
                            val = doc[key]
                            field_type = type(val).__name__
                            if field_type == "ObjectId":
                                field_type = "objectid"
                            elif field_type == "datetime":
                                field_type = "datetime"
                            elif field_type == "list":
                                field_type = "array"
                            elif field_type == "dict":
                                field_type = "object"
                            fields.append({"name": key, "type": field_type})

                collections_with_schema.append(
                    {
                        "name": coll_name,
                        "columns": fields,
                        "document_count": collection.count_documents({}),
                    }
                )

            schema = SchemaDefinition(
                tables=[],
                collections=collections_with_schema,
                metadata={
                    "database": connection.database,
                    "collection_count": len(collection_names),
                },
            )

            client.close()
            return schema

        except Exception as e:
            client.close()
            raise

    def _serialize_schema(self, schema: SchemaDefinition) -> dict:
        """
        Serialize SchemaDefinition to dict for JSON storage.

        Args:
            schema: SchemaDefinition to serialize

        Returns:
            Dictionary representation of schema
        """
        return {
            "tables": [
                {
                    "name": table.name,
                    "schema": table.schema,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.type,
                            "nullable": col.nullable,
                            "default": col.default,
                            "primary_key": col.primary_key,
                            "unique": col.unique,
                            "comment": col.comment,
                            "autoincrement": col.autoincrement,
                        }
                        for col in table.columns
                    ],
                    "indexes": [
                        {
                            "name": idx.name,
                            "columns": idx.columns,
                            "unique": idx.unique,
                            "type": idx.type,
                        }
                        for idx in table.indexes
                    ],
                    "foreign_keys": [
                        {
                            "name": fk.name,
                            "constrained_columns": fk.constrained_columns,
                            "referred_schema": fk.referred_schema,
                            "referred_table": fk.referred_table,
                            "referred_columns": fk.referred_columns,
                            "on_delete": fk.on_delete,
                            "on_update": fk.on_update,
                        }
                        for fk in table.foreign_keys
                    ],
                    "primary_key": table.primary_key,
                    "comment": table.comment,
                    "row_count": table.row_count,
                }
                for table in schema.tables
            ],
            "relationships": [
                {
                    "from_table": rel.from_table,
                    "to_table": rel.to_table,
                    "from_columns": rel.from_columns,
                    "to_columns": rel.to_columns,
                    "relationship_type": rel.relationship_type,
                }
                for rel in schema.relationships
            ],
            "collections": schema.collections,
            "metadata": schema.metadata,
        }

    def _deserialize_schema(self, schema_dict: dict) -> SchemaDefinition:
        """
        Deserialize dict to SchemaDefinition.

        Args:
            schema_dict: Dictionary from JSON

        Returns:
            SchemaDefinition object
        """
        from text2x.providers.base import Relationship

        tables = [
            TableInfo(
                name=table_dict["name"],
                schema=table_dict.get("schema"),
                columns=[ColumnInfo(**col_dict) for col_dict in table_dict.get("columns", [])],
                indexes=[
                    {
                        "name": idx["name"],
                        "columns": idx["columns"],
                        "unique": idx.get("unique", False),
                        "type": idx.get("type"),
                    }
                    for idx in table_dict.get("indexes", [])
                ],
                foreign_keys=[
                    ForeignKeyInfo(**fk_dict) for fk_dict in table_dict.get("foreign_keys", [])
                ],
                primary_key=table_dict.get("primary_key"),
                comment=table_dict.get("comment"),
                row_count=table_dict.get("row_count"),
            )
            for table_dict in schema_dict.get("tables", [])
        ]

        relationships = [
            Relationship(**rel_dict) for rel_dict in schema_dict.get("relationships", [])
        ]

        collections_raw = schema_dict.get("collections", [])
        collections = []
        for coll in collections_raw:
            if isinstance(coll, dict):
                collections.append(coll)
            else:
                collections.append({"name": coll, "columns": [], "document_count": 0})

        return SchemaDefinition(
            tables=tables,
            relationships=relationships,
            collections=collections,
            metadata=schema_dict.get("metadata", {}),
        )

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
