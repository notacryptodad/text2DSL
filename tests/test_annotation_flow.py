"""End-to-end tests for Scenario 2: Expert Schema Annotation flow.

Tests the complete annotation workflow including:
- Getting schema from connections
- Auto-annotation triggers
- Multi-turn annotation conversations
- Tool usage (sample_data, column_stats, save_annotation)
"""
import pytest
import pytest_asyncio
from datetime import datetime
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from text2x.agents.annotation_agent import AnnotationAgent
from text2x.agents.base import LLMConfig, LLMResponse
from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.models.workspace import (
    Workspace,
    Provider,
    Connection,
    ProviderType,
    ConnectionStatus,
)
from text2x.models.annotation import SchemaAnnotation
from text2x.providers.base import (
    QueryProvider,
    ProviderCapability,
    SchemaDefinition,
    TableInfo as ProviderTableInfo,
    ColumnInfo,
    ForeignKeyInfo,
    ExecutionResult as ProviderExecutionResult,
)
from text2x.repositories.workspace import WorkspaceRepository
from text2x.repositories.provider import ProviderRepository
from text2x.repositories.connection import ConnectionRepository
from text2x.repositories.annotation import SchemaAnnotationRepository
from text2x.services.schema_service import SchemaService
from tests.config import TEST_POSTGRES_CONFIG


# ============================================================================
# Mock Provider for Testing
# ============================================================================

class MockSQLProvider(QueryProvider):
    """Mock SQL provider with predefined schema and data."""

    def __init__(self, provider_id: str = "test-provider"):
        self._provider_id = provider_id

    def get_provider_id(self) -> str:
        return self._provider_id

    def get_query_language(self) -> str:
        return "SQL"

    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.SCHEMA_INTROSPECTION,
            ProviderCapability.QUERY_EXECUTION,
        ]

    async def get_schema(self) -> SchemaDefinition:
        """Return mock schema."""
        return SchemaDefinition(
            tables=[
                ProviderTableInfo(
                    name="users",
                    schema="public",
                    columns=[
                        ColumnInfo(name="id", type="integer", nullable=False, primary_key=True),
                        ColumnInfo(name="username", type="varchar(255)", nullable=False, unique=True),
                        ColumnInfo(name="email", type="varchar(255)", nullable=False, unique=True),
                        ColumnInfo(name="age", type="integer", nullable=True),
                        ColumnInfo(name="created_at", type="timestamp", nullable=False),
                    ],
                    primary_key=["id"],
                    comment="User account information",
                    row_count=1000,
                ),
                ProviderTableInfo(
                    name="orders",
                    schema="public",
                    columns=[
                        ColumnInfo(name="id", type="integer", nullable=False, primary_key=True),
                        ColumnInfo(name="user_id", type="integer", nullable=False),
                        ColumnInfo(name="total_amount", type="numeric(10,2)", nullable=False),
                        ColumnInfo(name="status", type="varchar(50)", nullable=False),
                        ColumnInfo(name="created_at", type="timestamp", nullable=False),
                    ],
                    primary_key=["id"],
                    foreign_keys=[
                        ForeignKeyInfo(
                            name="fk_user",
                            constrained_columns=["user_id"],
                            referred_schema="public",
                            referred_table="users",
                            referred_columns=["id"],
                        )
                    ],
                    comment="Customer orders",
                    row_count=5000,
                ),
            ],
            relationships=[],
            metadata={"database": "test_db", "version": "PostgreSQL 15.3"},
        )

    async def validate_syntax(self, query: str):
        return None

    async def execute_query(
        self, query: str, limit: int = 100
    ) -> Optional[ProviderExecutionResult]:
        """Execute mock query."""
        # Sample data queries
        if "SELECT * FROM users" in query:
            return ProviderExecutionResult(
                success=True,
                row_count=3,
                columns=["id", "username", "email", "age", "created_at"],
                sample_rows=[
                    {"id": 1, "username": "alice", "email": "alice@example.com", "age": 30, "created_at": "2024-01-01"},
                    {"id": 2, "username": "bob", "email": "bob@example.com", "age": 25, "created_at": "2024-01-02"},
                    {"id": 3, "username": "charlie", "email": "charlie@example.com", "age": 35, "created_at": "2024-01-03"},
                ],
            )
        # Column stats queries
        elif "COUNT(*)" in query and "COUNT(DISTINCT" in query:
            return ProviderExecutionResult(
                success=True,
                row_count=1,
                columns=["total_count", "distinct_count", "null_count", "non_null_percentage"],
                sample_rows=[
                    {"total_count": 1000, "distinct_count": 1000, "null_count": 0, "non_null_percentage": 100.0}
                ],
            )
        elif "SELECT DISTINCT" in query:
            return ProviderExecutionResult(
                success=True,
                row_count=3,
                columns=["email"],
                sample_rows=[
                    ["alice@example.com"],
                    ["bob@example.com"],
                    ["charlie@example.com"],
                ],
            )
        else:
            return ProviderExecutionResult(
                success=False,
                error=f"Query not supported in mock: {query}"
            )


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def setup_db():
    """Set up test database."""
    config = DatabaseConfig(
        host=TEST_POSTGRES_CONFIG['host'],
        port=TEST_POSTGRES_CONFIG['port'],
        database=TEST_POSTGRES_CONFIG['database'],
        user=TEST_POSTGRES_CONFIG['username'],
        password=TEST_POSTGRES_CONFIG['password'],
        echo=False,
    )

    db = init_db(config)

    # Create tables
    engine = db.engine
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS schema_annotations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))
        await conn.run_sync(Base.metadata.create_all)

    yield db

    # Cleanup
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS schema_annotations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))

    await close_db()


@pytest_asyncio.fixture
async def test_workspace(setup_db):
    """Create test workspace."""
    workspace_repo = WorkspaceRepository()
    workspace = await workspace_repo.create(
        name="Test Workspace",
        slug="test-workspace",
        description="Test workspace for annotation flow"
    )
    return workspace


@pytest_asyncio.fixture
async def test_provider(setup_db, test_workspace):
    """Create test provider."""
    provider_repo = ProviderRepository()
    provider = await provider_repo.create(
        workspace_id=test_workspace.id,
        name="Test PostgreSQL",
        type=ProviderType.POSTGRESQL,
        description="Test database"
    )
    return provider


@pytest_asyncio.fixture
async def test_connection(setup_db, test_provider):
    """Create test connection."""
    connection_repo = ConnectionRepository()
    connection = await connection_repo.create(
        provider_id=test_provider.id,
        name="Test Connection",
        host="localhost",
        port=5432,
        database="test_db",
        schema_name="public",
        credentials={"username": "test", "password": "test"},
        status=ConnectionStatus.CONNECTED,
    )
    return connection


@pytest_asyncio.fixture
def mock_provider():
    """Create mock SQL provider."""
    return MockSQLProvider()


@pytest_asyncio.fixture
def mock_schema_service(mock_provider):
    """Create schema service with mocked provider."""
    service = SchemaService()

    # Mock the _create_sql_provider method to return our mock
    async def mock_create_provider(connection, provider_type):
        return mock_provider

    service._create_sql_provider = mock_create_provider
    return service


# ============================================================================
# Schema Service Tests
# ============================================================================

@pytest.mark.asyncio
async def test_schema_service_get_schema(setup_db, test_connection, mock_schema_service):
    """Test getting schema via schema service."""
    # Get schema
    schema = await mock_schema_service.get_schema(test_connection.id)

    # Verify schema
    assert schema is not None
    assert len(schema.tables) == 2
    assert schema.tables[0].name == "users"
    assert schema.tables[1].name == "orders"
    assert len(schema.tables[0].columns) == 5
    assert schema.tables[0].comment == "User account information"


@pytest.mark.asyncio
async def test_schema_service_cache_schema(setup_db, test_connection, mock_schema_service):
    """Test caching schema."""
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_schema_service._redis_client = mock_redis

    # Get schema (which will cache it)
    schema = await mock_schema_service.get_schema(test_connection.id)

    # Verify Redis setex was called
    assert mock_redis.setex.called

    # Verify cache key format
    cache_key = mock_schema_service._make_cache_key(test_connection.id)
    assert cache_key == f"schema:{test_connection.id}"


@pytest.mark.asyncio
async def test_schema_service_invalidate_cache(setup_db, test_connection, mock_schema_service):
    """Test invalidating schema cache."""
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.delete.return_value = 1
    mock_schema_service._redis_client = mock_redis

    # Invalidate cache
    result = await mock_schema_service.invalidate_cache(test_connection.id)

    # Verify
    assert result is True
    assert mock_redis.delete.called


# ============================================================================
# Annotation Agent Tool Tests
# ============================================================================

@pytest.mark.asyncio
async def test_annotation_agent_sample_data(mock_provider):
    """Test annotation agent sample_data tool."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
    )

    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
    )

    # Test sample_data tool
    result = await agent._sample_data({
        "table_name": "users",
        "limit": 10
    })

    assert result["success"] is True
    assert result["table_name"] == "users"
    assert result["row_count"] == 3
    assert len(result["columns"]) == 5
    assert len(result["sample_rows"]) == 3

    await agent.cleanup()


@pytest.mark.asyncio
async def test_annotation_agent_column_stats(mock_provider):
    """Test annotation agent column_stats tool."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
    )

    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
    )

    # Test column_stats tool
    result = await agent._column_stats({
        "table_name": "users",
        "column_name": "email"
    })

    assert result["success"] is True
    assert result["table_name"] == "users"
    assert result["column_name"] == "email"
    assert result["total_count"] == 1000
    assert result["distinct_count"] == 1000

    await agent.cleanup()


@pytest.mark.asyncio
async def test_annotation_agent_save_annotation(setup_db, test_provider, mock_provider):
    """Test annotation agent save_annotation tool."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
    )

    annotation_repo = SchemaAnnotationRepository()

    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
        annotation_repo=annotation_repo,
    )

    # Test save_annotation tool
    result = await agent._save_annotation({
        "provider_id": str(test_provider.id),
        "user_id": "test-user",
        "table_name": "users",
        "description": "User account information",
        "business_terms": ["customers", "accounts"],
    })

    assert result["success"] is True
    assert "annotation_id" in result
    assert result["target"] == "users"
    assert result["target_type"] == "table"

    # Verify annotation was saved to database
    annotations = await annotation_repo.list_by_provider(str(test_provider.id))
    assert len(annotations) == 1
    assert annotations[0].description == "User account information"

    await agent.cleanup()


# ============================================================================
# Multi-turn Conversation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_annotation_multi_turn_conversation(setup_db, test_provider, mock_provider):
    """Test multi-turn annotation conversation."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
    )

    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
    )

    # Turn 1: Initial request
    with patch.object(
        agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="I'll help you annotate the users table. Let me sample some data first.",
            tokens_used=50,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        result1 = await agent.process({
            "user_message": "I want to annotate the users table",
            "provider_id": str(test_provider.id),
            "user_id": "test-user",
        })

    assert len(result1["conversation_history"]) == 2
    assert result1["conversation_history"][0]["role"] == "user"
    assert result1["conversation_history"][1]["role"] == "assistant"

    # Turn 2: Follow-up question
    with patch.object(
        agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="The email column contains user email addresses and appears to be unique.",
            tokens_used=40,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        result2 = await agent.process({
            "user_message": "What values does the email column have?",
            "provider_id": str(test_provider.id),
            "user_id": "test-user",
        })

    # Should maintain context from previous turn
    assert len(result2["conversation_history"]) == 4
    assert result2["conversation_history"][0]["content"] == "I want to annotate the users table"
    assert result2["conversation_history"][2]["content"] == "What values does the email column have?"

    await agent.cleanup()


@pytest.mark.asyncio
async def test_annotation_conversation_reset(mock_provider):
    """Test resetting annotation conversation."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
    )

    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
    )

    # Initial conversation
    with patch.object(
        agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="First response",
            tokens_used=30,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        await agent.process({
            "user_message": "First message",
            "provider_id": "test-provider",
            "user_id": "test-user",
        })

    assert len(agent.conversation_history) == 2

    # Reset conversation
    with patch.object(
        agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="New response",
            tokens_used=30,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        result = await agent.process({
            "user_message": "New message",
            "provider_id": "test-provider",
            "user_id": "test-user",
            "reset_conversation": True,
        })

    # Should only have new conversation
    assert len(result["conversation_history"]) == 2
    assert result["conversation_history"][0]["content"] == "New message"

    await agent.cleanup()


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_complete_annotation_workflow(setup_db, test_workspace, test_provider, test_connection, mock_schema_service):
    """Test complete annotation workflow end-to-end."""
    # Step 1: Get schema
    schema = await mock_schema_service.get_schema(test_connection.id)
    assert schema is not None
    assert len(schema.tables) == 2

    # Step 2: Create annotation agent
    llm_config = LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
    )

    mock_provider = MockSQLProvider()
    annotation_repo = SchemaAnnotationRepository()

    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
        annotation_repo=annotation_repo,
    )

    # Step 3: Sample data from table
    sample_result = await agent._sample_data({
        "table_name": "users",
        "limit": 5
    })
    assert sample_result["success"] is True

    # Step 4: Get column statistics
    stats_result = await agent._column_stats({
        "table_name": "users",
        "column_name": "email"
    })
    assert stats_result["success"] is True

    # Step 5: Save annotation
    annotation_result = await agent._save_annotation({
        "provider_id": str(test_provider.id),
        "user_id": "test-expert",
        "table_name": "users",
        "description": "User account information with login credentials",
        "business_terms": ["customers", "accounts", "users"],
        "sensitive": False,
    })
    assert annotation_result["success"] is True

    # Step 6: Verify annotation was saved
    annotations = await annotation_repo.list_by_provider(str(test_provider.id))
    assert len(annotations) == 1
    assert annotations[0].description == "User account information with login credentials"
    assert annotations[0].business_terms == ["customers", "accounts", "users"]

    await agent.cleanup()


@pytest.mark.asyncio
async def test_annotation_workflow_with_column_annotation(setup_db, test_provider, mock_provider):
    """Test annotation workflow for column-level annotations."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
    )

    annotation_repo = SchemaAnnotationRepository()

    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
        annotation_repo=annotation_repo,
    )

    # Get column stats
    stats_result = await agent._column_stats({
        "table_name": "users",
        "column_name": "email"
    })
    assert stats_result["success"] is True

    # Save column annotation
    annotation_result = await agent._save_annotation({
        "provider_id": str(test_provider.id),
        "user_id": "test-expert",
        "column_name": "users.email",
        "description": "User email address for login and communication",
        "business_terms": ["email address", "login email"],
        "sensitive": True,
        "examples": ["user@example.com"],
    })
    assert annotation_result["success"] is True

    # Verify column annotation
    annotations = await annotation_repo.list_by_provider(str(test_provider.id))
    assert len(annotations) == 1
    assert annotations[0].column_name == "users.email"
    assert annotations[0].sensitive is True

    await agent.cleanup()
