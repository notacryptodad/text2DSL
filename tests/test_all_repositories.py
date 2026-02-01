"""Tests for SchemaAnnotation, Conversation, RAGExample, and AuditLog Repositories.

Uses PostgreSQL test container for proper integration testing.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text

from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.models.workspace import Workspace, Provider, Connection, ProviderType, ConnectionStatus
from text2x.models.annotation import SchemaAnnotation
from text2x.models.conversation import Conversation, ConversationTurn, ConversationStatus
from text2x.models.rag import RAGExample, ExampleStatus
from text2x.models.audit import AuditLog

from text2x.repositories.annotation import SchemaAnnotationRepository
from text2x.repositories.conversation import ConversationRepository, ConversationTurnRepository
from text2x.repositories.rag import RAGExampleRepository
from text2x.repositories.audit import AuditLogRepository

from tests.config import TEST_POSTGRES_CONFIG


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def setup_db():
    """Set up the test database."""
    config = DatabaseConfig(
        host=TEST_POSTGRES_CONFIG['host'],
        port=TEST_POSTGRES_CONFIG['port'],
        database=TEST_POSTGRES_CONFIG['database'],
        user=TEST_POSTGRES_CONFIG['username'],
        password=TEST_POSTGRES_CONFIG['password'],
        echo=False,
    )
    
    db = init_db(config)
    engine = db.engine
    
    async with engine.begin() as conn:
        # Drop all tables
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rag_examples CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversation_turns CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS schema_annotations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))
        await conn.run_sync(Base.metadata.create_all)
    
    yield db
    
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rag_examples CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversation_turns CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS schema_annotations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))
    
    await close_db()


@pytest_asyncio.fixture
async def annotation_repo(setup_db):
    return SchemaAnnotationRepository()


@pytest_asyncio.fixture
async def conversation_repo(setup_db):
    return ConversationRepository()


@pytest_asyncio.fixture
async def turn_repo(setup_db):
    return ConversationTurnRepository()


@pytest_asyncio.fixture
async def rag_repo(setup_db):
    return RAGExampleRepository()


@pytest_asyncio.fixture
async def audit_repo(setup_db):
    return AuditLogRepository()


@pytest_asyncio.fixture
async def sample_connection(setup_db):
    """Create sample workspace/provider/connection for foreign key references."""
    db = get_db()
    async with db.session() as session:
        workspace = Workspace(
            id=uuid4(),
            name="Test Workspace",
            slug="test-workspace",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(workspace)
        await session.flush()
        
        provider = Provider(
            id=uuid4(),
            workspace_id=workspace.id,
            name="Test Provider",
            type=ProviderType.POSTGRESQL,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(provider)
        await session.flush()
        
        connection = Connection(
            id=uuid4(),
            provider_id=provider.id,
            name="Test Connection",
            host="localhost",
            database="testdb",
            status=ConnectionStatus.CONNECTED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(connection)
        await session.flush()
        await session.refresh(connection)
        return connection


# ============================================================================
# SchemaAnnotation Repository Tests
# ============================================================================

class TestSchemaAnnotationRepository:
    """Test SchemaAnnotationRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_table_annotation(self, annotation_repo):
        """Test creating a table-level annotation."""
        annotation = await annotation_repo.create(
            provider_id="test-provider",
            table_name="orders",
            description="Customer purchase orders",
            created_by="admin",
            business_terms=["purchases", "sales"],
            examples=["order_id", "customer_id"],
        )
        
        assert annotation is not None
        assert annotation.table_name == "orders"
        assert annotation.column_name is None
        assert annotation.description == "Customer purchase orders"
        assert "purchases" in annotation.business_terms

    @pytest.mark.asyncio
    async def test_create_column_annotation(self, annotation_repo):
        """Test creating a column-level annotation."""
        annotation = await annotation_repo.create(
            provider_id="test-provider",
            column_name="orders.status",
            description="Order fulfillment status",
            created_by="admin",
            enum_values=["pending", "shipped", "delivered"],
            sensitive=False,
        )
        
        assert annotation is not None
        assert annotation.table_name is None
        assert annotation.column_name == "orders.status"
        assert "pending" in annotation.enum_values

    @pytest.mark.asyncio
    async def test_get_by_id(self, annotation_repo):
        """Test getting annotation by ID."""
        created = await annotation_repo.create(
            provider_id="test-provider",
            table_name="customers",
            description="Customer data",
            created_by="admin",
        )
        
        fetched = await annotation_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, annotation_repo):
        """Test getting non-existent annotation."""
        result = await annotation_repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_provider(self, annotation_repo):
        """Test listing annotations by provider."""
        await annotation_repo.create(
            provider_id="provider-1",
            table_name="table1",
            description="Desc 1",
            created_by="admin",
        )
        await annotation_repo.create(
            provider_id="provider-1",
            table_name="table2",
            description="Desc 2",
            created_by="admin",
        )
        await annotation_repo.create(
            provider_id="provider-2",
            table_name="table3",
            description="Desc 3",
            created_by="admin",
        )
        
        results = await annotation_repo.list_by_provider("provider-1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_by_table(self, annotation_repo):
        """Test listing annotations for a specific table."""
        await annotation_repo.create(
            provider_id="prov",
            table_name="orders",
            description="Orders table",
            created_by="admin",
        )
        await annotation_repo.create(
            provider_id="prov",
            column_name="orders.id",
            description="Order ID",
            created_by="admin",
        )
        await annotation_repo.create(
            provider_id="prov",
            column_name="orders.status",
            description="Order status",
            created_by="admin",
        )
        
        results = await annotation_repo.list_by_table("prov", "orders")
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_update_annotation(self, annotation_repo):
        """Test updating an annotation."""
        created = await annotation_repo.create(
            provider_id="prov",
            table_name="test",
            description="Original",
            created_by="admin",
        )
        
        updated = await annotation_repo.update(
            created.id,
            description="Updated description",
            sensitive=True,
        )
        
        assert updated is not None
        assert updated.description == "Updated description"
        assert updated.sensitive is True

    @pytest.mark.asyncio
    async def test_delete_annotation(self, annotation_repo):
        """Test deleting an annotation."""
        created = await annotation_repo.create(
            provider_id="prov",
            table_name="test",
            description="To delete",
            created_by="admin",
        )
        
        result = await annotation_repo.delete(created.id)
        assert result is True
        
        fetched = await annotation_repo.get_by_id(created.id)
        assert fetched is None


# ============================================================================
# Conversation Repository Tests
# ============================================================================

class TestConversationRepository:
    """Test ConversationRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, conversation_repo, sample_connection):
        """Test creating a conversation."""
        conversation = await conversation_repo.create(
            user_id="user-123",
            connection_id=sample_connection.id,
            provider_id="test-provider",
        )
        
        assert conversation is not None
        assert conversation.user_id == "user-123"
        assert conversation.connection_id == sample_connection.id
        assert conversation.status == ConversationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_by_id(self, conversation_repo):
        """Test getting conversation by ID."""
        created = await conversation_repo.create(
            user_id="user-123",
            provider_id="test-provider",
        )
        
        fetched = await conversation_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_list_by_user(self, conversation_repo):
        """Test listing conversations by user."""
        await conversation_repo.create(user_id="user-1", provider_id="prov")
        await conversation_repo.create(user_id="user-1", provider_id="prov")
        await conversation_repo.create(user_id="user-2", provider_id="prov")
        
        results = await conversation_repo.list_by_user("user-1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_by_user_with_status_filter(self, conversation_repo):
        """Test listing conversations with status filter."""
        c1 = await conversation_repo.create(user_id="user-1", provider_id="prov")
        await conversation_repo.create(user_id="user-1", provider_id="prov")
        await conversation_repo.update_status(c1.id, ConversationStatus.COMPLETED)
        
        active = await conversation_repo.list_by_user("user-1", status=ConversationStatus.ACTIVE)
        assert len(active) == 1

    @pytest.mark.asyncio
    async def test_update_status(self, conversation_repo):
        """Test updating conversation status."""
        created = await conversation_repo.create(user_id="user-1", provider_id="prov")
        
        updated = await conversation_repo.update_status(
            created.id, ConversationStatus.COMPLETED
        )
        
        assert updated is not None
        assert updated.status == ConversationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_delete_conversation(self, conversation_repo):
        """Test deleting a conversation."""
        created = await conversation_repo.create(user_id="user-1", provider_id="prov")
        
        result = await conversation_repo.delete(created.id)
        assert result is True
        
        fetched = await conversation_repo.get_by_id(created.id)
        assert fetched is None


# ============================================================================
# ConversationTurn Repository Tests
# ============================================================================

class TestConversationTurnRepository:
    """Test ConversationTurnRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_turn(self, conversation_repo, turn_repo):
        """Test creating a conversation turn."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Show me all orders",
            generated_query="SELECT * FROM orders",
            confidence_score=0.95,
            reasoning_trace={"steps": ["analyzed", "generated"]},
        )
        
        assert turn is not None
        assert turn.turn_number == 1
        assert turn.user_input == "Show me all orders"
        assert turn.confidence_score == 0.95

    @pytest.mark.asyncio
    async def test_list_by_conversation(self, conversation_repo, turn_repo):
        """Test listing turns by conversation."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        
        await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query 1",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=2,
            user_input="Query 2",
            generated_query="SELECT 2",
            confidence_score=0.85,
            reasoning_trace={},
        )
        
        turns = await turn_repo.list_by_conversation(conversation.id)
        assert len(turns) == 2
        assert turns[0].turn_number == 1
        assert turns[1].turn_number == 2

    @pytest.mark.asyncio
    async def test_update_turn(self, conversation_repo, turn_repo):
        """Test updating a turn."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.8,
            reasoning_trace={},
        )
        
        updated = await turn_repo.update(
            turn.id,
            confidence_score=0.95,
            execution_result={"success": True, "rows": 10},
        )
        
        assert updated is not None
        assert updated.confidence_score == 0.95
        assert updated.execution_result["success"] is True


# ============================================================================
# RAGExample Repository Tests
# ============================================================================

class TestRAGExampleRepository:
    """Test RAGExampleRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_example(self, rag_repo):
        """Test creating a RAG example."""
        example = await rag_repo.create(
            provider_id="test-provider",
            natural_language_query="Show all orders from last month",
            generated_query="SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '1 month'",
            involved_tables=["orders"],
            query_intent="filter",
            complexity_level="simple",
        )
        
        assert example is not None
        assert example.provider_id == "test-provider"
        assert example.status == ExampleStatus.PENDING_REVIEW
        assert example.is_good_example is True

    @pytest.mark.asyncio
    async def test_get_by_id(self, rag_repo):
        """Test getting example by ID."""
        created = await rag_repo.create(
            provider_id="prov",
            natural_language_query="Query",
            generated_query="SELECT 1",
            involved_tables=["t1"],
            query_intent="filter",
            complexity_level="simple",
        )
        
        fetched = await rag_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_list_by_provider(self, rag_repo):
        """Test listing examples by provider."""
        await rag_repo.create(
            provider_id="prov-1",
            natural_language_query="Q1",
            generated_query="S1",
            involved_tables=["t"],
            query_intent="filter",
            complexity_level="simple",
        )
        await rag_repo.create(
            provider_id="prov-1",
            natural_language_query="Q2",
            generated_query="S2",
            involved_tables=["t"],
            query_intent="aggregation",
            complexity_level="medium",
        )
        
        results = await rag_repo.list_by_provider("prov-1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_pending_review(self, rag_repo):
        """Test listing examples pending review."""
        await rag_repo.create(
            provider_id="prov",
            natural_language_query="Q1",
            generated_query="S1",
            involved_tables=["t"],
            query_intent="filter",
            complexity_level="simple",
        )
        
        pending = await rag_repo.list_pending_review()
        assert len(pending) >= 1

    @pytest.mark.asyncio
    async def test_mark_reviewed_approved(self, rag_repo):
        """Test marking example as approved."""
        example = await rag_repo.create(
            provider_id="prov",
            natural_language_query="Q",
            generated_query="S",
            involved_tables=["t"],
            query_intent="filter",
            complexity_level="simple",
        )
        
        reviewed = await rag_repo.mark_reviewed(
            example.id,
            reviewer="expert",
            approved=True,
            notes="Looks good",
        )
        
        assert reviewed is not None
        assert reviewed.status == ExampleStatus.APPROVED
        assert reviewed.reviewed_by == "expert"

    @pytest.mark.asyncio
    async def test_mark_reviewed_with_correction(self, rag_repo):
        """Test marking example as approved with correction."""
        example = await rag_repo.create(
            provider_id="prov",
            natural_language_query="Q",
            generated_query="SELECT * FROM t",
            involved_tables=["t"],
            query_intent="filter",
            complexity_level="simple",
        )
        
        reviewed = await rag_repo.mark_reviewed(
            example.id,
            reviewer="expert",
            approved=True,
            corrected_query="SELECT id, name FROM t",
        )
        
        assert reviewed is not None
        assert reviewed.expert_corrected_query == "SELECT id, name FROM t"

    @pytest.mark.asyncio
    async def test_list_approved(self, rag_repo):
        """Test listing approved examples."""
        example = await rag_repo.create(
            provider_id="prov",
            natural_language_query="Q",
            generated_query="S",
            involved_tables=["t"],
            query_intent="filter",
            complexity_level="simple",
        )
        await rag_repo.mark_reviewed(example.id, "expert", approved=True)
        
        approved = await rag_repo.list_approved("prov")
        assert len(approved) == 1

    @pytest.mark.asyncio
    async def test_delete_example(self, rag_repo):
        """Test deleting an example."""
        example = await rag_repo.create(
            provider_id="prov",
            natural_language_query="Q",
            generated_query="S",
            involved_tables=["t"],
            query_intent="filter",
            complexity_level="simple",
        )
        
        result = await rag_repo.delete(example.id)
        assert result is True
        
        fetched = await rag_repo.get_by_id(example.id)
        assert fetched is None


# ============================================================================
# AuditLog Repository Tests
# ============================================================================

class TestAuditLogRepository:
    """Test AuditLogRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_audit_log(self, audit_repo, conversation_repo, turn_repo):
        """Test creating an audit log."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        
        audit_log = await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn.id,
            user_input="Query",
            provider_id="prov",
            schema_context_used={"tables": ["t1"]},
            final_query="SELECT 1",
            confidence_score=0.9,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=500,
            execution_success=True,
        )
        
        assert audit_log is not None
        assert audit_log.provider_id == "prov"
        assert audit_log.total_latency_ms == 500

    @pytest.mark.asyncio
    async def test_get_by_turn_id(self, audit_repo, conversation_repo, turn_repo):
        """Test getting audit log by turn ID."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn.id,
            user_input="Query",
            provider_id="prov",
            schema_context_used={},
            final_query="SELECT 1",
            confidence_score=0.9,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=500,
        )
        
        fetched = await audit_repo.get_by_turn_id(turn.id)
        assert fetched is not None
        assert fetched.turn_id == turn.id

    @pytest.mark.asyncio
    async def test_list_by_conversation(self, audit_repo, conversation_repo, turn_repo):
        """Test listing audit logs by conversation."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn1 = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Q1",
            generated_query="S1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        turn2 = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=2,
            user_input="Q2",
            generated_query="S2",
            confidence_score=0.85,
            reasoning_trace={},
        )
        
        await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn1.id,
            user_input="Q1",
            provider_id="prov",
            schema_context_used={},
            final_query="S1",
            confidence_score=0.9,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=500,
        )
        await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn2.id,
            user_input="Q2",
            provider_id="prov",
            schema_context_used={},
            final_query="S2",
            confidence_score=0.85,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=600,
        )
        
        logs = await audit_repo.list_by_conversation(conversation.id)
        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_add_agent_trace(self, audit_repo, conversation_repo, turn_repo):
        """Test adding agent trace to audit log."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        audit_log = await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn.id,
            user_input="Query",
            provider_id="prov",
            schema_context_used={},
            final_query="SELECT 1",
            confidence_score=0.9,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=500,
        )
        
        updated = await audit_repo.add_agent_trace(
            audit_log.id,
            agent_name="schema",
            trace_data={"tables_found": ["orders", "customers"]},
            latency_ms=100,
        )
        
        assert updated is not None
        assert updated.schema_agent_trace == {"tables_found": ["orders", "customers"]}
        assert updated.schema_agent_latency_ms == 100

    @pytest.mark.asyncio
    async def test_add_cost(self, audit_repo, conversation_repo, turn_repo):
        """Test adding cost to audit log."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        audit_log = await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn.id,
            user_input="Query",
            provider_id="prov",
            schema_context_used={},
            final_query="SELECT 1",
            confidence_score=0.9,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=500,
            total_tokens_input=100,
            total_tokens_output=50,
            total_cost_usd=0.001,
        )
        
        updated = await audit_repo.add_cost(
            audit_log.id,
            input_tokens=200,
            output_tokens=100,
            cost_usd=0.002,
        )
        
        assert updated is not None
        assert updated.total_tokens_input == 300
        assert updated.total_tokens_output == 150
        assert updated.total_cost_usd == pytest.approx(0.003)

    @pytest.mark.asyncio
    async def test_list_recent(self, audit_repo, conversation_repo, turn_repo):
        """Test listing recent audit logs."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn.id,
            user_input="Query",
            provider_id="prov",
            schema_context_used={},
            final_query="SELECT 1",
            confidence_score=0.9,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=500,
            execution_success=True,
        )
        
        recent = await audit_repo.list_recent(limit=10)
        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_delete_audit_log(self, audit_repo, conversation_repo, turn_repo):
        """Test deleting an audit log."""
        conversation = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conversation.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        audit_log = await audit_repo.create(
            conversation_id=conversation.id,
            turn_id=turn.id,
            user_input="Query",
            provider_id="prov",
            schema_context_used={},
            final_query="SELECT 1",
            confidence_score=0.9,
            validation_status="valid",
            model_used="claude-3",
            total_latency_ms=500,
        )
        
        result = await audit_repo.delete(audit_log.id)
        assert result is True
        
        fetched = await audit_repo.get_by_id(audit_log.id)
        assert fetched is None
