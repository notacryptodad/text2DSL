"""
End-to-end tests for Expert Review Queue (Scenario 4).

Tests the complete review workflow:
1. Auto-queueing items based on triggers
2. Processing review decisions (approve/reject/correct)
3. RAG index updates on approval
4. Priority calculation
"""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.models.conversation import Conversation, ConversationTurn, ConversationStatus
from text2x.models.rag import RAGExample, ExampleStatus
from text2x.repositories.conversation import ConversationRepository, ConversationTurnRepository
from text2x.repositories.rag import RAGExampleRepository
from text2x.services.review_service import ReviewService, ReviewTrigger, ReviewDecision
from text2x.services.rag_service import RAGService
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

    # Drop and create all tables
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS rag_examples CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS user_feedback CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversation_turns CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))
        await conn.run_sync(Base.metadata.create_all)

    yield db

    # Cleanup
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS rag_examples CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS user_feedback CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversation_turns CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))

    await close_db()


@pytest_asyncio.fixture
async def conversation_repo(setup_db):
    """Create ConversationRepository."""
    return ConversationRepository()


@pytest_asyncio.fixture
async def turn_repo(setup_db):
    """Create ConversationTurnRepository."""
    return ConversationTurnRepository()


@pytest_asyncio.fixture
async def rag_repo(setup_db):
    """Create RAGExampleRepository."""
    return RAGExampleRepository()


@pytest_asyncio.fixture
async def review_service(setup_db, rag_repo, turn_repo):
    """Create ReviewService."""
    return ReviewService(rag_repo=rag_repo, turn_repo=turn_repo)


@pytest_asyncio.fixture
async def rag_service(setup_db, rag_repo):
    """Create RAGService."""
    return RAGService(rag_repo=rag_repo)


@pytest_asyncio.fixture
async def sample_conversation(setup_db, conversation_repo):
    """Create a sample conversation."""
    return await conversation_repo.create(
        user_id="test_user",
        provider_id="postgresql",
    )


@pytest_asyncio.fixture
async def sample_turn(setup_db, turn_repo, sample_conversation):
    """Create a sample conversation turn."""
    return await turn_repo.create(
        conversation_id=sample_conversation.id,
        turn_number=1,
        user_input="Show me all orders from last month",
        generated_query="SELECT * FROM orders WHERE created_at >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')",
        confidence_score=0.65,
        reasoning_trace={
            "steps": ["schema_analysis", "query_construction"],
            "query_construction": {
                "intent": "filter",
                "complexity": "simple",
            },
        },
        validation_result={
            "is_valid": True,
            "syntax_errors": [],
        },
        schema_context={
            "relevant_tables": [
                {"name": "orders", "columns": ["id", "created_at", "total"]},
            ],
        },
    )


# ============================================================================
# Tests - Auto-Queue for Review
# ============================================================================

@pytest.mark.asyncio
async def test_auto_queue_low_confidence(
    review_service,
    rag_repo,
    sample_turn,
):
    """Test auto-queueing a low confidence query."""
    # Queue the turn for review
    example_id = await review_service.auto_queue_for_review(
        turn_id=sample_turn.id,
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        provider_id="postgresql",
    )

    assert example_id is not None

    # Verify the example was created
    example = await rag_repo.get_by_id(example_id)
    assert example is not None
    assert example.status == ExampleStatus.PENDING_REVIEW
    assert example.natural_language_query == sample_turn.user_input
    assert example.generated_query == sample_turn.generated_query
    assert example.is_good_example is True  # Low confidence is still a good example
    assert example.provider_id == "postgresql"
    assert "orders" in example.involved_tables

    # Check metadata
    assert example.extra_metadata is not None
    assert example.extra_metadata["trigger"] == "low_confidence"
    assert example.extra_metadata["original_confidence"] == 0.65
    assert str(sample_turn.id) == example.extra_metadata["turn_id"]


@pytest.mark.asyncio
async def test_auto_queue_validation_failure(
    review_service,
    rag_repo,
    turn_repo,
    sample_conversation,
):
    """Test auto-queueing a validation failure."""
    # Create a turn with validation failure
    turn = await turn_repo.create(
        conversation_id=sample_conversation.id,
        turn_number=2,
        user_input="Show invalid query",
        generated_query="INVALID SQL SYNTAX",
        confidence_score=0.85,
        reasoning_trace={"steps": []},
        validation_result={
            "is_valid": False,
            "syntax_errors": ["Syntax error near INVALID"],
        },
    )

    # Queue for review
    example_id = await review_service.auto_queue_for_review(
        turn_id=turn.id,
        trigger=ReviewTrigger.VALIDATION_FAILURE,
        provider_id="postgresql",
    )

    assert example_id is not None

    # Verify it's marked as bad example
    example = await rag_repo.get_by_id(example_id)
    assert example is not None
    assert example.is_good_example is False
    assert example.status == ExampleStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_auto_queue_negative_feedback(
    review_service,
    rag_repo,
    sample_turn,
):
    """Test auto-queueing based on negative user feedback."""
    example_id = await review_service.auto_queue_for_review(
        turn_id=sample_turn.id,
        trigger=ReviewTrigger.NEGATIVE_FEEDBACK,
        provider_id="postgresql",
    )

    assert example_id is not None

    example = await rag_repo.get_by_id(example_id)
    assert example is not None
    assert example.extra_metadata["trigger"] == "negative_feedback"


@pytest.mark.asyncio
async def test_auto_queue_nonexistent_turn(review_service):
    """Test auto-queueing a non-existent turn."""
    fake_turn_id = uuid4()
    example_id = await review_service.auto_queue_for_review(
        turn_id=fake_turn_id,
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        provider_id="postgresql",
    )

    # Should return None for non-existent turn
    assert example_id is None


# ============================================================================
# Tests - Process Review Decisions
# ============================================================================

@pytest.mark.asyncio
async def test_process_review_approve(
    review_service,
    rag_repo,
    sample_turn,
):
    """Test approving a review item."""
    # First, queue it for review
    example_id = await review_service.auto_queue_for_review(
        turn_id=sample_turn.id,
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        provider_id="postgresql",
    )

    # Approve the example
    result = await review_service.process_review_decision(
        item_id=example_id,
        decision=ReviewDecision.APPROVE,
        reviewer="expert_alice",
        notes="Looks good!",
    )

    assert result is not None
    assert result["approved"] is True
    assert result["status"] == ExampleStatus.APPROVED.value
    assert result["reviewed_by"] == "expert_alice"

    # Verify in database
    example = await rag_repo.get_by_id(example_id)
    assert example.status == ExampleStatus.APPROVED
    assert example.reviewed_by == "expert_alice"
    assert example.review_notes == "Looks good!"
    assert example.reviewed_at is not None
    assert example.expert_corrected_query is None


@pytest.mark.asyncio
async def test_process_review_reject(
    review_service,
    rag_repo,
    sample_turn,
):
    """Test rejecting a review item."""
    # Queue for review
    example_id = await review_service.auto_queue_for_review(
        turn_id=sample_turn.id,
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        provider_id="postgresql",
    )

    # Reject the example
    result = await review_service.process_review_decision(
        item_id=example_id,
        decision=ReviewDecision.REJECT,
        reviewer="expert_bob",
        notes="Query is incorrect",
    )

    assert result is not None
    assert result["approved"] is False
    assert result["status"] == ExampleStatus.REJECTED.value

    # Verify in database
    example = await rag_repo.get_by_id(example_id)
    assert example.status == ExampleStatus.REJECTED
    assert example.reviewed_by == "expert_bob"
    assert example.review_notes == "Query is incorrect"


@pytest.mark.asyncio
async def test_process_review_correct(
    review_service,
    rag_repo,
    sample_turn,
):
    """Test correcting a review item."""
    # Queue for review
    example_id = await review_service.auto_queue_for_review(
        turn_id=sample_turn.id,
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        provider_id="postgresql",
    )

    # Correct the query
    corrected_query = (
        "SELECT * FROM orders "
        "WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')"
    )

    result = await review_service.process_review_decision(
        item_id=example_id,
        decision=ReviewDecision.CORRECT,
        reviewer="expert_carol",
        corrected_query=corrected_query,
        notes="Fixed date calculation",
    )

    assert result is not None
    assert result["approved"] is True
    assert result["status"] == ExampleStatus.APPROVED.value
    assert result["query_used"] == corrected_query

    # Verify in database
    example = await rag_repo.get_by_id(example_id)
    assert example.status == ExampleStatus.APPROVED
    assert example.expert_corrected_query == corrected_query
    assert example.review_notes == "Fixed date calculation"
    assert example.get_query_for_rag() == corrected_query


@pytest.mark.asyncio
async def test_process_review_correct_without_query_fails(
    review_service,
    sample_turn,
):
    """Test that CORRECT decision requires corrected_query."""
    example_id = await review_service.auto_queue_for_review(
        turn_id=sample_turn.id,
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        provider_id="postgresql",
    )

    # Try to correct without providing corrected_query
    with pytest.raises(ValueError, match="corrected_query is required"):
        await review_service.process_review_decision(
            item_id=example_id,
            decision=ReviewDecision.CORRECT,
            reviewer="expert_dave",
        )


@pytest.mark.asyncio
async def test_process_review_nonexistent_item(review_service):
    """Test processing review for non-existent item."""
    fake_item_id = uuid4()
    result = await review_service.process_review_decision(
        item_id=fake_item_id,
        decision=ReviewDecision.APPROVE,
        reviewer="expert_eve",
    )

    # Should return None for non-existent item
    assert result is None


# ============================================================================
# Tests - Should Queue Logic
# ============================================================================

@pytest.mark.asyncio
async def test_should_queue_validation_failure(review_service):
    """Test should_queue logic for validation failures."""
    should_queue, trigger = await review_service.should_queue_for_review(
        confidence_score=0.9,
        validation_passed=False,
        has_negative_feedback=False,
    )

    assert should_queue is True
    assert trigger == ReviewTrigger.VALIDATION_FAILURE


@pytest.mark.asyncio
async def test_should_queue_negative_feedback(review_service):
    """Test should_queue logic for negative feedback."""
    should_queue, trigger = await review_service.should_queue_for_review(
        confidence_score=0.9,
        validation_passed=True,
        has_negative_feedback=True,
    )

    assert should_queue is True
    assert trigger == ReviewTrigger.NEGATIVE_FEEDBACK


@pytest.mark.asyncio
async def test_should_queue_low_confidence(review_service):
    """Test should_queue logic for low confidence."""
    should_queue, trigger = await review_service.should_queue_for_review(
        confidence_score=0.65,
        validation_passed=True,
        has_negative_feedback=False,
    )

    assert should_queue is True
    assert trigger == ReviewTrigger.LOW_CONFIDENCE


@pytest.mark.asyncio
async def test_should_queue_multiple_clarifications(review_service):
    """Test should_queue logic for multiple clarifications."""
    should_queue, trigger = await review_service.should_queue_for_review(
        confidence_score=0.8,
        validation_passed=True,
        has_negative_feedback=False,
        clarification_count=3,
    )

    assert should_queue is True
    assert trigger == ReviewTrigger.MULTIPLE_CLARIFICATIONS


@pytest.mark.asyncio
async def test_should_not_queue_high_quality(review_service):
    """Test that high quality results are not queued."""
    should_queue, trigger = await review_service.should_queue_for_review(
        confidence_score=0.9,
        validation_passed=True,
        has_negative_feedback=False,
        clarification_count=0,
    )

    assert should_queue is False
    assert trigger is None


# ============================================================================
# Tests - Priority Calculation
# ============================================================================

@pytest.mark.asyncio
async def test_priority_validation_failure(review_service):
    """Test priority for validation failures."""
    priority = await review_service.get_review_priority(
        trigger=ReviewTrigger.VALIDATION_FAILURE,
    )

    assert priority == 100  # Highest priority


@pytest.mark.asyncio
async def test_priority_negative_feedback(review_service):
    """Test priority for negative feedback."""
    priority = await review_service.get_review_priority(
        trigger=ReviewTrigger.NEGATIVE_FEEDBACK,
    )

    assert priority == 50


@pytest.mark.asyncio
async def test_priority_low_confidence(review_service):
    """Test priority for low confidence."""
    # Very low confidence (0.0) should have high priority
    priority_low = await review_service.get_review_priority(
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        confidence_score=0.0,
    )

    # Medium-low confidence (0.5) should have medium priority
    priority_medium = await review_service.get_review_priority(
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        confidence_score=0.5,
    )

    assert priority_low > priority_medium
    assert priority_low == 70
    assert 19 <= priority_medium <= 20  # Allow for minor rounding


@pytest.mark.asyncio
async def test_priority_multiple_clarifications(review_service):
    """Test priority for multiple clarifications."""
    priority = await review_service.get_review_priority(
        trigger=ReviewTrigger.MULTIPLE_CLARIFICATIONS,
    )

    assert priority == 10  # Lowest priority


# ============================================================================
# Tests - RAG Service Integration
# ============================================================================

@pytest.mark.asyncio
async def test_rag_add_example(rag_service, rag_repo):
    """Test adding an example to RAG."""
    example = await rag_service.add_example(
        nl_query="Show me all users",
        generated_query="SELECT * FROM users",
        is_good=True,
        provider_id="postgresql",
        involved_tables=["users"],
        query_intent="filter",
        complexity_level="simple",
        auto_approve=False,
    )

    assert example is not None
    assert example.status == ExampleStatus.PENDING_REVIEW
    assert example.natural_language_query == "Show me all users"
    assert example.generated_query == "SELECT * FROM users"


@pytest.mark.asyncio
async def test_rag_add_example_auto_approve(rag_service, rag_repo):
    """Test adding an auto-approved example."""
    example = await rag_service.add_example(
        nl_query="Show me all products",
        generated_query="SELECT * FROM products",
        is_good=True,
        provider_id="postgresql",
        involved_tables=["products"],
        auto_approve=True,
    )

    assert example is not None

    # Refresh from DB to get updated status
    example = await rag_repo.get_by_id(example.id)
    assert example.status == ExampleStatus.APPROVED
    assert example.reviewed_by == "system"


@pytest.mark.asyncio
async def test_rag_remove_example(rag_service, rag_repo):
    """Test removing an example."""
    # Add an example
    example = await rag_service.add_example(
        nl_query="Test query",
        generated_query="SELECT 1",
        is_good=True,
        provider_id="postgresql",
    )

    example_id = example.id

    # Remove it
    removed = await rag_service.remove_example(example_id)
    assert removed is True

    # Verify it's gone
    example = await rag_repo.get_by_id(example_id)
    assert example is None


@pytest.mark.asyncio
async def test_rag_search_examples(rag_service, rag_repo):
    """Test searching for similar examples."""
    # Add some approved examples
    for i in range(3):
        example = await rag_service.add_example(
            nl_query=f"Show me all orders from customer {i}",
            generated_query=f"SELECT * FROM orders WHERE customer_id = {i}",
            is_good=True,
            provider_id="postgresql",
            involved_tables=["orders"],
            query_intent="filter",
            auto_approve=True,
        )

    # Search for similar queries
    results = await rag_service.search_examples(
        query="Show me orders for customer 5",
        provider_id="postgresql",
        limit=5,
    )

    assert len(results) > 0
    assert all(r.status == ExampleStatus.APPROVED for r in results)
    assert all(r.provider_id == "postgresql" for r in results)


@pytest.mark.asyncio
async def test_rag_search_with_intent_filter(rag_service):
    """Test searching with intent filter."""
    # Add examples with different intents
    await rag_service.add_example(
        nl_query="Show all orders",
        generated_query="SELECT * FROM orders",
        is_good=True,
        provider_id="postgresql",
        query_intent="filter",
        auto_approve=True,
    )

    await rag_service.add_example(
        nl_query="Count all orders",
        generated_query="SELECT COUNT(*) FROM orders",
        is_good=True,
        provider_id="postgresql",
        query_intent="aggregation",
        auto_approve=True,
    )

    # Search with intent filter
    results = await rag_service.search_examples(
        query="How many users",
        provider_id="postgresql",
        query_intent="aggregation",
        limit=5,
    )

    # Should only get aggregation examples
    assert all(r.query_intent == "aggregation" for r in results)


@pytest.mark.asyncio
async def test_rag_get_statistics(rag_service):
    """Test getting RAG statistics."""
    # Add various examples
    await rag_service.add_example(
        nl_query="Query 1",
        generated_query="SELECT 1",
        is_good=True,
        provider_id="postgresql",
        auto_approve=False,
    )

    await rag_service.add_example(
        nl_query="Query 2",
        generated_query="SELECT 2",
        is_good=True,
        provider_id="postgresql",
        auto_approve=True,
    )

    stats = await rag_service.get_statistics(provider_id="postgresql")

    assert stats["provider_id"] == "postgresql"
    assert stats["pending_review"] >= 1
    assert stats["approved"] >= 1
    assert stats["total"] >= 2


# ============================================================================
# Tests - End-to-End Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_complete_review_workflow(
    review_service,
    rag_service,
    rag_repo,
    sample_turn,
):
    """Test complete workflow from auto-queue to approval."""
    # Step 1: Auto-queue for review
    example_id = await review_service.auto_queue_for_review(
        turn_id=sample_turn.id,
        trigger=ReviewTrigger.LOW_CONFIDENCE,
        provider_id="postgresql",
    )

    assert example_id is not None

    # Step 2: Verify it's in pending status
    example = await rag_repo.get_by_id(example_id)
    assert example.status == ExampleStatus.PENDING_REVIEW

    # Step 3: Expert reviews and approves with correction
    corrected_query = "SELECT * FROM orders WHERE created_at >= '2024-01-01'"

    result = await review_service.process_review_decision(
        item_id=example_id,
        decision=ReviewDecision.CORRECT,
        reviewer="expert_alice",
        corrected_query=corrected_query,
        notes="Improved date handling",
    )

    assert result["approved"] is True
    assert result["status"] == ExampleStatus.APPROVED.value

    # Step 4: Verify it's now approved and ready for RAG
    example = await rag_repo.get_by_id(example_id)
    assert example.status == ExampleStatus.APPROVED
    assert example.get_query_for_rag() == corrected_query

    # Step 5: Search should now find this example
    results = await rag_service.search_examples(
        query="Show me orders",
        provider_id="postgresql",
        limit=5,
    )

    # Should include our approved example
    assert any(r.id == example_id for r in results)
