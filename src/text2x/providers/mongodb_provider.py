"""MongoDB Provider Implementation for Text2X"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from .base import (
    QueryProvider,
    ProviderCapability,
    SchemaDefinition,
    ValidationResult,
    ExecutionResult,
    TableInfo,
    ColumnInfo,
    ProviderConfig,
)


@dataclass
class MongoDBConnectionConfig:
    """Configuration for MongoDB connection"""

    host: str = "localhost"
    port: int = 27017
    database: str = "text2x"
    username: str = ""
    password: str = ""
    auth_source: str = "admin"
    connect_timeout: int = 10000
    server_selection_timeout: int = 5000


class MongoDBProvider(QueryProvider):
    """MongoDB Provider for MongoDB databases"""

    def __init__(
        self, config: MongoDBConnectionConfig, provider_config: Optional[ProviderConfig] = None
    ):
        """
        Initialize MongoDB Provider

        Args:
            config: MongoDB connection configuration
            provider_config: General provider configuration
        """
        self.config = config
        self.provider_config = provider_config or ProviderConfig(provider_type="mongodb")

        connection_string = self._build_connection_string()
        self.client = MongoClient(
            connection_string,
            connectTimeoutMS=self.config.connect_timeout,
            serverSelectionTimeoutMS=self.config.server_selection_timeout,
        )
        self._db = None

    def _build_connection_string(self) -> str:
        """Build MongoDB connection string"""
        if self.config.username and self.config.password:
            return f"mongodb://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?authSource={self.config.auth_source}"
        return f"mongodb://{self.config.host}:{self.config.port}/{self.config.database}"

    @property
    def db(self):
        """Lazy load database"""
        if self._db is None:
            self._db = self.client[self.config.database]
        return self._db

    def get_provider_id(self) -> str:
        """Unique identifier for this provider"""
        return f"mongodb_{self.config.host}_{self.config.port}"

    def get_query_language(self) -> str:
        """Query language supported by this provider"""
        return "MongoDB"

    def get_capabilities(self) -> List[ProviderCapability]:
        """List of capabilities this provider supports"""
        return [
            ProviderCapability.SCHEMA_INTROSPECTION,
            ProviderCapability.QUERY_VALIDATION,
            ProviderCapability.QUERY_EXECUTION,
        ]

    async def get_schema(self) -> SchemaDefinition:
        """
        Retrieve the complete database schema (collections)

        Returns:
            SchemaDefinition with collections and columns
        """
        return await asyncio.to_thread(self._get_schema_sync)

    def _get_schema_sync(self) -> SchemaDefinition:
        """Synchronous schema introspection"""
        collections = self.db.list_collection_names()
        tables = []

        for collection_name in collections:
            collection = self.db[collection_name]
            columns = []
            row_count = collection.count_documents({})

            # Sample multiple documents to build complete schema
            sample_docs = collection.find({}).limit(100).to_list(length=100)

            # Collect all unique fields from all sampled documents
            all_fields = set()
            field_types = {}

            for doc in sample_docs:
                for key, value in doc.items():
                    if key not in all_fields:
                        all_fields.add(key)
                        field_types[key] = self._infer_type(value)
                    else:
                        # If field exists with different type, mark as mixed
                        current_type = field_types.get(key)
                        new_type = self._infer_type(value)
                        if current_type != new_type:
                            field_types[key] = "mixed"

            # Create column info for each field
            for field_name in sorted(all_fields):
                col_info = ColumnInfo(
                    name=field_name,
                    type=field_types.get(field_name, "unknown"),
                    nullable=True,
                )
                columns.append(col_info)

            table_info = TableInfo(
                name=collection_name,
                columns=columns,
                row_count=row_count,
            )
            tables.append(table_info)

        return SchemaDefinition(
            tables=tables,
            relationships=[],
            metadata={
                "database": self.config.database,
                "collection_count": len(tables),
            },
        )

    def _infer_type(self, value: Any) -> str:
        """Infer MongoDB type from Python value"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "str"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif hasattr(value, "_id"):
            return "objectid"
        else:
            return "unknown"

    async def validate_syntax(self, query: str) -> ValidationResult:
        """
        Validate MongoDB query syntax

        Args:
            query: MongoDB query to validate

        Returns:
            ValidationResult with validation status and any errors
        """
        start_time = time.time()

        try:
            import json

            query_obj = json.loads(query)
            return ValidationResult(
                valid=True,
                validation_time_ms=(time.time() - start_time) * 1000,
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                error=f"Invalid JSON: {str(e)}",
                validation_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                error=f"Validation failed: {str(e)}",
                validation_time_ms=(time.time() - start_time) * 1000,
            )

    async def execute_query(self, query: str, limit: Optional[int] = None) -> ExecutionResult:
        """
        Execute MongoDB query and return results

        Args:
            query: MongoDB query (JSON format with collection)
            limit: Maximum number of rows to return

        Returns:
            ExecutionResult with query results
        """
        if limit is None:
            limit = self.provider_config.max_rows

        start_time = time.time()

        try:
            import json

            query_obj = json.loads(query)

            if "collection" not in query_obj:
                return ExecutionResult(
                    success=False,
                    error="Query must include 'collection' field",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            collection_name = query_obj.pop("collection")
            collection = self.db[collection_name]

            pipeline = query_obj.get("pipeline", [])
            if pipeline:
                cursor = collection.aggregate(pipeline)
            else:
                filter_query = query_obj.get("filter", {})
                cursor = collection.find(filter_query).limit(limit)

            rows = list(cursor)
            columns = []
            sample_rows = []

            if rows:
                columns = list(rows[0].keys())
                sample_rows = [dict(row) for row in rows[:10]]

            return ExecutionResult(
                success=True,
                row_count=len(rows),
                columns=columns,
                sample_rows=sample_rows,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except PyMongoError as e:
            return ExecutionResult(
                success=False,
                error=f"MongoDB error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except json.JSONDecodeError as e:
            return ExecutionResult(
                success=False,
                error=f"Invalid JSON query: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    async def explain_query(self, query: str) -> Optional[str]:
        """
        Get query execution plan

        Args:
            query: MongoDB query to explain

        Returns:
            Query execution plan as string
        """
        try:
            import json

            query_obj = json.loads(query)

            if "collection" not in query_obj:
                return "Query must include 'collection' field"

            collection_name = query_obj.pop("collection")
            collection = self.db[collection_name]

            pipeline = query_obj.get("pipeline", [])
            if pipeline:
                return str(list(collection.aggregate(pipeline + [{"$explain": True}])))
            else:
                filter_query = query_obj.get("filter", {})
                return str(collection.find(filter_query).explain())
        except Exception as e:
            return f"Error getting query plan: {str(e)}"

    async def close(self) -> None:
        """Close MongoDB connections"""
        if self.client:
            self.client.close()


def create_mongodb_provider(
    host: str = "localhost",
    port: int = 27017,
    database: str = "text2x",
    username: str = "",
    password: str = "",
    **kwargs,
) -> MongoDBProvider:
    """
    Create MongoDB provider with sensible defaults

    Args:
        host: MongoDB host
        port: MongoDB port
        database: Database name
        username: Username
        password: Password
        **kwargs: Additional configuration parameters

    Returns:
        Configured MongoDBProvider instance
    """
    config = MongoDBConnectionConfig(
        host=host, port=port, database=database, username=username, password=password, **kwargs
    )

    return MongoDBProvider(config)
