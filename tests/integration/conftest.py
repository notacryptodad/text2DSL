"""Fixtures for integration tests."""
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from opensearchpy import OpenSearch

from text2x.config import Settings
from text2x.providers.sql_provider import SQLProvider, SQLConnectionConfig
from text2x.providers.base import ProviderConfig


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Get application settings for integration tests."""
    # Override with test-specific settings
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://text2x:text2x@localhost:5432/text2x")
    os.environ.setdefault("OPENSEARCH_URL", "http://localhost:9200")
    os.environ.setdefault("OPENSEARCH_USE_SSL", "false")
    os.environ.setdefault("OPENSEARCH_VERIFY_CERTS", "false")
    return Settings()


@pytest.fixture(scope="session")
def postgres_connection_config() -> SQLConnectionConfig:
    """PostgreSQL connection configuration for tests."""
    return SQLConnectionConfig(
        host="localhost",
        port=5432,
        database="text2x",
        username="text2x",
        password="text2x",
        dialect="postgresql",
        driver="psycopg2",
        pool_size=5,
        max_overflow=10,
    )


@pytest.fixture(scope="session")
def sync_postgres_engine(postgres_connection_config: SQLConnectionConfig):
    """Create synchronous PostgreSQL engine for setup/teardown."""
    engine = create_engine(postgres_connection_config.get_connection_string())
    yield engine
    engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_postgres_engine(settings: Settings):
    """Create async PostgreSQL engine for tests."""
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.database_echo,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_postgres_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for each test."""
    async_session = async_sessionmaker(
        async_postgres_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="session")
def sql_provider(postgres_connection_config: SQLConnectionConfig) -> SQLProvider:
    """Create SQL provider instance for tests."""
    provider_config = ProviderConfig(
        provider_type="sql",
        timeout_seconds=30,
    )
    provider = SQLProvider(config=postgres_connection_config, provider_config=provider_config)
    yield provider
    provider.engine.dispose()


@pytest.fixture(scope="session")
def opensearch_client(settings: Settings) -> OpenSearch:
    """Create OpenSearch client for tests."""
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_auth=None,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

    # Verify connection
    info = client.info()
    print(f"Connected to OpenSearch: {info['version']['number']}")

    yield client
    client.close()


@pytest_asyncio.fixture
async def setup_test_schema(sync_postgres_engine):
    """Setup test database schema for integration tests."""
    # Create test tables for SQL queries
    with sync_postgres_engine.connect() as conn:
        # Drop existing test tables if they exist
        conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))
        conn.commit()

        # Create customers table
        conn.execute(text("""
            CREATE TABLE customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # Create products table
        conn.execute(text("""
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                price DECIMAL(10, 2) NOT NULL,
                in_stock BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # Create orders table
        conn.execute(text("""
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(id),
                total DECIMAL(10, 2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # Create order_items table
        conn.execute(text("""
            CREATE TABLE order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL
            )
        """))

        # Insert sample data
        conn.execute(text("""
            INSERT INTO customers (name, email) VALUES
            ('Alice Johnson', 'alice@example.com'),
            ('Bob Smith', 'bob@example.com'),
            ('Charlie Brown', 'charlie@example.com')
        """))

        conn.execute(text("""
            INSERT INTO products (name, category, price, in_stock) VALUES
            ('Laptop', 'Electronics', 999.99, true),
            ('Mouse', 'Electronics', 29.99, true),
            ('Desk Chair', 'Furniture', 199.99, true),
            ('Monitor', 'Electronics', 299.99, false)
        """))

        conn.execute(text("""
            INSERT INTO orders (customer_id, total, status) VALUES
            (1, 1029.98, 'delivered'),
            (2, 199.99, 'pending'),
            (1, 299.99, 'delivered')
        """))

        conn.execute(text("""
            INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
            (1, 1, 1, 999.99),
            (1, 2, 1, 29.99),
            (2, 3, 1, 199.99),
            (3, 4, 1, 299.99)
        """))

        conn.commit()

    yield

    # Cleanup after tests
    with sync_postgres_engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS customers CASCADE"))
        conn.commit()


@pytest_asyncio.fixture
async def setup_opensearch_index(opensearch_client: OpenSearch, settings: Settings):
    """Setup OpenSearch index for testing."""
    index_name = settings.opensearch_index_examples

    # Delete index if it exists
    if opensearch_client.indices.exists(index=index_name):
        opensearch_client.indices.delete(index=index_name)

    # Create index with mappings
    opensearch_client.indices.create(
        index=index_name,
        body={
            "mappings": {
                "properties": {
                    "natural_language_query": {"type": "text"},
                    "generated_query": {"type": "text"},
                    "provider_id": {"type": "keyword"},
                    "is_good_example": {"type": "boolean"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 384,  # Default embedding dimension
                    }
                }
            }
        }
    )

    yield index_name

    # Cleanup
    if opensearch_client.indices.exists(index=index_name):
        opensearch_client.indices.delete(index=index_name)
