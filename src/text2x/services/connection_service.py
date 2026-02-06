"""Connection service for testing and introspecting database connections."""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from text2x.models.workspace import Connection, ConnectionStatus, ProviderType
from text2x.providers.base import SchemaDefinition, TableInfo
from text2x.providers.sql_provider import SQLConnectionConfig, SQLProvider

logger = logging.getLogger(__name__)


@dataclass
class ConnectionTestResult:
    """Result of connection test."""

    success: bool
    message: str
    latency_ms: Optional[float] = None
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    error_details: Optional[str] = None


@dataclass
class SchemaIntrospectionResult:
    """Result of schema introspection."""

    success: bool
    schema: Optional[SchemaDefinition] = None
    table_count: int = 0
    error: Optional[str] = None
    introspection_time_ms: Optional[float] = None


class ConnectionService:
    """Service for managing database connections."""

    @staticmethod
    async def test_connection(connection: Connection) -> ConnectionTestResult:
        """
        Test a database connection to verify connectivity.

        Args:
            connection: Connection model with credentials and details

        Returns:
            ConnectionTestResult with success status and latency
        """
        logger.info(f"Testing connection {connection.id} ({connection.name})")

        start_time = time.time()

        try:
            # Get provider type
            provider_type = connection.provider.type

            # Route to appropriate provider test
            if provider_type in [
                ProviderType.POSTGRESQL,
                ProviderType.MYSQL,
                ProviderType.REDSHIFT,
            ]:
                result = await ConnectionService._test_sql_connection(connection, provider_type)
            elif provider_type == ProviderType.MONGODB:
                result = await ConnectionService._test_nosql_connection(connection)
            elif provider_type == ProviderType.SPLUNK:
                result = await ConnectionService._test_splunk_connection(connection)
            elif provider_type in [
                ProviderType.ATHENA,
                ProviderType.BIGQUERY,
                ProviderType.SNOWFLAKE,
            ]:
                result = await ConnectionService._test_cloud_sql_connection(
                    connection, provider_type
                )
            elif provider_type in [
                ProviderType.OPENSEARCH,
                ProviderType.ELASTICSEARCH,
            ]:
                result = await ConnectionService._test_search_connection(connection, provider_type)
            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"Unsupported provider type: {provider_type.value}",
                    status=ConnectionStatus.ERROR,
                    error_details=f"Provider type {provider_type.value} not implemented",
                )

            # Add latency
            latency_ms = (time.time() - start_time) * 1000
            result.latency_ms = latency_ms

            logger.info(f"Connection test completed: {result.success} ({latency_ms:.2f}ms)")

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Connection test failed: {e}", exc_info=True)
            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {str(e)}",
                latency_ms=latency_ms,
                status=ConnectionStatus.ERROR,
                error_details=str(e),
            )

    @staticmethod
    async def _test_sql_connection(
        connection: Connection, provider_type: ProviderType
    ) -> ConnectionTestResult:
        """Test SQL database connection."""
        try:
            # Get credentials
            if not connection.credentials:
                return ConnectionTestResult(
                    success=False,
                    message="No credentials provided",
                    status=ConnectionStatus.ERROR,
                    error_details="Missing credentials",
                )

            username = connection.credentials.get("username")
            password = connection.credentials.get("password")

            if not username or not password:
                return ConnectionTestResult(
                    success=False,
                    message="Invalid credentials: missing username or password",
                    status=ConnectionStatus.ERROR,
                    error_details="Incomplete credentials",
                )

            # Determine dialect
            dialect_map = {
                ProviderType.POSTGRESQL: "postgresql",
                ProviderType.MYSQL: "mysql",
                ProviderType.REDSHIFT: "postgresql",
            }
            dialect = dialect_map.get(provider_type, "postgresql")

            # Determine driver
            driver_map = {
                ProviderType.POSTGRESQL: "psycopg2",
                ProviderType.MYSQL: "pymysql",
                ProviderType.REDSHIFT: "psycopg2",
            }
            driver = driver_map.get(provider_type)

            # Build config
            config = SQLConnectionConfig(
                host=connection.host,
                port=connection.port or 5432,
                database=connection.database,
                username=username,
                password=password,
                dialect=dialect,
                driver=driver,
                pool_size=1,
                max_overflow=0,
                echo=False,
                extra_params=connection.connection_options or {},
            )

            # Create provider and test
            provider = SQLProvider(config)

            try:
                # Run a simple test query
                test_result = await asyncio.wait_for(
                    provider.execute_query("SELECT 1 as test", limit=1), timeout=10.0
                )

                if test_result and test_result.success:
                    return ConnectionTestResult(
                        success=True,
                        message="Connection successful",
                        status=ConnectionStatus.CONNECTED,
                    )
                else:
                    return ConnectionTestResult(
                        success=False,
                        message="Query execution failed",
                        status=ConnectionStatus.ERROR,
                        error_details=test_result.error if test_result else "Unknown error",
                    )

            finally:
                await provider.close()

        except asyncio.TimeoutError:
            return ConnectionTestResult(
                success=False,
                message="Connection timeout",
                status=ConnectionStatus.DISCONNECTED,
                error_details="Connection attempt timed out after 10 seconds",
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                status=ConnectionStatus.ERROR,
                error_details=str(e),
            )

    @staticmethod
    async def _test_nosql_connection(connection: Connection) -> ConnectionTestResult:
        """Test NoSQL (MongoDB) connection."""
        try:
            # Import MongoDB client if available
            try:
                from pymongo import MongoClient
                from pymongo.errors import ConnectionFailure
            except ImportError:
                return ConnectionTestResult(
                    success=False,
                    message="MongoDB client not installed",
                    status=ConnectionStatus.ERROR,
                    error_details="pymongo library not available",
                )

            # Build connection string - MongoDB allows connections without credentials
            username = connection.credentials.get("username") if connection.credentials else None
            password = connection.credentials.get("password") if connection.credentials else None

            if username and password:
                conn_str = f"mongodb://{username}:{password}@{connection.host}:{connection.port or 27017}/{connection.database}"
            else:
                conn_str = (
                    f"mongodb://{connection.host}:{connection.port or 27017}/{connection.database}"
                )

            # Test connection
            client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)

            # Run admin command to verify connection
            await asyncio.to_thread(client.admin.command, "ping")

            client.close()

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                status=ConnectionStatus.CONNECTED,
            )

        except ConnectionFailure as e:
            return ConnectionTestResult(
                success=False,
                message="MongoDB connection failed",
                status=ConnectionStatus.ERROR,
                error_details=str(e),
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                status=ConnectionStatus.ERROR,
                error_details=str(e),
            )

    @staticmethod
    async def _test_splunk_connection(connection: Connection) -> ConnectionTestResult:
        """Test Splunk connection."""
        try:
            # Import Splunk SDK if available
            try:
                import splunklib.client as splunk_client
            except ImportError:
                return ConnectionTestResult(
                    success=False,
                    message="Splunk SDK not installed",
                    status=ConnectionStatus.ERROR,
                    error_details="splunk-sdk library not available",
                )

            if not connection.credentials:
                return ConnectionTestResult(
                    success=False,
                    message="No credentials provided",
                    status=ConnectionStatus.ERROR,
                    error_details="Missing credentials",
                )

            username = connection.credentials.get("username")
            password = connection.credentials.get("password")

            if not username or not password:
                return ConnectionTestResult(
                    success=False,
                    message="Invalid credentials",
                    status=ConnectionStatus.ERROR,
                    error_details="Incomplete credentials",
                )

            # Create Splunk service
            service = splunk_client.Service(
                host=connection.host,
                port=connection.port or 8089,
                username=username,
                password=password,
            )

            # Login to verify credentials
            await asyncio.to_thread(service.login)

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                status=ConnectionStatus.CONNECTED,
            )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Splunk connection failed: {str(e)}",
                status=ConnectionStatus.ERROR,
                error_details=str(e),
            )

    @staticmethod
    async def _test_cloud_sql_connection(
        connection: Connection, provider_type: ProviderType
    ) -> ConnectionTestResult:
        """Test cloud SQL connection (Athena, BigQuery, Snowflake)."""
        # For now, return a placeholder indicating not implemented
        return ConnectionTestResult(
            success=False,
            message=f"{provider_type.value} connection testing not yet implemented",
            status=ConnectionStatus.PENDING,
            error_details="Cloud SQL provider testing in development",
        )

    @staticmethod
    async def _test_search_connection(
        connection: Connection, provider_type: ProviderType
    ) -> ConnectionTestResult:
        """Test search engine connection (OpenSearch, Elasticsearch)."""
        try:
            # Import OpenSearch/Elasticsearch client if available
            try:
                from opensearchpy import OpenSearch
            except ImportError:
                return ConnectionTestResult(
                    success=False,
                    message="OpenSearch client not installed",
                    status=ConnectionStatus.ERROR,
                    error_details="opensearch-py library not available",
                )

            # Build connection config
            if not connection.credentials:
                return ConnectionTestResult(
                    success=False,
                    message="No credentials provided",
                    status=ConnectionStatus.ERROR,
                    error_details="Missing credentials",
                )

            username = connection.credentials.get("username")
            password = connection.credentials.get("password")

            # Create client
            client = OpenSearch(
                hosts=[{"host": connection.host, "port": connection.port or 9200}],
                http_auth=(username, password) if username and password else None,
                use_ssl=connection.connection_options.get("use_ssl", True),
                verify_certs=connection.connection_options.get("verify_certs", True),
                timeout=5,
            )

            # Test connection with cluster health
            await asyncio.to_thread(client.cluster.health)

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                status=ConnectionStatus.CONNECTED,
            )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Search engine connection failed: {str(e)}",
                status=ConnectionStatus.ERROR,
                error_details=str(e),
            )

    @staticmethod
    async def introspect_schema(
        connection: Connection,
    ) -> SchemaIntrospectionResult:
        """
        Introspect database schema.

        Args:
            connection: Connection model with credentials and details

        Returns:
            SchemaIntrospectionResult with schema definition
        """
        logger.info(f"Introspecting schema for connection {connection.id}")

        start_time = time.time()

        try:
            provider_type = connection.provider.type

            # Route to appropriate provider introspection
            if provider_type in [
                ProviderType.POSTGRESQL,
                ProviderType.MYSQL,
                ProviderType.REDSHIFT,
            ]:
                result = await ConnectionService._introspect_sql_schema(connection, provider_type)
            elif provider_type == ProviderType.MONGODB:
                result = await ConnectionService._introspect_nosql_schema(connection)
            elif provider_type == ProviderType.SPLUNK:
                result = await ConnectionService._introspect_splunk_schema(connection)
            else:
                return SchemaIntrospectionResult(
                    success=False,
                    error=f"Schema introspection not supported for {provider_type.value}",
                )

            # Add timing
            introspection_ms = (time.time() - start_time) * 1000
            result.introspection_time_ms = introspection_ms

            logger.info(
                f"Schema introspection completed: {result.success} "
                f"({result.table_count} tables, {introspection_ms:.2f}ms)"
            )

            return result

        except Exception as e:
            introspection_ms = (time.time() - start_time) * 1000
            logger.error(f"Schema introspection failed: {e}", exc_info=True)
            return SchemaIntrospectionResult(
                success=False,
                error=str(e),
                introspection_time_ms=introspection_ms,
            )

    @staticmethod
    async def _introspect_sql_schema(
        connection: Connection, provider_type: ProviderType
    ) -> SchemaIntrospectionResult:
        """Introspect SQL database schema."""
        try:
            if not connection.credentials:
                return SchemaIntrospectionResult(success=False, error="No credentials provided")

            username = connection.credentials.get("username")
            password = connection.credentials.get("password")

            if not username or not password:
                return SchemaIntrospectionResult(success=False, error="Invalid credentials")

            # Determine dialect and driver
            dialect_map = {
                ProviderType.POSTGRESQL: "postgresql",
                ProviderType.MYSQL: "mysql",
                ProviderType.REDSHIFT: "postgresql",
            }
            dialect = dialect_map.get(provider_type, "postgresql")

            driver_map = {
                ProviderType.POSTGRESQL: "psycopg2",
                ProviderType.MYSQL: "pymysql",
                ProviderType.REDSHIFT: "psycopg2",
            }
            driver = driver_map.get(provider_type)

            # Build config
            config = SQLConnectionConfig(
                host=connection.host,
                port=connection.port or 5432,
                database=connection.database,
                username=username,
                password=password,
                dialect=dialect,
                driver=driver,
                pool_size=1,
                max_overflow=0,
                echo=False,
                extra_params=connection.connection_options or {},
            )

            # Create provider and introspect
            provider = SQLProvider(config)

            try:
                # Get schema
                schema = await asyncio.wait_for(provider.get_schema(), timeout=30.0)

                return SchemaIntrospectionResult(
                    success=True, schema=schema, table_count=len(schema.tables)
                )

            finally:
                await provider.close()

        except asyncio.TimeoutError:
            return SchemaIntrospectionResult(
                success=False, error="Schema introspection timeout after 30 seconds"
            )
        except Exception as e:
            return SchemaIntrospectionResult(
                success=False, error=f"Schema introspection failed: {str(e)}"
            )

    @staticmethod
    async def _introspect_nosql_schema(
        connection: Connection,
    ) -> SchemaIntrospectionResult:
        """Introspect NoSQL (MongoDB) schema with sampled document fields."""
        try:
            from pymongo import MongoClient
        except ImportError:
            return SchemaIntrospectionResult(success=False, error="MongoDB client not installed")

        username = None
        password = None
        if connection.credentials:
            username = connection.credentials.get("username")
            password = connection.credentials.get("password")

        if username and password:
            conn_str = f"mongodb://{username}:{password}@{connection.host}:{connection.port or 27017}/{connection.database}"
        else:
            conn_str = (
                f"mongodb://{connection.host}:{connection.port or 27017}/{connection.database}"
            )

        try:
            client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)
            db = client[connection.database]
            collection_names = db.list_collection_names()

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

            client.close()

            schema = SchemaDefinition(
                tables=[],
                collections=collections_with_schema,
                metadata={"database": connection.database},
            )

            return SchemaIntrospectionResult(
                success=True, schema=schema, table_count=len(collection_names)
            )

        except Exception as e:
            return SchemaIntrospectionResult(
                success=False, error=f"MongoDB schema introspection failed: {str(e)}"
            )

    @staticmethod
    async def _introspect_splunk_schema(
        connection: Connection,
    ) -> SchemaIntrospectionResult:
        """Introspect Splunk schema (sourcetypes)."""
        try:
            # Import Splunk SDK if available
            try:
                import splunklib.client as splunk_client
            except ImportError:
                return SchemaIntrospectionResult(success=False, error="Splunk SDK not installed")

            if not connection.credentials:
                return SchemaIntrospectionResult(success=False, error="No credentials provided")

            username = connection.credentials.get("username")
            password = connection.credentials.get("password")

            if not username or not password:
                return SchemaIntrospectionResult(success=False, error="Invalid credentials")

            # Create Splunk service
            service = splunk_client.Service(
                host=connection.host,
                port=connection.port or 8089,
                username=username,
                password=password,
            )

            # Login
            await asyncio.to_thread(service.login)

            # Get sourcetypes (this is a simplified version)
            # In practice, you'd query the Splunk REST API for available sourcetypes
            sourcetypes = []
            indexes = await asyncio.to_thread(lambda: list(service.indexes))

            for index in indexes[:10]:  # Limit to 10 indexes for performance
                sourcetypes.append(index.name)

            # Build schema definition
            schema = SchemaDefinition(sourcetypes=sourcetypes, tables=[])

            return SchemaIntrospectionResult(
                success=True, schema=schema, table_count=len(sourcetypes)
            )

        except Exception as e:
            return SchemaIntrospectionResult(
                success=False, error=f"Splunk schema introspection failed: {str(e)}"
            )
