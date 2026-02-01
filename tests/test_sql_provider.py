"""Tests for SQL Provider"""
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy import create_engine, text

from text2x.providers import (
    SQLProvider,
    SQLConnectionConfig,
    create_sql_provider,
    ProviderCapability,
)
from tests.config import TEST_POSTGRES_CONFIG


# Test connection configuration - uses test containers (docker-compose.test.yml)
TEST_CONFIG = SQLConnectionConfig(**TEST_POSTGRES_CONFIG)


@pytest_asyncio.fixture
async def sql_provider():
    """Create SQL provider for testing"""
    provider = SQLProvider(TEST_CONFIG)
    yield provider
    await provider.close()


@pytest_asyncio.fixture
async def setup_test_database():
    """Setup test database with sample tables"""
    engine = create_engine(TEST_CONFIG.get_connection_string())
    
    with engine.connect() as conn:
        # Clean up any existing test tables
        conn.execute(text("DROP TABLE IF EXISTS test_orders CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS test_customers CASCADE"))
        conn.commit()
        
        # Create test tables
        conn.execute(text("""
            CREATE TABLE test_customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE test_orders (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                amount DECIMAL(10, 2),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES test_customers(id)
            )
        """))
        
        conn.execute(text("""
            CREATE INDEX idx_orders_customer ON test_orders(customer_id)
        """))
        
        # Insert test data
        conn.execute(text("""
            INSERT INTO test_customers (name, email) VALUES
                ('Alice Smith', 'alice@example.com'),
                ('Bob Jones', 'bob@example.com'),
                ('Charlie Brown', 'charlie@example.com')
        """))
        
        conn.execute(text("""
            INSERT INTO test_orders (customer_id, amount, status) VALUES
                (1, 100.50, 'completed'),
                (1, 200.00, 'completed'),
                (2, 150.75, 'pending'),
                (3, 300.00, 'completed')
        """))
        
        conn.commit()
    
    yield
    
    # Cleanup
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_orders CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS test_customers CASCADE"))
        conn.commit()
    
    engine.dispose()


class TestSQLProvider:
    """Test SQL Provider functionality"""
    
    def test_provider_id(self, sql_provider):
        """Test provider ID"""
        assert sql_provider.get_provider_id() == "sql_postgresql"
    
    def test_query_language(self, sql_provider):
        """Test query language"""
        assert sql_provider.get_query_language() == "SQL"
    
    def test_capabilities(self, sql_provider):
        """Test provider capabilities"""
        capabilities = sql_provider.get_capabilities()
        assert ProviderCapability.SCHEMA_INTROSPECTION in capabilities
        assert ProviderCapability.QUERY_VALIDATION in capabilities
        assert ProviderCapability.QUERY_EXECUTION in capabilities
        assert ProviderCapability.QUERY_EXPLANATION in capabilities
    
    @pytest.mark.asyncio
    async def test_get_schema(self, sql_provider, setup_test_database):
        """Test schema introspection"""
        schema = await sql_provider.get_schema()
        
        assert schema is not None
        assert len(schema.tables) >= 2  # At least our test tables
        
        # Find test_customers table
        customers_table = next(
            (t for t in schema.tables if t.name == "test_customers"), 
            None
        )
        assert customers_table is not None
        assert len(customers_table.columns) == 4  # id, name, email, created_at
        
        # Check primary key
        assert customers_table.primary_key == ["id"]
        
        # Check columns
        id_col = next((c for c in customers_table.columns if c.name == "id"), None)
        assert id_col is not None
        assert id_col.primary_key
        
        email_col = next((c for c in customers_table.columns if c.name == "email"), None)
        assert email_col is not None
        assert email_col.unique or any(idx.unique and "email" in idx.columns for idx in customers_table.indexes)
        
        # Find test_orders table
        orders_table = next(
            (t for t in schema.tables if t.name == "test_orders"),
            None
        )
        assert orders_table is not None
        
        # Check foreign key
        assert len(orders_table.foreign_keys) == 1
        fk = orders_table.foreign_keys[0]
        assert fk.referred_table == "test_customers"
        assert "customer_id" in fk.constrained_columns
        
        # Check relationships
        assert len(schema.relationships) >= 1
        rel = next((r for r in schema.relationships if r.from_table == "test_orders"), None)
        assert rel is not None
        assert rel.to_table == "test_customers"
    
    @pytest.mark.asyncio
    async def test_validate_syntax_valid(self, sql_provider, setup_test_database):
        """Test syntax validation with valid query"""
        query = "SELECT * FROM test_customers WHERE id = 1"
        result = await sql_provider.validate_syntax(query)
        
        assert result.valid
        assert result.error is None
        assert result.validation_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_validate_syntax_invalid(self, sql_provider, setup_test_database):
        """Test syntax validation with invalid query"""
        query = "SELECT * FORM test_customers"  # Typo: FORM instead of FROM
        result = await sql_provider.validate_syntax(query)
        
        assert not result.valid
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_validate_syntax_dangerous(self, sql_provider, setup_test_database):
        """Test syntax validation with dangerous query"""
        query = "DELETE FROM test_customers"  # No WHERE clause
        result = await sql_provider.validate_syntax(query)
        
        # Should have warning
        assert len(result.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_execute_query_select(self, sql_provider, setup_test_database):
        """Test query execution with SELECT"""
        query = "SELECT * FROM test_customers ORDER BY id"
        result = await sql_provider.execute_query(query)
        
        assert result.success
        assert result.row_count == 3
        assert len(result.columns) == 4
        assert len(result.sample_rows) == 3
        assert result.execution_time_ms is not None
        
        # Check first row
        first_row = result.sample_rows[0]
        assert first_row["name"] == "Alice Smith"
        assert first_row["email"] == "alice@example.com"
    
    @pytest.mark.asyncio
    async def test_execute_query_with_limit(self, sql_provider, setup_test_database):
        """Test query execution with LIMIT"""
        query = "SELECT * FROM test_customers"
        result = await sql_provider.execute_query(query, limit=2)
        
        assert result.success
        assert result.row_count <= 2
    
    @pytest.mark.asyncio
    async def test_execute_query_join(self, sql_provider, setup_test_database):
        """Test query execution with JOIN"""
        query = """
            SELECT c.name, COUNT(o.id) as order_count, SUM(o.amount) as total_amount
            FROM test_customers c
            LEFT JOIN test_orders o ON c.id = o.customer_id
            GROUP BY c.name
            ORDER BY c.name
        """
        result = await sql_provider.execute_query(query)
        
        assert result.success
        assert result.row_count == 3
        assert "name" in result.columns
        assert "order_count" in result.columns
        assert "total_amount" in result.columns
    
    @pytest.mark.asyncio
    async def test_execute_query_error(self, sql_provider, setup_test_database):
        """Test query execution with error"""
        query = "SELECT * FROM nonexistent_table"
        result = await sql_provider.execute_query(query)
        
        assert not result.success
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_explain_query(self, sql_provider, setup_test_database):
        """Test query explanation"""
        query = "SELECT * FROM test_customers WHERE id = 1"
        plan = await sql_provider.explain_query(query)
        
        assert plan is not None
        assert len(plan) > 0
        # PostgreSQL EXPLAIN output should contain some keywords
        assert any(keyword in plan.upper() for keyword in ["SEQ SCAN", "INDEX SCAN", "COST"])
    
    @pytest.mark.asyncio
    async def test_ensure_limit(self, sql_provider):
        """Test LIMIT clause addition"""
        query = "SELECT * FROM test_customers"
        safe_query = sql_provider._ensure_limit(query, 10)
        
        assert "LIMIT 10" in safe_query
        
        # Query with existing LIMIT should not be modified
        query_with_limit = "SELECT * FROM test_customers LIMIT 5"
        safe_query = sql_provider._ensure_limit(query_with_limit, 10)
        
        assert "LIMIT 5" in safe_query
        assert "LIMIT 10" not in safe_query


class TestSQLProviderFactory:
    """Test SQL provider factory function"""
    
    @pytest.mark.asyncio
    async def test_create_sql_provider(self):
        """Test factory function"""
        provider = create_sql_provider(
            host="localhost",
            port=5432,
            database="text2x",
            username="text2x",
            password="text2x",
        )
        
        assert provider is not None
        assert provider.get_provider_id() == "sql_postgresql"
        
        await provider.close()


class TestConnectionConfiguration:
    """Test SQL connection configuration"""
    
    def test_connection_string_basic(self):
        """Test basic connection string generation"""
        config = SQLConnectionConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
            dialect="postgresql",
        )
        
        conn_str = config.get_connection_string()
        assert "postgresql://" in conn_str
        assert "localhost:5432" in conn_str
        assert "testdb" in conn_str
    
    def test_connection_string_with_driver(self):
        """Test connection string with driver"""
        config = SQLConnectionConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
            dialect="postgresql",
            driver="psycopg2",
        )
        
        conn_str = config.get_connection_string()
        assert "postgresql+psycopg2://" in conn_str
    
    def test_connection_string_with_params(self):
        """Test connection string with extra parameters"""
        config = SQLConnectionConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
            dialect="postgresql",
            extra_params={"sslmode": "require", "connect_timeout": "10"},
        )
        
        conn_str = config.get_connection_string()
        assert "sslmode=require" in conn_str
        assert "connect_timeout=10" in conn_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
