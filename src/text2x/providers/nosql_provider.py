"""NoSQL Provider Implementation for MongoDB"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import errors as pymongo_errors
from pymongo.collection import Collection as SyncCollection

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

    connection_string: str  # mongodb://host:port or mongodb+srv://...
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    auth_source: str = "admin"
    replica_set: Optional[str] = None
    tls: bool = False
    tls_ca_file: Optional[str] = None
    tls_cert_file: Optional[str] = None
    server_selection_timeout_ms: int = 30000
    connect_timeout_ms: int = 30000
    max_pool_size: int = 100
    min_pool_size: int = 0
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def get_connection_string(self) -> str:
        """Build complete MongoDB connection string"""
        # If connection string already includes auth, use as-is
        if self.username and self.password and "@" not in self.connection_string:
            # Parse the connection string
            parsed = urlparse(self.connection_string)
            # Reconstruct with auth
            scheme = parsed.scheme
            host_port = parsed.netloc
            path = parsed.path or ""

            conn_str = f"{scheme}://{self.username}:{self.password}@{host_port}{path}"

            # Add auth source and other params
            params = []
            if self.auth_source:
                params.append(f"authSource={self.auth_source}")
            if self.replica_set:
                params.append(f"replicaSet={self.replica_set}")
            if self.tls:
                params.append("tls=true")
            if self.tls_ca_file:
                params.append(f"tlsCAFile={self.tls_ca_file}")
            if self.tls_cert_file:
                params.append(f"tlsCertificateKeyFile={self.tls_cert_file}")

            params.extend(f"{k}={v}" for k, v in self.extra_params.items())

            if params:
                conn_str += "?" + "&".join(params)

            return conn_str

        return self.connection_string


class NoSQLProvider(QueryProvider):
    """NoSQL Provider for MongoDB"""

    def __init__(
        self, config: MongoDBConnectionConfig, provider_config: Optional[ProviderConfig] = None
    ):
        """
        Initialize NoSQL Provider for MongoDB

        Args:
            config: MongoDB connection configuration
            provider_config: General provider configuration
        """
        self.config = config
        self.provider_config = provider_config or ProviderConfig(provider_type="nosql")

        # Create async MongoDB client
        self.client = AsyncIOMotorClient(
            config.get_connection_string(),
            serverSelectionTimeoutMS=config.server_selection_timeout_ms,
            connectTimeoutMS=config.connect_timeout_ms,
            maxPoolSize=config.max_pool_size,
            minPoolSize=config.min_pool_size,
        )

        self.database = self.client[config.database]
        self._schema_cache: Optional[SchemaDefinition] = None
        self._cache_time: Optional[float] = None
        self._cache_ttl = 3600  # Cache schema for 1 hour

    def get_provider_id(self) -> str:
        """Unique identifier for this provider"""
        return f"nosql_mongodb"

    def get_query_language(self) -> str:
        """Query language supported by this provider"""
        return "MongoDB Query"

    def get_capabilities(self) -> List[ProviderCapability]:
        """List of capabilities this provider supports"""
        return [
            ProviderCapability.SCHEMA_INTROSPECTION,
            ProviderCapability.QUERY_VALIDATION,
            ProviderCapability.QUERY_EXECUTION,
        ]

    async def get_schema(self, force_refresh: bool = False) -> SchemaDefinition:
        """
        Retrieve MongoDB schema by sampling documents from collections

        Args:
            force_refresh: Force refresh of cached schema

        Returns:
            SchemaDefinition with inferred schema from sample documents
        """
        # Check cache
        current_time = time.time()
        if not force_refresh and self._schema_cache and self._cache_time:
            if current_time - self._cache_time < self._cache_ttl:
                return self._schema_cache

        tables = []

        try:
            # List all collections
            collection_names = await self.database.list_collection_names()

            for collection_name in collection_names:
                # Skip system collections
                if collection_name.startswith("system."):
                    continue

                collection = self.database[collection_name]

                # Get collection stats
                try:
                    stats = await self.database.command("collStats", collection_name)
                    row_count = stats.get("count", 0)
                except Exception:
                    row_count = None

                # Sample documents to infer schema
                columns = await self._infer_schema_from_samples(collection)

                # Get indexes
                indexes = []
                try:
                    cursor = collection.list_indexes()
                    async for index in cursor:
                        from .base import IndexInfo

                        index_info = IndexInfo(
                            name=index.get("name", ""),
                            columns=list(index.get("key", {}).keys()),
                            unique=index.get("unique", False),
                            type=None,  # MongoDB doesn't expose index type in the same way
                        )
                        indexes.append(index_info)
                except Exception:
                    pass

                table_info = TableInfo(
                    name=collection_name,
                    columns=columns,
                    indexes=indexes,
                    foreign_keys=[],  # MongoDB doesn't have explicit foreign keys
                    primary_key=["_id"],  # MongoDB always has _id
                    comment=f"MongoDB collection with {row_count} documents" if row_count else None,
                    row_count=row_count,
                )
                tables.append(table_info)

            schema_def = SchemaDefinition(
                tables=tables,
                collections=collection_names,
                metadata={
                    "database": self.config.database,
                    "collection_count": len(collection_names),
                    "provider_type": "mongodb",
                },
            )

            # Cache the schema
            self._schema_cache = schema_def
            self._cache_time = current_time

            return schema_def

        except Exception as e:
            # Return empty schema on error
            return SchemaDefinition(
                tables=[],
                collections=[],
                metadata={
                    "error": str(e),
                    "database": self.config.database,
                },
            )

    async def _infer_schema_from_samples(
        self, collection, sample_size: int = 100
    ) -> List[ColumnInfo]:
        """
        Infer schema by sampling documents from a collection

        Args:
            collection: MongoDB collection
            sample_size: Number of documents to sample

        Returns:
            List of inferred columns with flattened dot-notation for nested fields
        """
        field_types: Dict[str, set] = {}
        field_nullable: Dict[str, int] = {}
        total_docs = 0

        try:
            cursor = collection.find().limit(sample_size)
            async for doc in cursor:
                total_docs += 1
                self._sample_document(doc, "", field_types, field_nullable)

            columns = self._build_columns(field_types, field_nullable)
            return columns

        except Exception:
            return [
                ColumnInfo(
                    name="_id",
                    type="ObjectId",
                    nullable=False,
                    primary_key=True,
                )
            ]

    def _sample_document(
        self,
        doc: Any,
        prefix: str,
        field_types: Dict[str, set],
        field_nullable: Dict[str, int],
    ) -> None:
        """Recursively sample document to collect all field paths"""
        if doc is None:
            return

        if isinstance(doc, dict):
            for key, value in doc.items():
                full_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    self._sample_document(value, full_key, field_types, field_nullable)
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        self._sample_document(value[0], full_key, field_types, field_nullable)
                    self._record_field(field_types, field_nullable, full_key, "Array")
                else:
                    bson_type = self._get_bson_type(value)
                    self._record_field(field_types, field_nullable, full_key, bson_type)

    def _record_field(
        self,
        field_types: Dict[str, set],
        field_nullable: Dict[str, int],
        field_name: str,
        bson_type: str,
    ) -> None:
        """Record a field and its type"""
        if field_name not in field_types:
            field_types[field_name] = set()
            field_nullable[field_name] = 0
        field_types[field_name].add(bson_type)

    def _build_columns(
        self,
        field_types: Dict[str, set],
        field_nullable: Dict[str, int],
    ) -> List[ColumnInfo]:
        """Build ColumnInfo list from collected field data"""
        columns = []

        for field_name, types in sorted(field_types.items()):
            col_info = ColumnInfo(
                name=field_name,
                type=self._merge_types(types),
                nullable=field_nullable.get(field_name, 0) > 0,
                primary_key=(field_name == "_id"),
            )
            columns.append(col_info)

        id_col = next((c for c in columns if c.name == "_id"), None)
        if id_col:
            columns = [id_col] + [c for c in columns if c.name != "_id"]

        return columns

    def _merge_types(self, types: set) -> str:
        """Merge multiple types into a single type string"""
        if len(types) == 1:
            return next(iter(types))
        return " | ".join(sorted(types))

    def _flatten_document(self, doc: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Flatten a nested document structure

        Args:
            doc: Document to flatten
            prefix: Prefix for nested fields

        Returns:
            Flattened document
        """
        result = {}

        for key, value in doc.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested documents
                result.update(self._flatten_document(value, full_key))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # For arrays of documents, flatten first element
                result[full_key] = f"Array<{self._get_bson_type(value[0])}>"
            else:
                result[full_key] = value

        return result

    def _get_bson_type(self, value: Any) -> str:
        """
        Get BSON type name for a value

        Args:
            value: Value to check

        Returns:
            BSON type name
        """
        type_mapping = {
            bool: "Boolean",
            int: "Int32",
            float: "Double",
            str: "String",
            bytes: "BinData",
            dict: "Object",
            list: "Array",
        }

        # Handle None
        if value is None:
            return "Null"

        # Check for MongoDB-specific types
        type_name = type(value).__name__
        if type_name == "ObjectId":
            return "ObjectId"
        elif type_name == "datetime":
            return "Date"
        elif type_name == "Timestamp":
            return "Timestamp"

        # Get from mapping
        return type_mapping.get(type(value), "Unknown")

    async def validate_syntax(self, query: str) -> ValidationResult:
        """
        Validate MongoDB query syntax

        Args:
            query: MongoDB query (JSON or Python dict string)

        Returns:
            ValidationResult with validation status
        """
        start_time = time.time()

        try:
            # Parse the query as JSON
            parsed_query = json.loads(query) if isinstance(query, str) else query

            # Basic validation
            if not isinstance(parsed_query, dict):
                return ValidationResult(
                    valid=False,
                    error="Query must be a JSON object",
                    validation_time_ms=(time.time() - start_time) * 1000,
                )

            # Check for required fields
            if "collection" not in parsed_query:
                return ValidationResult(
                    valid=False,
                    error="Query must specify a 'collection' field",
                    validation_time_ms=(time.time() - start_time) * 1000,
                )

            # Validate operation type
            operation = parsed_query.get("operation", "find")
            valid_operations = [
                "find",
                "find_one",
                "aggregate",
                "count_documents",
                "insert_one",
                "insert_many",
                "update_one",
                "update_many",
                "delete_one",
                "delete_many",
                "distinct",
            ]

            if operation not in valid_operations:
                return ValidationResult(
                    valid=False,
                    error=f"Invalid operation '{operation}'. Must be one of: {', '.join(valid_operations)}",
                    validation_time_ms=(time.time() - start_time) * 1000,
                )

            # Check if collection exists
            collection_names = await self.database.list_collection_names()
            collection_name = parsed_query["collection"]

            warnings = []
            if collection_name not in collection_names:
                warnings.append(f"Collection '{collection_name}' does not exist in database")

            return ValidationResult(
                valid=True,
                warnings=warnings,
                parsed_query=parsed_query,
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
                error=f"Validation error: {str(e)}",
                validation_time_ms=(time.time() - start_time) * 1000,
            )

    async def execute_query(self, query: str, limit: Optional[int] = None) -> ExecutionResult:
        """
        Execute MongoDB query and return results

        Args:
            query: MongoDB query (JSON format)
            limit: Maximum number of documents to return

        Returns:
            ExecutionResult with query results
        """
        if limit is None:
            limit = self.provider_config.max_rows

        start_time = time.time()

        try:
            # Parse query
            parsed_query = json.loads(query) if isinstance(query, str) else query

            collection_name = parsed_query["collection"]
            operation = parsed_query.get("operation", "find")

            collection = self.database[collection_name]

            # Execute based on operation type
            if operation == "find":
                result = await self._execute_find(collection, parsed_query, limit)
            elif operation == "find_one":
                result = await self._execute_find_one(collection, parsed_query)
            elif operation == "aggregate":
                result = await self._execute_aggregate(collection, parsed_query, limit)
            elif operation == "count_documents":
                result = await self._execute_count(collection, parsed_query)
            elif operation == "distinct":
                result = await self._execute_distinct(collection, parsed_query)
            elif operation.startswith("insert"):
                result = await self._execute_insert(collection, parsed_query, operation)
            elif operation.startswith("update"):
                result = await self._execute_update(collection, parsed_query, operation)
            elif operation.startswith("delete"):
                result = await self._execute_delete(collection, parsed_query, operation)
            else:
                return ExecutionResult(
                    success=False,
                    error=f"Unsupported operation: {operation}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            result.execution_time_ms = (time.time() - start_time) * 1000
            return result

        except pymongo_errors.ExecutionTimeout:
            return ExecutionResult(
                success=False,
                error=f"Query execution timeout after {self.provider_config.timeout_seconds}s",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    async def _execute_find(
        self, collection, parsed_query: Dict[str, Any], limit: int
    ) -> ExecutionResult:
        """Execute find operation"""
        filter_query = parsed_query.get("filter", {})
        projection = parsed_query.get("projection")
        sort = parsed_query.get("sort")
        skip = parsed_query.get("skip", 0)

        cursor = collection.find(filter_query, projection)

        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)

        cursor = cursor.limit(limit)

        # Fetch results
        documents = []
        async for doc in cursor:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
            documents.append(doc)

        # Extract column names from first document
        columns = []
        if documents:
            columns = list(documents[0].keys())

        return ExecutionResult(
            success=True,
            row_count=len(documents),
            columns=columns,
            sample_rows=documents[:10],
        )

    async def _execute_find_one(self, collection, parsed_query: Dict[str, Any]) -> ExecutionResult:
        """Execute find_one operation"""
        filter_query = parsed_query.get("filter", {})
        projection = parsed_query.get("projection")

        doc = await collection.find_one(filter_query, projection)

        if doc:
            doc["_id"] = str(doc["_id"])
            columns = list(doc.keys())
            return ExecutionResult(
                success=True,
                row_count=1,
                columns=columns,
                sample_rows=[doc],
            )
        else:
            return ExecutionResult(
                success=True,
                row_count=0,
                columns=[],
                sample_rows=[],
            )

    async def _execute_aggregate(
        self, collection, parsed_query: Dict[str, Any], limit: int
    ) -> ExecutionResult:
        """Execute aggregation pipeline"""
        pipeline = parsed_query.get("pipeline", [])

        # Add limit to pipeline if not present
        has_limit = any(stage.get("$limit") for stage in pipeline if isinstance(stage, dict))
        if not has_limit:
            pipeline.append({"$limit": limit})

        cursor = collection.aggregate(pipeline)

        documents = []
        async for doc in cursor:
            if "_id" in doc and hasattr(doc["_id"], "__str__"):
                doc["_id"] = str(doc["_id"])
            documents.append(doc)

        columns = []
        if documents:
            columns = list(documents[0].keys())

        return ExecutionResult(
            success=True,
            row_count=len(documents),
            columns=columns,
            sample_rows=documents[:10],
        )

    async def _execute_count(self, collection, parsed_query: Dict[str, Any]) -> ExecutionResult:
        """Execute count_documents operation"""
        filter_query = parsed_query.get("filter", {})
        count = await collection.count_documents(filter_query)

        return ExecutionResult(
            success=True,
            row_count=1,
            columns=["count"],
            sample_rows=[{"count": count}],
        )

    async def _execute_distinct(self, collection, parsed_query: Dict[str, Any]) -> ExecutionResult:
        """Execute distinct operation"""
        field = parsed_query.get("field")
        filter_query = parsed_query.get("filter", {})

        if not field:
            return ExecutionResult(
                success=False,
                error="distinct operation requires 'field' parameter",
            )

        values = await collection.distinct(field, filter_query)

        return ExecutionResult(
            success=True,
            row_count=len(values),
            columns=[field],
            sample_rows=[{field: v} for v in values[:10]],
        )

    async def _execute_insert(
        self, collection, parsed_query: Dict[str, Any], operation: str
    ) -> ExecutionResult:
        """Execute insert operation"""
        if operation == "insert_one":
            document = parsed_query.get("document")
            if not document:
                return ExecutionResult(success=False, error="Missing 'document' field")

            result = await collection.insert_one(document)
            return ExecutionResult(
                success=True,
                affected_rows=1,
                sample_rows=[{"inserted_id": str(result.inserted_id)}],
            )

        elif operation == "insert_many":
            documents = parsed_query.get("documents")
            if not documents:
                return ExecutionResult(success=False, error="Missing 'documents' field")

            result = await collection.insert_many(documents)
            return ExecutionResult(
                success=True,
                affected_rows=len(result.inserted_ids),
                sample_rows=[{"inserted_count": len(result.inserted_ids)}],
            )

        return ExecutionResult(success=False, error=f"Unknown insert operation: {operation}")

    async def _execute_update(
        self, collection, parsed_query: Dict[str, Any], operation: str
    ) -> ExecutionResult:
        """Execute update operation"""
        filter_query = parsed_query.get("filter", {})
        update = parsed_query.get("update")

        if not update:
            return ExecutionResult(success=False, error="Missing 'update' field")

        if operation == "update_one":
            result = await collection.update_one(filter_query, update)
            return ExecutionResult(
                success=True,
                affected_rows=result.modified_count,
                sample_rows=[
                    {
                        "matched_count": result.matched_count,
                        "modified_count": result.modified_count,
                    }
                ],
            )

        elif operation == "update_many":
            result = await collection.update_many(filter_query, update)
            return ExecutionResult(
                success=True,
                affected_rows=result.modified_count,
                sample_rows=[
                    {
                        "matched_count": result.matched_count,
                        "modified_count": result.modified_count,
                    }
                ],
            )

        return ExecutionResult(success=False, error=f"Unknown update operation: {operation}")

    async def _execute_delete(
        self, collection, parsed_query: Dict[str, Any], operation: str
    ) -> ExecutionResult:
        """Execute delete operation"""
        filter_query = parsed_query.get("filter", {})

        if operation == "delete_one":
            result = await collection.delete_one(filter_query)
            return ExecutionResult(
                success=True,
                affected_rows=result.deleted_count,
                sample_rows=[{"deleted_count": result.deleted_count}],
            )

        elif operation == "delete_many":
            result = await collection.delete_many(filter_query)
            return ExecutionResult(
                success=True,
                affected_rows=result.deleted_count,
                sample_rows=[{"deleted_count": result.deleted_count}],
            )

        return ExecutionResult(success=False, error=f"Unknown delete operation: {operation}")

    async def close(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()


# Factory function for easy provider creation
def create_nosql_provider(
    connection_string: str = "mongodb://localhost:27017",
    database: str = "text2x",
    username: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs,
) -> NoSQLProvider:
    """
    Create NoSQL provider with sensible defaults

    Args:
        connection_string: MongoDB connection string
        database: Database name
        username: Optional username
        password: Optional password
        **kwargs: Additional configuration parameters

    Returns:
        Configured NoSQLProvider instance
    """
    config = MongoDBConnectionConfig(
        connection_string=connection_string,
        database=database,
        username=username,
        password=password,
        **kwargs,
    )

    return NoSQLProvider(config)
