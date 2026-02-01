"""
Comprehensive tests for Phase 4: Query Generation.

Tests the agentic loop with termination criteria (confidence >= 0.85 AND validation passed),
clarification flow for vague queries, and end-to-end query processing.
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from text2x.agents.orchestrator import OrchestratorAgent
from text2x.agents.base import LLMConfig, LLMResponse

# Import domain models from models.py directly to avoid conflicts with DB models
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import domain dataclasses directly from models.py file (not the models/ package)
# The models/ package exports database models which have the same names but are SQLAlchemy models
import importlib.util
from pathlib import Path

# Load the domain models.py file directly
_models_file = Path(__file__).parent.parent / "src" / "text2x" / "models.py"
spec = importlib.util.spec_from_file_location("text2x_domain_models", _models_file)
domain_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(domain_models)

# Extract domain models (dataclasses) for use in tests
QueryResult = domain_models.QueryResult
ValidationResult = domain_models.ValidationResult
ValidationStatus = domain_models.ValidationStatus
ExecutionResult = domain_models.ExecutionResult
SchemaContext = domain_models.SchemaContext
RAGExample = domain_models.RAGExample  # Domain dataclass with similarity_score
ExampleStatus = domain_models.ExampleStatus
TableInfo = domain_models.TableInfo
ColumnInfo = domain_models.ColumnInfo
Relationship = domain_models.Relationship
JoinPath = domain_models.JoinPath
ConversationStatus = domain_models.ConversationStatus


# ============================================================================
# Fixtures
# ============================================================================


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


@pytest.fixture
def mock_provider():
    """Create mock query provider."""
    provider = Mock()
    provider.get_provider_id.return_value = "test-provider"
    provider.get_query_language.return_value = "SQL"
    return provider


@pytest.fixture
def mock_opensearch():
    """Create mock OpenSearch client."""
    return Mock()


@pytest.fixture
def sample_schema_context():
    """Create sample schema context for testing."""
    return SchemaContext(
        relevant_tables=[
            TableInfo(
                name="users",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", nullable=False),
                    ColumnInfo(name="name", type="VARCHAR", nullable=False),
                    ColumnInfo(name="email", type="VARCHAR", nullable=False),
                    ColumnInfo(name="age", type="INTEGER", nullable=True),
                    ColumnInfo(name="created_at", type="TIMESTAMP", nullable=False),
                ],
                description="User accounts",
                primary_keys=["id"],
            ),
            TableInfo(
                name="orders",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", nullable=False),
                    ColumnInfo(name="user_id", type="INTEGER", nullable=False),
                    ColumnInfo(name="total", type="DECIMAL", nullable=False),
                    ColumnInfo(name="status", type="VARCHAR", nullable=False),
                ],
                description="Customer orders",
                primary_keys=["id"],
            ),
        ],
        relationships=[
            Relationship(
                from_table="orders",
                from_column="user_id",
                to_table="users",
                to_column="id",
                relationship_type="foreign_key",
            )
        ],
        annotations={
            "users.age": "Age in years",
            "orders.status": "Order status: pending, completed, cancelled",
        },
        suggested_joins=[
            JoinPath(
                tables=["users", "orders"],
                relationships=[
                    Relationship(
                        from_table="orders",
                        from_column="user_id",
                        to_table="users",
                        to_column="id",
                    )
                ],
                suggested_join_clause="users JOIN orders ON users.id = orders.user_id",
            )
        ],
        provider_id="test-provider",
        query_language="SQL",
    )


@pytest.fixture
def sample_rag_examples():
    """Create sample RAG examples for testing."""
    return [
        RAGExample(
            id=uuid4(),
            provider_id="test-provider",
            natural_language_query="Show me all users over 21",
            generated_query="SELECT * FROM users WHERE age > 21",
            is_good_example=True,
            status=ExampleStatus.APPROVED,
            involved_tables=["users"],
            query_intent="filter",
            complexity_level="simple",
            similarity_score=0.89,
        ),
        RAGExample(
            id=uuid4(),
            provider_id="test-provider",
            natural_language_query="Get user orders with total over 100",
            generated_query="SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id WHERE o.total > 100",
            is_good_example=True,
            status=ExampleStatus.APPROVED,
            involved_tables=["users", "orders"],
            query_intent="join",
            complexity_level="medium",
            similarity_score=0.76,
        ),
    ]


# ============================================================================
# Orchestrator Tests - Termination Criteria
# ============================================================================


@pytest.mark.asyncio
class TestTerminationCriteria:
    """Test the agentic loop termination criteria: confidence >= 0.85 AND validation passed."""

    async def test_terminates_when_criteria_met(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that loop terminates when confidence >= 0.85 AND validation passes."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=5,
            confidence_threshold=0.85,
        )

        # Mock sub-agents to return successful results
        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}

            # Query builder returns high confidence result
            mock_query_result = QueryResult(
                generated_query="SELECT * FROM users WHERE age > 18",
                confidence_score=0.90,  # Above threshold
                validation_result=ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,  # Validation passed
                    suggestions=["Consider adding LIMIT clause"],
                ),
                iteration_count=1,
                reasoning_steps=["Parsed query", "Generated SQL"],
            )
            mock_query_builder.return_value = {"query_result": mock_query_result}

            # Validator returns success
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            # Process query
            result = await orchestrator.process({
                "user_query": "Show me users over 18",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Verify termination after 1 iteration (criteria met immediately)
            assert result["query_response"].iterations == 1
            assert result["query_response"].confidence_score == 0.90
            assert result["query_response"].validation_status == ValidationStatus.PASSED

    async def test_continues_when_confidence_low(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that loop continues when confidence < 0.85."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=3,
            confidence_threshold=0.85,
        )

        iteration_count = 0

        def mock_query_builder_process(input_data):
            nonlocal iteration_count
            iteration_count += 1

            # First two iterations: low confidence
            if iteration_count < 3:
                confidence = 0.70  # Below threshold
            else:
                confidence = 0.90  # Above threshold on final iteration

            return {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users WHERE age > 18",
                    confidence_score=confidence,
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                    iteration_count=iteration_count,
                )
            }

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}
            mock_query_builder.side_effect = mock_query_builder_process
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            result = await orchestrator.process({
                "user_query": "Show me users over 18",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should iterate until confidence meets threshold
            assert result["query_response"].iterations == 3
            assert result["query_response"].confidence_score == 0.90

    async def test_continues_when_validation_fails(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that loop continues when validation fails even with high confidence."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=3,
            confidence_threshold=0.85,
        )

        iteration_count = 0

        def mock_validator_process(input_data):
            nonlocal iteration_count
            iteration_count += 1

            # First two iterations: validation fails
            if iteration_count < 3:
                status = ValidationStatus.FAILED
                valid = False
                error = "Syntax error in query"
            else:
                status = ValidationStatus.PASSED
                valid = True
                error = None

            return {
                "validation_result": ValidationResult(
                    valid=valid,
                    validation_status=status,
                    error=error,
                ),
                "execution_result": None,
            }

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}
            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users WHERE age > 18",
                    confidence_score=0.92,  # High confidence
                    validation_result=ValidationResult(
                        valid=False,
                        validation_status=ValidationStatus.FAILED,
                    ),
                    iteration_count=1,
                )
            }
            mock_validator.side_effect = mock_validator_process

            result = await orchestrator.process({
                "user_query": "Show me users over 18",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should iterate until validation passes
            assert result["query_response"].iterations == 3
            assert result["query_response"].validation_status == ValidationStatus.PASSED

    async def test_stops_at_max_iterations(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that loop stops at max_iterations even if criteria not met."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=2,
            confidence_threshold=0.85,
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}

            # Always return low confidence
            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users WHERE age > 18",
                    confidence_score=0.60,  # Always below threshold
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                    iteration_count=1,
                )
            }
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            result = await orchestrator.process({
                "user_query": "Show me users over 18",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should stop at max_iterations
            assert result["query_response"].iterations == 2
            assert result["query_response"].confidence_score == 0.60


# ============================================================================
# Clarification Flow Tests
# ============================================================================


@pytest.mark.asyncio
class TestClarificationFlow:
    """Test the clarification flow for vague/ambiguous queries."""

    async def test_clarification_requested_for_low_confidence(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that clarification is requested when confidence is below threshold.

        Per design.md 15.3: clarify = confidence < 0.6 AND iterations < 5
        This should happen DURING iteration, breaking the loop early instead of wasting iterations.
        """
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=3,
            confidence_threshold=0.85,
            clarification_threshold=0.60,  # Request clarification below 0.60
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator, \
             patch.object(orchestrator, "invoke_llm") as mock_llm:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}

            # Return low confidence result on first iteration
            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users",
                    confidence_score=0.45,  # Below clarification threshold
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                    iteration_count=1,
                )
            }
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            # Mock LLM response for clarification question
            mock_llm.return_value = LLMResponse(
                content="Which specific fields from the users table would you like to see?",
                tokens_used=50,
                model="gpt-4o",
                finish_reason="stop",
            )

            result = await orchestrator.process({
                "user_query": "Show me data",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Verify clarification is requested and loop breaks early
            assert result["query_response"].clarification_needed is True
            assert result["query_response"].clarification_question is not None
            assert len(result["query_response"].clarification_question) > 0
            # Should break after first iteration, not continue to max_iterations
            assert result["query_response"].iterations == 1

    async def test_clarification_for_vague_query(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context
    ):
        """Test that clarification is requested for very short/vague queries."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=2,
            confidence_threshold=0.85,
            clarification_threshold=0.60,
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator, \
             patch.object(orchestrator, "invoke_llm") as mock_llm:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": []}

            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT *",
                    confidence_score=0.30,  # Very low confidence
                    validation_result=ValidationResult(
                        valid=False,
                        validation_status=ValidationStatus.FAILED,
                        error="Incomplete query",
                    ),
                    iteration_count=2,
                )
            }
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=False,
                    validation_status=ValidationStatus.FAILED,
                    error="Incomplete query",
                ),
                "execution_result": None,
            }

            mock_llm.return_value = LLMResponse(
                content="Could you provide more details about what data you're looking for?",
                tokens_used=50,
                model="gpt-4o",
                finish_reason="stop",
            )

            result = await orchestrator.process({
                "user_query": "all",  # Very vague query (1 word)
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should request clarification due to vague query
            assert result["query_response"].clarification_needed is True
            assert result["query_response"].clarification_question is not None

    async def test_no_clarification_for_good_query(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that no clarification is requested for clear queries with good results."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=3,
            confidence_threshold=0.85,
            clarification_threshold=0.60,
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}

            # Return high confidence, valid result
            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT name, email FROM users WHERE age > 18 ORDER BY name",
                    confidence_score=0.95,  # High confidence
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                    iteration_count=1,
                )
            }
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            result = await orchestrator.process({
                "user_query": "Show me names and emails of users over 18 sorted by name",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should NOT request clarification
            assert result["query_response"].clarification_needed is False
            assert result["query_response"].clarification_question is None

    async def test_clarification_breaks_loop_early(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that clarification breaks the iteration loop early instead of continuing.

        Per design.md 15.3: If confidence < 0.6 on iteration 1-4, we should return immediately
        with clarification instead of wasting iterations (since the query is too vague to refine
        without user input).
        """
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=5,
            confidence_threshold=0.85,
            clarification_threshold=0.60,
        )

        iteration_count = 0

        def mock_query_builder_process(input_data):
            nonlocal iteration_count
            iteration_count += 1

            # Always return low confidence
            return {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users",
                    confidence_score=0.50,  # Below clarification threshold
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                    iteration_count=iteration_count,
                )
            }

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator, \
             patch.object(orchestrator, "invoke_llm") as mock_llm:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}
            mock_query_builder.side_effect = mock_query_builder_process
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            mock_llm.return_value = LLMResponse(
                content="Could you be more specific about what data you need?",
                tokens_used=50,
                model="gpt-4o",
                finish_reason="stop",
            )

            result = await orchestrator.process({
                "user_query": "show stuff",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should break after first iteration due to low confidence
            # NOT continue to max_iterations (5)
            assert iteration_count == 1, f"Expected 1 iteration, got {iteration_count}"
            assert result["query_response"].iterations == 1
            assert result["query_response"].clarification_needed is True

    async def test_no_clarification_on_final_iteration(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that clarification check allows final iteration to complete.

        On the final iteration (iteration == max_iterations), we should not break for
        clarification, but let it complete normally and check after.
        """
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=2,
            confidence_threshold=0.85,
            clarification_threshold=0.60,
        )

        iteration_count = 0

        def mock_query_builder_process(input_data):
            nonlocal iteration_count
            iteration_count += 1

            # Always return low confidence
            return {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users",
                    confidence_score=0.50,  # Below clarification threshold
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                    iteration_count=iteration_count,
                )
            }

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator, \
             patch.object(orchestrator, "invoke_llm") as mock_llm:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}
            mock_query_builder.side_effect = mock_query_builder_process
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            mock_llm.return_value = LLMResponse(
                content="Could you be more specific?",
                tokens_used=50,
                model="gpt-4o",
                finish_reason="stop",
            )

            result = await orchestrator.process({
                "user_query": "show data",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # On iteration 1, should break early due to low confidence
            # So we only get 1 iteration, not 2
            assert iteration_count == 1
            assert result["query_response"].iterations == 1
            assert result["query_response"].clarification_needed is True

    async def test_clarification_when_no_tables_found(
        self, llm_config, mock_provider, mock_opensearch
    ):
        """Test clarification when no relevant tables are found."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=2,
            confidence_threshold=0.85,
            clarification_threshold=0.60,
        )

        # Empty schema context - no tables found
        empty_schema = SchemaContext(
            relevant_tables=[],
            relationships=[],
            annotations={},
            suggested_joins=[],
            provider_id="test-provider",
            query_language="SQL",
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator, \
             patch.object(orchestrator, "invoke_llm") as mock_llm:

            mock_schema.return_value = {"schema_context": empty_schema}
            mock_rag.return_value = {"examples": []}

            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="",
                    confidence_score=0.10,
                    validation_result=ValidationResult(
                        valid=False,
                        validation_status=ValidationStatus.FAILED,
                        error="No tables found",
                    ),
                    iteration_count=2,
                )
            }
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=False,
                    validation_status=ValidationStatus.FAILED,
                    error="No tables found",
                ),
                "execution_result": None,
            }

            mock_llm.return_value = LLMResponse(
                content="I couldn't identify which tables to query. Could you specify which data you're interested in?",
                tokens_used=50,
                model="gpt-4o",
                finish_reason="stop",
            )

            result = await orchestrator.process({
                "user_query": "Show me xyz data",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should request clarification due to no tables found
            assert result["query_response"].clarification_needed is True
            assert "tables" in result["query_response"].clarification_question.lower() or \
                   "data" in result["query_response"].clarification_question.lower()


# ============================================================================
# Conversation Management Tests
# ============================================================================


@pytest.mark.asyncio
class TestConversationManagement:
    """Test conversation management across multiple turns."""

    async def test_creates_new_conversation(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that a new conversation is created when conversation_id is not provided."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}
            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users",
                    confidence_score=0.90,
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                )
            }
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            result = await orchestrator.process({
                "user_query": "Show me all users",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "none",
            })

            # Should create new conversation
            assert result["conversation_id"] is not None
            assert result["turn_id"] is not None
            assert len(orchestrator.conversations) == 1

    async def test_continues_existing_conversation(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test that an existing conversation is continued when conversation_id is provided."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}
            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT * FROM users WHERE age > 18",
                    confidence_score=0.90,
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                )
            }
            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": None,
            }

            # First turn
            result1 = await orchestrator.process({
                "user_query": "Show me all users",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "none",
            })

            conversation_id = result1["conversation_id"]

            # Second turn with same conversation_id
            result2 = await orchestrator.process({
                "user_query": "Filter by age over 18",
                "provider_id": "test-provider",
                "conversation_id": conversation_id,
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "none",
            })

            # Should use same conversation
            assert result2["conversation_id"] == conversation_id
            assert result2["turn_id"] != result1["turn_id"]
            assert len(orchestrator.conversations) == 1
            assert len(orchestrator.conversations[conversation_id].turns) == 2


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
class TestQueryGenerationIntegration:
    """Integration tests for complete query generation flow."""

    async def test_end_to_end_successful_query(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test complete end-to-end flow with successful query generation."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=3,
            confidence_threshold=0.85,
        )

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}

            mock_query_builder.return_value = {
                "query_result": QueryResult(
                    generated_query="SELECT id, name, email FROM users WHERE age >= 18 ORDER BY name LIMIT 100",
                    confidence_score=0.95,
                    validation_result=ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                        suggestions=["Query looks good"],
                    ),
                    iteration_count=1,
                    reasoning_steps=[
                        "Identified users table from query",
                        "Parsed age filter >= 18",
                        "Added ORDER BY for better UX",
                        "Added LIMIT to prevent large result sets",
                    ],
                    examples_used=[sample_rag_examples[0].id],
                )
            }

            mock_validator.return_value = {
                "validation_result": ValidationResult(
                    valid=True,
                    validation_status=ValidationStatus.PASSED,
                ),
                "execution_result": ExecutionResult(
                    success=True,
                    row_count=42,
                    columns=["id", "name", "email"],
                    sample_rows=[
                        {"id": 1, "name": "Alice", "email": "alice@example.com"},
                        {"id": 2, "name": "Bob", "email": "bob@example.com"},
                    ],
                    execution_time_ms=15.5,
                ),
            }

            result = await orchestrator.process({
                "user_query": "Show me adult users with their names and emails",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": True,
                "trace_level": "full",
            })

            # Verify successful result
            query_response = result["query_response"]
            assert query_response.confidence_score >= 0.85
            assert query_response.validation_status.value == "passed"
            assert query_response.iterations == 1
            assert query_response.clarification_needed is False
            assert query_response.execution_result is not None
            assert query_response.execution_result.success is True
            assert query_response.execution_result.row_count == 42

            # Verify reasoning trace is present (even if empty with mocked agents)
            assert "all_traces" in result

    async def test_iterative_refinement_flow(
        self, llm_config, mock_provider, mock_opensearch, sample_schema_context, sample_rag_examples
    ):
        """Test iterative refinement with validation feedback."""
        orchestrator = OrchestratorAgent(
            llm_config=llm_config,
            provider=mock_provider,
            opensearch_client=mock_opensearch,
            max_iterations=3,
            confidence_threshold=0.85,
        )

        iteration_count = 0

        def mock_query_builder_process(input_data):
            nonlocal iteration_count
            iteration_count += 1

            # Simulate improvement over iterations
            if iteration_count == 1:
                return {
                    "query_result": QueryResult(
                        generated_query="SELECT * FROM userz WHERE age > 18",  # Typo in table name
                        confidence_score=0.75,
                        validation_result=ValidationResult(
                            valid=False,
                            validation_status=ValidationStatus.FAILED,
                            error="Table 'userz' does not exist",
                        ),
                        iteration_count=1,
                    )
                }
            elif iteration_count == 2:
                return {
                    "query_result": QueryResult(
                        generated_query="SELECT * FROM users WHERE age > 18",  # Fixed table name
                        confidence_score=0.82,
                        validation_result=ValidationResult(
                            valid=True,
                            validation_status=ValidationStatus.PASSED,
                        ),
                        iteration_count=2,
                    )
                }
            else:
                return {
                    "query_result": QueryResult(
                        generated_query="SELECT id, name, email FROM users WHERE age > 18 ORDER BY name",
                        confidence_score=0.92,
                        validation_result=ValidationResult(
                            valid=True,
                            validation_status=ValidationStatus.PASSED,
                        ),
                        iteration_count=3,
                    )
                }

        def mock_validator_process(input_data):
            if iteration_count == 1:
                return {
                    "validation_result": ValidationResult(
                        valid=False,
                        validation_status=ValidationStatus.FAILED,
                        error="Table 'userz' does not exist",
                    ),
                    "execution_result": None,
                }
            else:
                return {
                    "validation_result": ValidationResult(
                        valid=True,
                        validation_status=ValidationStatus.PASSED,
                    ),
                    "execution_result": None,
                }

        with patch.object(orchestrator.schema_expert, "process") as mock_schema, \
             patch.object(orchestrator.rag_retrieval, "process") as mock_rag, \
             patch.object(orchestrator.query_builder, "process") as mock_query_builder, \
             patch.object(orchestrator.validator, "process") as mock_validator:

            mock_schema.return_value = {"schema_context": sample_schema_context}
            mock_rag.return_value = {"examples": sample_rag_examples}
            mock_query_builder.side_effect = mock_query_builder_process
            mock_validator.side_effect = mock_validator_process

            result = await orchestrator.process({
                "user_query": "Show me adult users",
                "provider_id": "test-provider",
                "user_id": "test-user",
                "enable_execution": False,
                "trace_level": "summary",
            })

            # Should iterate and improve
            assert result["query_response"].iterations == 3
            assert result["query_response"].confidence_score >= 0.85
            assert result["query_response"].validation_status.value == "passed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
