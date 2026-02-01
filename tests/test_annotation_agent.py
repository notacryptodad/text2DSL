"""Tests for AnnotationAgent.

Tests the annotation agent's ability to help experts annotate schemas
with multi-turn chat support and tool usage.
"""
import pytest
import pytest_asyncio
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Import annotation agent directly without going through agents package
# to avoid import issues with models.py vs models/ naming conflict
import text2x.agents.annotation_agent
from text2x.agents.annotation_agent import AnnotationAgent
from text2x.agents.base import LLMConfig, LLMResponse
from text2x.models.annotation import SchemaAnnotation
from text2x.providers.base import (
    QueryProvider,
    ProviderCapability,
    ExecutionResult as ProviderExecutionResult,
)
from text2x.repositories.annotation import SchemaAnnotationRepository


# ============================================================================
# Mock Provider
# ============================================================================

class MockQueryProvider(QueryProvider):
    """Mock query provider for testing."""

    def __init__(self, provider_id: str = "test-provider"):
        self._provider_id = provider_id
        self._execution_results = {}

    def get_provider_id(self) -> str:
        return self._provider_id

    def get_query_language(self) -> str:
        return "SQL"

    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.SCHEMA_INTROSPECTION,
            ProviderCapability.QUERY_EXECUTION,
        ]

    async def get_schema(self):
        return None

    async def validate_syntax(self, query: str):
        return None

    async def execute_query(
        self, query: str, limit: int = 100
    ) -> Optional[ProviderExecutionResult]:
        """Execute mock query and return pre-configured results."""
        # Return pre-configured results based on query
        if "SELECT * FROM users" in query:
            return ProviderExecutionResult(
                success=True,
                row_count=3,
                columns=["id", "name", "email", "age"],
                sample_rows=[
                    {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
                    {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25},
                    {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35},
                ],
                execution_time_ms=10.5
            )
        elif "COUNT(*)" in query and "COUNT(DISTINCT" in query:
            # Column stats query
            return ProviderExecutionResult(
                success=True,
                row_count=1,
                columns=["total_count", "distinct_count", "null_count", "non_null_percentage"],
                sample_rows=[
                    {"total_count": 100, "distinct_count": 95, "null_count": 5, "non_null_percentage": 95.0}
                ],
                execution_time_ms=15.2
            )
        elif "SELECT DISTINCT" in query:
            # Sample distinct values query
            return ProviderExecutionResult(
                success=True,
                row_count=3,
                columns=["email"],
                sample_rows=[
                    ["alice@example.com"],
                    ["bob@example.com"],
                    ["charlie@example.com"],
                ],
                execution_time_ms=8.3
            )
        else:
            return ProviderExecutionResult(
                success=False,
                error="Query not supported in mock"
            )


# ============================================================================
# Mock Repository
# ============================================================================

class MockAnnotationRepository:
    """Mock annotation repository for testing."""

    def __init__(self):
        self.annotations = []

    async def create(
        self,
        provider_id: str,
        description: str,
        created_by: str,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        business_terms: Optional[List[str]] = None,
        examples: Optional[List[str]] = None,
        relationships: Optional[List[str]] = None,
        date_format: Optional[str] = None,
        enum_values: Optional[List[str]] = None,
        sensitive: bool = False,
    ) -> SchemaAnnotation:
        """Create mock annotation."""
        annotation = SchemaAnnotation(
            id=uuid4(),
            provider_id=provider_id,
            table_name=table_name,
            column_name=column_name,
            description=description,
            created_by=created_by,
            business_terms=business_terms,
            examples=examples,
            relationships=relationships,
            date_format=date_format,
            enum_values=enum_values,
            sensitive=sensitive,
        )
        self.annotations.append(annotation)
        return annotation


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_provider():
    """Create mock query provider."""
    return MockQueryProvider()


@pytest.fixture
def mock_annotation_repo():
    """Create mock annotation repository."""
    return MockAnnotationRepository()


@pytest.fixture
def llm_config():
    """Create LLM config for testing."""
    return LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
        temperature=0.3,
        max_tokens=2048,
    )


@pytest_asyncio.fixture
async def annotation_agent(llm_config, mock_provider, mock_annotation_repo):
    """Create annotation agent with mocks."""
    agent = AnnotationAgent(
        llm_config=llm_config,
        provider=mock_provider,
        annotation_repo=mock_annotation_repo
    )
    yield agent
    await agent.cleanup()


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_agent_initialization(annotation_agent):
    """Test that agent initializes correctly."""
    assert annotation_agent.agent_name == "AnnotationAgent"
    assert len(annotation_agent.tools) == 3
    assert "sample_data" in annotation_agent.tools
    assert "column_stats" in annotation_agent.tools
    assert "save_annotation" in annotation_agent.tools
    assert len(annotation_agent.conversation_history) == 0


@pytest.mark.asyncio
async def test_sample_data_tool(annotation_agent, mock_provider):
    """Test sample_data tool functionality."""
    result = await annotation_agent._sample_data({
        "table_name": "users",
        "limit": 10
    })

    assert result["success"] is True
    assert result["table_name"] == "users"
    assert result["row_count"] == 3
    assert len(result["columns"]) == 4
    assert len(result["sample_rows"]) == 3
    assert result["sample_rows"][0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_sample_data_missing_table(annotation_agent):
    """Test sample_data with missing table_name."""
    result = await annotation_agent._sample_data({})

    assert "error" in result
    assert "table_name is required" in result["error"]


@pytest.mark.asyncio
async def test_column_stats_tool(annotation_agent, mock_provider):
    """Test column_stats tool functionality."""
    result = await annotation_agent._column_stats({
        "table_name": "users",
        "column_name": "email"
    })

    assert result["success"] is True
    assert result["table_name"] == "users"
    assert result["column_name"] == "email"
    assert result["total_count"] == 100
    assert result["distinct_count"] == 95
    assert result["null_count"] == 5
    assert result["non_null_percentage"] == 95.0
    assert len(result["sample_values"]) == 3


@pytest.mark.asyncio
async def test_column_stats_missing_params(annotation_agent):
    """Test column_stats with missing parameters."""
    result = await annotation_agent._column_stats({"table_name": "users"})

    assert "error" in result
    assert "table_name and column_name are required" in result["error"]


@pytest.mark.asyncio
async def test_save_annotation_table_level(annotation_agent, mock_annotation_repo):
    """Test save_annotation for table-level annotation."""
    result = await annotation_agent._save_annotation({
        "provider_id": "test-provider",
        "user_id": "test-user",
        "table_name": "users",
        "description": "User account information",
        "business_terms": ["customers", "accounts"],
        "examples": ["Contains user login and profile data"],
    })

    assert result["success"] is True
    assert "annotation_id" in result
    assert result["target"] == "users"
    assert result["target_type"] == "table"
    assert len(mock_annotation_repo.annotations) == 1

    annotation = mock_annotation_repo.annotations[0]
    assert annotation.table_name == "users"
    assert annotation.description == "User account information"
    assert annotation.business_terms == ["customers", "accounts"]


@pytest.mark.asyncio
async def test_save_annotation_column_level(annotation_agent, mock_annotation_repo):
    """Test save_annotation for column-level annotation."""
    result = await annotation_agent._save_annotation({
        "provider_id": "test-provider",
        "user_id": "test-user",
        "column_name": "users.email",
        "description": "User email address",
        "sensitive": True,
        "examples": ["alice@example.com"],
    })

    assert result["success"] is True
    assert result["target"] == "users.email"
    assert result["target_type"] == "column"
    assert len(mock_annotation_repo.annotations) == 1

    annotation = mock_annotation_repo.annotations[0]
    assert annotation.column_name == "users.email"
    assert annotation.description == "User email address"
    assert annotation.sensitive is True


@pytest.mark.asyncio
async def test_save_annotation_missing_description(annotation_agent):
    """Test save_annotation with missing description."""
    result = await annotation_agent._save_annotation({
        "provider_id": "test-provider",
        "user_id": "test-user",
        "table_name": "users",
    })

    assert "error" in result
    assert "description is required" in result["error"]


@pytest.mark.asyncio
async def test_save_annotation_missing_target(annotation_agent):
    """Test save_annotation with no table or column specified."""
    result = await annotation_agent._save_annotation({
        "provider_id": "test-provider",
        "user_id": "test-user",
        "description": "Some description",
    })

    assert "error" in result
    assert "Either table_name or column_name must be provided" in result["error"]


@pytest.mark.asyncio
async def test_save_annotation_both_targets(annotation_agent):
    """Test save_annotation with both table and column specified."""
    result = await annotation_agent._save_annotation({
        "provider_id": "test-provider",
        "user_id": "test-user",
        "table_name": "users",
        "column_name": "users.email",
        "description": "Some description",
    })

    assert "error" in result
    assert "Cannot specify both table_name and column_name" in result["error"]


@pytest.mark.asyncio
async def test_process_basic_conversation(annotation_agent):
    """Test basic conversation processing."""
    # Mock LLM response
    with patch.object(
        annotation_agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="Hello! I'm here to help you annotate your database schema. What would you like to work on?",
            tokens_used=50,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        result = await annotation_agent.process({
            "user_message": "Hello, I need help annotating my database",
            "provider_id": "test-provider",
            "user_id": "test-user"
        })

    assert "response" in result
    assert "conversation_history" in result
    assert len(result["conversation_history"]) == 2  # User + assistant
    assert result["conversation_history"][0]["role"] == "user"
    assert result["conversation_history"][1]["role"] == "assistant"
    assert len(result["tool_calls"]) == 0


@pytest.mark.asyncio
async def test_process_with_tool_call(annotation_agent):
    """Test conversation with tool call."""
    # Mock LLM responses
    llm_responses = [
        # First response: request to use tool
        LLMResponse(
            content='Let me sample the data for you.\n```json\n{"tool": "sample_data", "parameters": {"table_name": "users", "limit": 5}}\n```',
            tokens_used=100,
            model="gpt-4o",
            finish_reason="stop"
        ),
        # Second response: after tool execution
        LLMResponse(
            content="I've sampled 3 rows from the users table. The table has 4 columns: id, name, email, and age. Would you like to create an annotation for this table?",
            tokens_used=80,
            model="gpt-4o",
            finish_reason="stop"
        ),
    ]

    with patch.object(
        annotation_agent,
        "invoke_llm",
        side_effect=llm_responses
    ):
        result = await annotation_agent.process({
            "user_message": "Can you show me sample data from the users table?",
            "provider_id": "test-provider",
            "user_id": "test-user"
        })

    assert "response" in result
    assert "tool_calls" in result
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["tool"] == "sample_data"
    assert result["tool_calls"][0]["result"]["success"] is True
    assert len(result["conversation_history"]) == 2


@pytest.mark.asyncio
async def test_multi_turn_conversation(annotation_agent):
    """Test multi-turn conversation with context."""
    # Turn 1
    with patch.object(
        annotation_agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="I'll help you with that. What table do you want to annotate?",
            tokens_used=40,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        result1 = await annotation_agent.process({
            "user_message": "I want to annotate my database",
            "provider_id": "test-provider",
            "user_id": "test-user"
        })

    assert len(result1["conversation_history"]) == 2

    # Turn 2 - should have previous context
    with patch.object(
        annotation_agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="Great choice! Let me sample the users table to understand it better.",
            tokens_used=45,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        result2 = await annotation_agent.process({
            "user_message": "The users table",
            "provider_id": "test-provider",
            "user_id": "test-user"
        })

    # Should have 4 messages now (2 from turn 1, 2 from turn 2)
    assert len(result2["conversation_history"]) == 4
    assert result2["conversation_history"][0]["content"] == "I want to annotate my database"
    assert result2["conversation_history"][2]["content"] == "The users table"


@pytest.mark.asyncio
async def test_reset_conversation(annotation_agent):
    """Test conversation reset functionality."""
    # Add some conversation history
    with patch.object(
        annotation_agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="First response",
            tokens_used=30,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        await annotation_agent.process({
            "user_message": "First message",
            "provider_id": "test-provider",
            "user_id": "test-user"
        })

    assert len(annotation_agent.conversation_history) == 2

    # Reset and start new conversation
    with patch.object(
        annotation_agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="Second response",
            tokens_used=30,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        result = await annotation_agent.process({
            "user_message": "New message after reset",
            "provider_id": "test-provider",
            "user_id": "test-user",
            "reset_conversation": True
        })

    # Should only have 2 messages (the new conversation)
    assert len(result["conversation_history"]) == 2
    assert result["conversation_history"][0]["content"] == "New message after reset"


@pytest.mark.asyncio
async def test_get_conversation_history(annotation_agent):
    """Test retrieving conversation history."""
    # Add some history
    annotation_agent.conversation_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    history = annotation_agent.get_conversation_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_reset_conversation_method(annotation_agent):
    """Test reset_conversation method."""
    # Add some history
    annotation_agent.conversation_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    assert len(annotation_agent.conversation_history) == 2

    annotation_agent.reset_conversation()

    assert len(annotation_agent.conversation_history) == 0


@pytest.mark.asyncio
async def test_reasoning_traces(annotation_agent):
    """Test that reasoning traces are created."""
    with patch.object(
        annotation_agent,
        "invoke_llm",
        return_value=LLMResponse(
            content="Test response",
            tokens_used=30,
            model="gpt-4o",
            finish_reason="stop"
        )
    ):
        await annotation_agent.process({
            "user_message": "Test message",
            "provider_id": "test-provider",
            "user_id": "test-user"
        })

    traces = annotation_agent.get_traces()
    assert len(traces) > 0
    assert traces[0].agent_name == "AnnotationAgent"
    assert traces[0].step == "process_annotation_request"
