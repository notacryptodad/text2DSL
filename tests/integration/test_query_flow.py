"""End-to-end integration tests for query generation flow."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from text2x.agents.orchestrator import OrchestratorAgent
from text2x.agents.base import LLMConfig
from text2x.models import ValidationStatus


@pytest.fixture
def sample_queries():
    """Load sample queries from fixtures."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "sample_queries.json"
    with open(fixtures_path) as f:
        return json.load(f)


@pytest.fixture
def llm_config():
    """Create LLM config for testing."""
    return LLMConfig(
        model="gpt-4o",
        api_base="https://api.openai.com/v1",
        api_key="test-key",
        temperature=0.1,
        max_tokens=4096,
    )


@pytest.mark.asyncio
class TestQueryFlowWithPostgreSQL:
    """Test end-to-end query flow with PostgreSQL."""

    async def test_simple_query_flow(
        self,
        llm_config,
        sql_provider,
        opensearch_client,
        setup_test_schema,
        sample_queries
    ):
        """Test simple query generation and validation flow."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=sql_provider,
            opensearch_client=opensearch_client,
            max_iterations=3,
            confidence_threshold=0.85,
        )

        # Find a simple query from sample_queries
        simple_query = next(q for q in sample_queries if q["difficulty"] == "simple")

        # Mock the LLM responses for query generation
        with patch.object(orchestrator.query_builder, "invoke_llm") as mock_llm:
            mock_llm.return_value.content = simple_query["sql"]

            # Mock confidence scoring
            with patch.object(orchestrator.query_builder, "_calculate_confidence") as mock_confidence:
                mock_confidence.return_value = 0.95

                result = await orchestrator.process({
                    "user_query": simple_query["question"],
                    "provider_id": sql_provider.get_provider_id(),
                    "user_id": "test-user",
                    "enable_execution": False,
                    "trace_level": "summary",
                })

        # Verify result structure
        assert result is not None
        assert "query_response" in result
        assert "conversation_id" in result

        query_response = result["query_response"]
        assert query_response.generated_query is not None
        assert query_response.confidence_score > 0

    async def test_query_with_database_validation(
        self,
        llm_config,
        sql_provider,
        opensearch_client,
        setup_test_schema,
    ):
        """Test query generation with actual database validation."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=sql_provider,
            opensearch_client=opensearch_client,
            max_iterations=2,
            confidence_threshold=0.85,
        )

        # Use a valid SQL query that should work with our test schema
        valid_query = "SELECT COUNT(*) FROM customers"

        with patch.object(orchestrator.query_builder, "invoke_llm") as mock_llm:
            mock_llm.return_value.content = valid_query

            with patch.object(orchestrator.query_builder, "_calculate_confidence") as mock_confidence:
                mock_confidence.return_value = 0.90

                result = await orchestrator.process({
                    "user_query": "How many customers do we have?",
                    "provider_id": sql_provider.get_provider_id(),
                    "user_id": "test-user",
                    "enable_execution": True,  # Enable execution
                    "trace_level": "summary",
                })

        # Verify query was validated and executed
        query_response = result["query_response"]
        assert query_response.validation_status == ValidationStatus.PASSED

        # If execution was successful, verify results
        if query_response.execution_result:
            assert query_response.execution_result.success is True
            assert query_response.execution_result.row_count >= 0

    async def test_invalid_query_validation(
        self,
        llm_config,
        sql_provider,
        opensearch_client,
        setup_test_schema,
    ):
        """Test that invalid queries are properly caught during validation."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=sql_provider,
            opensearch_client=opensearch_client,
            max_iterations=2,
            confidence_threshold=0.85,
        )

        # Use an invalid SQL query (non-existent table)
        invalid_query = "SELECT * FROM nonexistent_table"

        with patch.object(orchestrator.query_builder, "invoke_llm") as mock_llm:
            mock_llm.return_value.content = invalid_query

            with patch.object(orchestrator.query_builder, "_calculate_confidence") as mock_confidence:
                mock_confidence.return_value = 0.70

                result = await orchestrator.process({
                    "user_query": "Show me data from nonexistent table",
                    "provider_id": sql_provider.get_provider_id(),
                    "user_id": "test-user",
                    "enable_execution": False,
                    "trace_level": "summary",
                })

        # Verify validation failed
        query_response = result["query_response"]
        # Should either fail validation or request clarification
        assert (
            query_response.validation_status == ValidationStatus.FAILED or
            query_response.clarification_needed is True
        )


@pytest.mark.asyncio
class TestQueryFlowWithSampleQueries:
    """Test query flow using sample queries from fixtures."""

    async def test_multiple_sample_queries(
        self,
        llm_config,
        sql_provider,
        opensearch_client,
        setup_test_schema,
        sample_queries
    ):
        """Test processing multiple sample queries."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=sql_provider,
            opensearch_client=opensearch_client,
            max_iterations=2,
            confidence_threshold=0.85,
        )

        # Test first 5 simple queries
        simple_queries = [q for q in sample_queries if q["difficulty"] == "simple"][:5]

        results = []
        for query_data in simple_queries:
            with patch.object(orchestrator.query_builder, "invoke_llm") as mock_llm:
                mock_llm.return_value.content = query_data["sql"]

                with patch.object(orchestrator.query_builder, "_calculate_confidence") as mock_confidence:
                    mock_confidence.return_value = 0.90

                    result = await orchestrator.process({
                        "user_query": query_data["question"],
                        "provider_id": sql_provider.get_provider_id(),
                        "user_id": "test-user",
                        "enable_execution": False,
                        "trace_level": "none",
                    })

                    results.append(result)

        # Verify all queries were processed
        assert len(results) == len(simple_queries)

        for result in results:
            assert result is not None
            assert "query_response" in result
            assert result["query_response"].generated_query is not None

    async def test_complex_query_with_joins(
        self,
        llm_config,
        sql_provider,
        opensearch_client,
        setup_test_schema,
        sample_queries
    ):
        """Test complex query with joins."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=sql_provider,
            opensearch_client=opensearch_client,
            max_iterations=3,
            confidence_threshold=0.85,
        )

        # Find a complex query with joins
        complex_query = next(
            q for q in sample_queries
            if q["difficulty"] == "complex" and "JOIN" in q["sql"].upper()
        )

        with patch.object(orchestrator.query_builder, "invoke_llm") as mock_llm:
            mock_llm.return_value.content = complex_query["sql"]

            with patch.object(orchestrator.query_builder, "_calculate_confidence") as mock_confidence:
                mock_confidence.return_value = 0.88

                result = await orchestrator.process({
                    "user_query": complex_query["question"],
                    "provider_id": sql_provider.get_provider_id(),
                    "user_id": "test-user",
                    "enable_execution": False,
                    "trace_level": "full",
                })

        # Verify complex query handling
        query_response = result["query_response"]
        assert query_response.generated_query is not None
        assert "JOIN" in query_response.generated_query.upper()
        assert query_response.confidence_score >= 0.85


@pytest.mark.asyncio
class TestSchemaIntrospection:
    """Test schema introspection with PostgreSQL."""

    async def test_get_schema_metadata(
        self,
        sql_provider,
        setup_test_schema
    ):
        """Test retrieving schema metadata from PostgreSQL."""
        # Get schema definition
        schema = sql_provider.get_schema_definition(include_samples=False)

        assert schema is not None
        assert schema.tables is not None

        # Verify our test tables are present
        table_names = [table.name for table in schema.tables]
        assert "customers" in table_names
        assert "products" in table_names
        assert "orders" in table_names
        assert "order_items" in table_names

        # Verify customers table structure
        customers_table = next(t for t in schema.tables if t.name == "customers")
        column_names = [col.name for col in customers_table.columns]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names

    async def test_get_relationships(
        self,
        sql_provider,
        setup_test_schema
    ):
        """Test retrieving table relationships."""
        schema = sql_provider.get_schema_definition(include_samples=False)

        # Verify relationships exist
        assert schema.relationships is not None
        assert len(schema.relationships) > 0

        # Check for foreign key relationships
        relationship_pairs = [
            (rel.from_table, rel.to_table)
            for rel in schema.relationships
        ]

        # orders -> customers relationship should exist
        assert ("orders", "customers") in relationship_pairs


@pytest.mark.asyncio
class TestConversationFlow:
    """Test multi-turn conversation flow."""

    async def test_multi_turn_conversation(
        self,
        llm_config,
        sql_provider,
        opensearch_client,
        setup_test_schema
    ):
        """Test multiple turns in a conversation."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=sql_provider,
            opensearch_client=opensearch_client,
            max_iterations=2,
            confidence_threshold=0.85,
        )

        # First turn
        with patch.object(orchestrator.query_builder, "invoke_llm") as mock_llm:
            mock_llm.return_value.content = "SELECT * FROM customers"

            with patch.object(orchestrator.query_builder, "_calculate_confidence") as mock_confidence:
                mock_confidence.return_value = 0.90

                result1 = await orchestrator.process({
                    "user_query": "Show me all customers",
                    "provider_id": sql_provider.get_provider_id(),
                    "user_id": "test-user",
                    "enable_execution": False,
                    "trace_level": "none",
                })

        conversation_id = result1["conversation_id"]

        # Second turn - continue conversation
        with patch.object(orchestrator.query_builder, "invoke_llm") as mock_llm:
            mock_llm.return_value.content = "SELECT * FROM customers LIMIT 10"

            with patch.object(orchestrator.query_builder, "_calculate_confidence") as mock_confidence:
                mock_confidence.return_value = 0.92

                result2 = await orchestrator.process({
                    "user_query": "Only show the first 10",
                    "provider_id": sql_provider.get_provider_id(),
                    "conversation_id": conversation_id,
                    "user_id": "test-user",
                    "enable_execution": False,
                    "trace_level": "none",
                })

        # Verify conversation continuity
        assert result2["conversation_id"] == conversation_id
        assert result2["turn_id"] != result1["turn_id"]

        # Verify conversation history is maintained
        assert len(orchestrator.conversations) == 1
        assert len(orchestrator.conversations[conversation_id].turns) == 2
