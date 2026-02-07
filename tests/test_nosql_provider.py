"""Tests for NoSQL MongoDB Provider"""

import pytest
import pytest_asyncio
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

from text2x.providers import (
    NoSQLProvider,
    MongoDBConnectionConfig,
    create_nosql_provider,
    ProviderCapability,
)
from tests.config import TEST_MONGODB_CONFIG


# Test connection configuration - uses test containers (docker-compose.test.yml)
TEST_CONFIG = MongoDBConnectionConfig(**TEST_MONGODB_CONFIG)


@pytest_asyncio.fixture
async def nosql_provider():
    """Create NoSQL provider for testing"""
    provider = NoSQLProvider(TEST_CONFIG)
    yield provider
    await provider.close()


@pytest_asyncio.fixture
async def setup_test_database():
    """Setup test MongoDB database with sample collections"""
    client = AsyncIOMotorClient(TEST_CONFIG.get_connection_string())
    db = client[TEST_CONFIG.database]

    # Clean up any existing test collections
    await db.test_customers.drop()
    await db.test_orders.drop()

    # Insert test data into customers collection
    await db.test_customers.insert_many(
        [
            {
                "name": "Alice Smith",
                "email": "alice@example.com",
                "age": 30,
                "address": {"city": "New York", "state": "NY"},
                "tags": ["premium", "active"],
            },
            {
                "name": "Bob Jones",
                "email": "bob@example.com",
                "age": 25,
                "address": {"city": "Los Angeles", "state": "CA"},
                "tags": ["active"],
            },
            {
                "name": "Charlie Brown",
                "email": "charlie@example.com",
                "age": 35,
                "address": {"city": "Chicago", "state": "IL"},
                "tags": ["premium"],
            },
        ]
    )

    # Insert test data into orders collection
    customers = await db.test_customers.find().to_list(length=None)
    customer_ids = [c["_id"] for c in customers]

    await db.test_orders.insert_many(
        [
            {
                "customer_id": customer_ids[0],
                "amount": 100.50,
                "status": "completed",
                "items": ["item1", "item2"],
            },
            {
                "customer_id": customer_ids[0],
                "amount": 200.00,
                "status": "completed",
                "items": ["item3"],
            },
            {
                "customer_id": customer_ids[1],
                "amount": 150.75,
                "status": "pending",
                "items": ["item1", "item4"],
            },
            {
                "customer_id": customer_ids[2],
                "amount": 300.00,
                "status": "completed",
                "items": ["item5", "item6", "item7"],
            },
        ]
    )

    # Create indexes
    await db.test_customers.create_index("email", unique=True)
    await db.test_orders.create_index("customer_id")
    await db.test_orders.create_index("status")

    yield

    # Cleanup
    await db.test_customers.drop()
    await db.test_orders.drop()
    client.close()


class TestNoSQLProvider:
    """Test NoSQL Provider functionality"""

    @pytest.mark.asyncio
    async def test_provider_id(self, nosql_provider):
        """Test provider ID"""
        assert nosql_provider.get_provider_id() == "nosql_mongodb"

    @pytest.mark.asyncio
    async def test_query_language(self, nosql_provider):
        """Test query language"""
        assert nosql_provider.get_query_language() == "MongoDB Query"

    @pytest.mark.asyncio
    async def test_capabilities(self, nosql_provider):
        """Test provider capabilities"""
        capabilities = nosql_provider.get_capabilities()
        assert ProviderCapability.SCHEMA_INTROSPECTION in capabilities
        assert ProviderCapability.QUERY_VALIDATION in capabilities
        assert ProviderCapability.QUERY_EXECUTION in capabilities

    @pytest.mark.asyncio
    async def test_get_schema(self, nosql_provider, setup_test_database):
        """Test schema introspection"""
        schema = await nosql_provider.get_schema()

        assert schema is not None
        assert len(schema.tables) >= 2  # At least our test collections
        assert len(schema.collections) >= 2

        # Find test_customers collection
        customers_table = next((t for t in schema.tables if t.name == "test_customers"), None)
        assert customers_table is not None

        # Check that _id is present and is primary key
        id_col = next((c for c in customers_table.columns if c.name == "_id"), None)
        assert id_col is not None
        assert id_col.primary_key

        # Check for inferred fields
        name_col = next((c for c in customers_table.columns if c.name == "name"), None)
        assert name_col is not None

        # Find test_orders collection
        orders_table = next((t for t in schema.tables if t.name == "test_orders"), None)
        assert orders_table is not None

        # Check indexes
        assert len(orders_table.indexes) > 0

    @pytest.mark.asyncio
    async def test_get_schema_cached(self, nosql_provider, setup_test_database):
        """Test schema caching"""
        # First call should fetch schema
        schema1 = await nosql_provider.get_schema()
        cache_time1 = nosql_provider._cache_time

        # Second call should use cache
        schema2 = await nosql_provider.get_schema()
        cache_time2 = nosql_provider._cache_time

        assert cache_time1 == cache_time2
        assert schema1 == schema2

        # Force refresh should update cache
        schema3 = await nosql_provider.get_schema(force_refresh=True)
        cache_time3 = nosql_provider._cache_time

        assert cache_time3 > cache_time1

    @pytest.mark.asyncio
    async def test_validate_syntax_valid(self, nosql_provider, setup_test_database):
        """Test syntax validation with valid query"""
        query = json.dumps(
            {"collection": "test_customers", "operation": "find", "filter": {"age": {"$gte": 25}}}
        )

        result = await nosql_provider.validate_syntax(query)

        assert result.valid
        assert result.error is None
        assert result.validation_time_ms is not None

    @pytest.mark.asyncio
    async def test_validate_syntax_invalid_json(self, nosql_provider):
        """Test syntax validation with invalid JSON"""
        query = "not a valid json"
        result = await nosql_provider.validate_syntax(query)

        assert not result.valid
        assert "JSON" in result.error

    @pytest.mark.asyncio
    async def test_validate_syntax_missing_collection(self, nosql_provider):
        """Test syntax validation with missing collection field"""
        query = json.dumps({"operation": "find", "filter": {}})
        result = await nosql_provider.validate_syntax(query)

        assert not result.valid
        assert "collection" in result.error

    @pytest.mark.asyncio
    async def test_validate_syntax_invalid_operation(self, nosql_provider):
        """Test syntax validation with invalid operation"""
        query = json.dumps({"collection": "test_customers", "operation": "invalid_operation"})
        result = await nosql_provider.validate_syntax(query)

        assert not result.valid
        assert "operation" in result.error

    @pytest.mark.asyncio
    async def test_validate_syntax_nonexistent_collection(
        self, nosql_provider, setup_test_database
    ):
        """Test syntax validation with nonexistent collection"""
        query = json.dumps({"collection": "nonexistent_collection", "operation": "find"})
        result = await nosql_provider.validate_syntax(query)

        # Should be valid but with warning
        assert result.valid
        assert len(result.warnings) > 0
        assert "does not exist" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_execute_query_find(self, nosql_provider, setup_test_database):
        """Test query execution with find operation"""
        query = json.dumps(
            {"collection": "test_customers", "operation": "find", "filter": {"age": {"$gte": 30}}}
        )

        result = await nosql_provider.execute_query(query)

        assert result.success
        assert result.row_count == 2  # Alice (30) and Charlie (35)
        assert len(result.columns) > 0
        assert "_id" in result.columns
        assert "name" in result.columns
        assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_execute_query_find_with_projection(self, nosql_provider, setup_test_database):
        """Test query execution with projection"""
        query = json.dumps(
            {
                "collection": "test_customers",
                "operation": "find",
                "filter": {},
                "projection": {"name": 1, "email": 1},
            }
        )

        result = await nosql_provider.execute_query(query)

        assert result.success
        assert result.row_count == 3
        # Projection should limit columns
        assert "name" in result.columns
        assert "email" in result.columns or "_id" in result.columns

    @pytest.mark.asyncio
    async def test_execute_query_find_with_sort(self, nosql_provider, setup_test_database):
        """Test query execution with sort"""
        query = json.dumps(
            {
                "collection": "test_customers",
                "operation": "find",
                "filter": {},
                "sort": [("age", -1)],  # Sort by age descending
            }
        )

        result = await nosql_provider.execute_query(query)

        assert result.success
        assert result.row_count == 3
        # First row should be Charlie (age 35)
        first_row = result.sample_rows[0]
        assert first_row["name"] == "Charlie Brown"

    @pytest.mark.asyncio
    async def test_execute_query_find_one(self, nosql_provider, setup_test_database):
        """Test query execution with find_one operation"""
        query = json.dumps(
            {
                "collection": "test_customers",
                "operation": "find_one",
                "filter": {"name": "Alice Smith"},
            }
        )

        result = await nosql_provider.execute_query(query)

        assert result.success
        assert result.row_count == 1
        assert result.sample_rows[0]["name"] == "Alice Smith"
        assert result.sample_rows[0]["email"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_execute_query_aggregate(self, nosql_provider, setup_test_database):
        """Test query execution with aggregation pipeline"""
        query = json.dumps(
            {
                "collection": "test_orders",
                "operation": "aggregate",
                "pipeline": [
                    {
                        "$group": {
                            "_id": "$status",
                            "total_amount": {"$sum": "$amount"},
                            "count": {"$sum": 1},
                        }
                    }
                ],
            }
        )

        result = await nosql_provider.execute_query(query)

        assert result.success
        assert result.row_count == 2  # completed and pending
        assert "total_amount" in result.columns
        assert "count" in result.columns

    @pytest.mark.asyncio
    async def test_execute_query_count_documents(self, nosql_provider, setup_test_database):
        """Test query execution with count_documents operation"""
        query = json.dumps(
            {
                "collection": "test_customers",
                "operation": "count_documents",
                "filter": {"age": {"$gt": 25}},
            }
        )

        result = await nosql_provider.execute_query(query)

        assert result.success
        assert result.row_count == 1
        assert result.sample_rows[0]["count"] == 2  # Alice and Charlie

    @pytest.mark.asyncio
    async def test_execute_query_distinct(self, nosql_provider, setup_test_database):
        """Test query execution with distinct operation"""
        query = json.dumps(
            {"collection": "test_orders", "operation": "distinct", "field": "status"}
        )

        result = await nosql_provider.execute_query(query)

        assert result.success
        assert result.row_count == 2  # completed and pending
        assert "status" in result.columns

    @pytest.mark.asyncio
    async def test_execute_query_with_limit(self, nosql_provider, setup_test_database):
        """Test query execution with limit"""
        query = json.dumps({"collection": "test_customers", "operation": "find", "filter": {}})

        result = await nosql_provider.execute_query(query, limit=2)

        assert result.success
        assert result.row_count <= 2

    @pytest.mark.asyncio
    async def test_execute_query_error(self, nosql_provider, setup_test_database):
        """Test query execution with error"""
        query = json.dumps(
            {
                "collection": "test_customers",
                "operation": "find",
                "filter": {"$invalid": "operator"},
            }
        )

        result = await nosql_provider.execute_query(query)

        assert not result.success
        assert result.error is not None

    def test_flatten_document(self):
        """Test document flattening for schema inference"""
        # Create a provider just for this test
        provider = NoSQLProvider(TEST_CONFIG)

        doc = {
            "name": "John",
            "age": 30,
            "address": {"city": "New York", "zip": "10001"},
            "tags": ["tag1", "tag2"],
        }

        flattened = provider._flatten_document(doc)

        assert "name" in flattened
        assert "age" in flattened
        assert "address.city" in flattened
        assert "address.zip" in flattened
        assert "tags" in flattened

    @pytest.mark.asyncio
    async def test_nested_schema_structure(self, nosql_provider):
        """Test that nested documents return proper hierarchical structure"""
        client = AsyncIOMotorClient(TEST_CONFIG.get_connection_string())
        db = client[TEST_CONFIG.database]

        # Create test collection with nested documents
        await db.test_nested.drop()
        await db.test_nested.insert_many(
            [
                {
                    "_id": "nested1",
                    "level1": "value1",
                    "metadata": {
                        "request_id": "req-001",
                        "user": {"id": "user-123", "name": "Alice"},
                    },
                    "tags": ["tag1", "tag2"],
                },
                {
                    "_id": "nested2",
                    "level1": "value2",
                    "metadata": {
                        "request_id": "req-002",
                        "user": {"id": "user-456", "email": "alice@example.com"},
                        "optional_field": "present",
                    },
                    "tags": [],
                },
            ]
        )

        try:
            schema = await nosql_provider.get_schema(force_refresh=True)
            nested_table = next((t for t in schema.tables if t.name == "test_nested"), None)

            assert nested_table is not None, "test_nested collection not found"

            # Check that we have the top-level columns with nested structure
            col_names = [c.name for c in nested_table.columns]
            assert "_id" in col_names
            assert "level1" in col_names
            assert "metadata" in col_names
            assert "tags" in col_names

            # Find metadata column and verify it has nested structure
            metadata_col = next((c for c in nested_table.columns if c.name == "metadata"), None)
            assert metadata_col is not None, "metadata column not found"
            assert metadata_col.type == "Object", f"Expected Object type, got {metadata_col.type}"
            assert metadata_col.nested is not None, "metadata should have nested columns"

            # Check nested fields in metadata
            nested_names = [c.name for c in metadata_col.nested]
            assert "request_id" in nested_names, f"request_id not in {nested_names}"
            assert "user" in nested_names, f"user not in {nested_names}"

            # Find user column inside metadata and verify it has nested structure
            user_col = next((c for c in metadata_col.nested if c.name == "user"), None)
            assert user_col is not None, "user column not found in metadata"
            assert user_col.type == "Object", f"Expected Object type for user, got {user_col.type}"
            assert user_col.nested is not None, "user should have nested columns"

            user_nested_names = [c.name for c in user_col.nested]
            assert "id" in user_nested_names, f"id not in {user_nested_names}"
            assert "name" in user_nested_names or "email" in user_nested_names

        finally:
            await db.test_nested.drop()
            client.close()

    def test_get_bson_type(self):
        """Test BSON type detection"""
        provider = NoSQLProvider(TEST_CONFIG)

        assert provider._get_bson_type("string") == "String"
        assert provider._get_bson_type(123) == "Int32"
        assert provider._get_bson_type(123.45) == "Double"
        assert provider._get_bson_type(True) == "Boolean"
        assert provider._get_bson_type(None) == "Null"
        assert provider._get_bson_type({}) == "Object"
        assert provider._get_bson_type([]) == "Array"


class TestNoSQLProviderFactory:
    """Test NoSQL provider factory function"""

    @pytest.mark.asyncio
    async def test_create_nosql_provider(self):
        """Test factory function"""
        provider = create_nosql_provider(
            connection_string="mongodb://localhost:27017",
            database="text2x_test",
        )

        assert provider is not None
        assert provider.get_provider_id() == "nosql_mongodb"

        await provider.close()


class TestMongoDBConnectionConfiguration:
    """Test MongoDB connection configuration"""

    def test_connection_string_basic(self):
        """Test basic connection string generation"""
        config = MongoDBConnectionConfig(
            connection_string="mongodb://localhost:27017",
            database="testdb",
        )

        conn_str = config.get_connection_string()
        assert "mongodb://" in conn_str
        assert "localhost:27017" in conn_str

    def test_connection_string_with_auth(self):
        """Test connection string with authentication"""
        config = MongoDBConnectionConfig(
            connection_string="mongodb://localhost:27017",
            database="testdb",
            username="user",
            password="pass",
        )

        conn_str = config.get_connection_string()
        assert "user:pass@" in conn_str
        assert "authSource=" in conn_str

    def test_connection_string_with_replica_set(self):
        """Test connection string with replica set"""
        config = MongoDBConnectionConfig(
            connection_string="mongodb://localhost:27017",
            database="testdb",
            username="user",
            password="pass",
            replica_set="rs0",
        )

        conn_str = config.get_connection_string()
        assert "replicaSet=rs0" in conn_str

    def test_connection_string_with_tls(self):
        """Test connection string with TLS"""
        config = MongoDBConnectionConfig(
            connection_string="mongodb://localhost:27017",
            database="testdb",
            username="user",
            password="pass",
            tls=True,
            tls_ca_file="/path/to/ca.pem",
        )

        conn_str = config.get_connection_string()
        assert "tls=true" in conn_str
        assert "tlsCAFile=" in conn_str

    def test_connection_string_with_extra_params(self):
        """Test connection string with extra parameters"""
        config = MongoDBConnectionConfig(
            connection_string="mongodb://localhost:27017",
            database="testdb",
            username="user",
            password="pass",
            extra_params={"retryWrites": "true", "w": "majority"},
        )

        conn_str = config.get_connection_string()
        assert "retryWrites=true" in conn_str
        assert "w=majority" in conn_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
