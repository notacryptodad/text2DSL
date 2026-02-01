"""End-to-end tests for the complete feedback flow.

Tests the full feedback pipeline including:
- Submitting feedback via API
- Auto-queue logic based on confidence + rating
- Statistics aggregation
- Review queue integration
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import text, select

from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.models.conversation import Conversation, ConversationTurn, ConversationStatus
from text2x.models.feedback import UserFeedback, FeedbackRating, FeedbackCategory
from text2x.models.rag import RAGExample, ExampleStatus

from text2x.repositories.conversation import ConversationRepository, ConversationTurnRepository
from text2x.repositories.feedback import FeedbackRepository
from text2x.services.feedback_service import FeedbackService

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
async def feedback_service(setup_db):
    return FeedbackService()


@pytest_asyncio.fixture
async def conversation_repo(setup_db):
    return ConversationRepository()


@pytest_asyncio.fixture
async def turn_repo(setup_db):
    return ConversationTurnRepository()


@pytest_asyncio.fixture
async def feedback_repo(setup_db):
    return FeedbackRepository()


async def create_test_turn(
    conversation_repo,
    turn_repo,
    confidence: float = 0.95,
    user_input: str = "Show me all orders",
    generated_query: str = "SELECT * FROM orders",
):
    """Helper to create a test conversation turn."""
    conversation = await conversation_repo.create(
        user_id="test-user",
        provider_id="test-provider",
    )

    turn = await turn_repo.create(
        conversation_id=conversation.id,
        turn_number=1,
        user_input=user_input,
        generated_query=generated_query,
        confidence_score=confidence,
        reasoning_trace={"intent": "aggregation"},
    )

    return conversation, turn


# ============================================================================
# Auto-Queue Logic Tests
# ============================================================================

class TestAutoQueueLogic:
    """Test the auto-queue decision logic."""

    @pytest.mark.asyncio
    async def test_thumbs_up_high_confidence_auto_approve(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test thumbs up + confidence >= 0.9 auto-approves to RAG."""
        # Create turn with high confidence (0.95)
        conversation, turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.95,
        )

        # Submit thumbs up feedback
        feedback = await feedback_service.submit_feedback(
            turn_id=turn.id,
            rating=FeedbackRating.UP,
            category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
            feedback_text="Perfect!",
        )

        assert feedback is not None
        assert feedback.rating == FeedbackRating.UP

        # Check that RAG example was created and auto-approved
        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(
                RAGExample.source_conversation_id == conversation.id
            )
            result = await session.execute(stmt)
            rag_example = result.scalar_one_or_none()

            assert rag_example is not None
            assert rag_example.status == ExampleStatus.APPROVED
            assert rag_example.is_good_example is True
            assert rag_example.reviewed_by == "auto_approved"
            assert rag_example.natural_language_query == turn.user_input
            assert rag_example.generated_query == turn.generated_query

    @pytest.mark.asyncio
    async def test_thumbs_up_medium_confidence_queue_review(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test thumbs up + confidence < 0.9 queues for review (low priority)."""
        # Create turn with medium confidence (0.75)
        conversation, turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.75,
        )

        # Submit thumbs up feedback
        feedback = await feedback_service.submit_feedback(
            turn_id=turn.id,
            rating=FeedbackRating.UP,
            category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        assert feedback is not None

        # Check that RAG example was created for review
        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(
                RAGExample.source_conversation_id == conversation.id
            )
            result = await session.execute(stmt)
            rag_example = result.scalar_one_or_none()

            assert rag_example is not None
            assert rag_example.status == ExampleStatus.PENDING_REVIEW
            assert rag_example.is_good_example is True  # Low priority = likely good
            assert rag_example.extra_metadata["review_priority"] == "low"
            assert rag_example.extra_metadata["review_reason"] == "thumbs_up_medium_confidence"

    @pytest.mark.asyncio
    async def test_thumbs_down_queue_high_priority(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test thumbs down queues for review (high priority)."""
        # Create turn with any confidence
        conversation, turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.85,
        )

        # Submit thumbs down feedback
        feedback = await feedback_service.submit_feedback(
            turn_id=turn.id,
            rating=FeedbackRating.DOWN,
            category=FeedbackCategory.INCORRECT_RESULT,
            user_id="test-user",
            feedback_text="Wrong results",
        )

        assert feedback is not None
        assert feedback.rating == FeedbackRating.DOWN

        # Check that RAG example was created for high-priority review
        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(
                RAGExample.source_conversation_id == conversation.id
            )
            result = await session.execute(stmt)
            rag_example = result.scalar_one_or_none()

            assert rag_example is not None
            assert rag_example.status == ExampleStatus.PENDING_REVIEW
            assert rag_example.is_good_example is False  # High priority = likely bad
            assert rag_example.extra_metadata["review_priority"] == "high"
            assert rag_example.extra_metadata["review_reason"] == "thumbs_down"
            assert "Wrong results" in rag_example.review_notes

    @pytest.mark.asyncio
    async def test_existing_rag_example_updated(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test that existing RAG example is updated instead of creating duplicate."""
        conversation, turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.85,
        )

        # Create existing RAG example
        db = get_db()
        async with db.session() as session:
            existing_example = RAGExample(
                provider_id="test-provider",
                natural_language_query=turn.user_input,
                generated_query=turn.generated_query,
                is_good_example=True,
                status=ExampleStatus.PENDING_REVIEW,
                involved_tables=["orders"],
                query_intent="aggregation",
                complexity_level="simple",
                source_conversation_id=conversation.id,
            )
            session.add(existing_example)
            await session.commit()
            example_id = existing_example.id

        # Submit feedback
        await feedback_service.submit_feedback(
            turn_id=turn.id,
            rating=FeedbackRating.DOWN,
            category=FeedbackCategory.INCORRECT_RESULT,
            user_id="test-user",
            feedback_text="Needs correction",
        )

        # Verify existing example was updated, not duplicated
        async with db.session() as session:
            stmt = select(RAGExample).where(
                RAGExample.source_conversation_id == conversation.id
            )
            result = await session.execute(stmt)
            examples = result.scalars().all()

            assert len(examples) == 1
            assert examples[0].id == example_id
            assert examples[0].status == ExampleStatus.PENDING_REVIEW
            assert "Needs correction" in examples[0].review_notes


# ============================================================================
# Feedback Statistics Tests
# ============================================================================

class TestFeedbackStats:
    """Test feedback statistics aggregation."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, feedback_service, setup_db):
        """Test getting stats with no feedback."""
        stats = await feedback_service.get_stats(days=30)

        assert stats.total_feedback == 0
        assert stats.thumbs_up == 0
        assert stats.thumbs_down == 0
        assert stats.approval_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_stats_with_feedback(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test aggregated feedback statistics."""
        # Create multiple feedback entries
        for i in range(3):
            _, turn = await create_test_turn(
                conversation_repo,
                turn_repo,
                confidence=0.9,
                user_input=f"Query {i}",
                generated_query=f"SELECT {i}",
            )
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=FeedbackRating.UP,
                category=FeedbackCategory.GREAT_RESULT,
                user_id="test-user",
            )

        for i in range(2):
            _, turn = await create_test_turn(
                conversation_repo,
                turn_repo,
                confidence=0.5,
                user_input=f"Bad query {i}",
                generated_query=f"SELECT BAD {i}",
            )
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=FeedbackRating.DOWN,
                category=FeedbackCategory.INCORRECT_RESULT,
                user_id="test-user",
            )

        # Get stats
        stats = await feedback_service.get_stats(days=30)

        assert stats.total_feedback == 5
        assert stats.thumbs_up == 3
        assert stats.thumbs_down == 2
        assert stats.approval_rate == 0.6  # 3/5
        assert stats.avg_confidence_thumbs_up > stats.avg_confidence_thumbs_down

    @pytest.mark.asyncio
    async def test_get_stats_by_category(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test category breakdown in stats."""
        # Create feedback with different categories
        categories = [
            FeedbackCategory.GREAT_RESULT,
            FeedbackCategory.GREAT_RESULT,
            FeedbackCategory.INCORRECT_RESULT,
            FeedbackCategory.SYNTAX_ERROR,
        ]

        for i, category in enumerate(categories):
            _, turn = await create_test_turn(
                conversation_repo,
                turn_repo,
                confidence=0.9,
                user_input=f"Query {i}",
                generated_query=f"SELECT {i}",
            )
            rating = FeedbackRating.UP if category == FeedbackCategory.GREAT_RESULT else FeedbackRating.DOWN
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=rating,
                category=category,
                user_id="test-user",
            )

        stats = await feedback_service.get_stats(days=30)

        assert stats.by_category["great_result"] == 2
        assert stats.by_category["incorrect_result"] == 1
        assert stats.by_category["syntax_error"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_time_filter(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        feedback_repo,
        setup_db,
    ):
        """Test stats with time filtering."""
        # Create old feedback (should not be included in 7-day stats)
        _, old_turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.9,
        )

        db = get_db()
        async with db.session() as session:
            old_feedback = UserFeedback(
                turn_id=old_turn.id,
                rating=FeedbackRating.UP,
                feedback_category=FeedbackCategory.GREAT_RESULT,
                user_id="test-user",
            )
            # Manually set created_at to 10 days ago
            old_feedback.created_at = datetime.utcnow() - timedelta(days=10)
            session.add(old_feedback)
            await session.commit()

        # Create recent feedback
        _, recent_turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.9,
            user_input="Recent query",
            generated_query="SELECT recent",
        )
        await feedback_service.submit_feedback(
            turn_id=recent_turn.id,
            rating=FeedbackRating.UP,
            category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        # Get stats for last 7 days
        stats_7_days = await feedback_service.get_stats(days=7)
        assert stats_7_days.total_feedback == 1  # Only recent feedback

        # Get stats for last 30 days
        stats_30_days = await feedback_service.get_stats(days=30)
        assert stats_30_days.total_feedback == 2  # Both feedbacks


# ============================================================================
# Recent Feedback Tests
# ============================================================================

class TestRecentFeedback:
    """Test recent feedback retrieval."""

    @pytest.mark.asyncio
    async def test_get_recent_feedback(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test getting recent feedback items."""
        # Create multiple feedback entries
        for i in range(5):
            _, turn = await create_test_turn(
                conversation_repo,
                turn_repo,
                confidence=0.9,
                user_input=f"Query {i}",
                generated_query=f"SELECT {i}",
            )
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=FeedbackRating.UP if i % 2 == 0 else FeedbackRating.DOWN,
                category=FeedbackCategory.GREAT_RESULT if i % 2 == 0 else FeedbackCategory.INCORRECT_RESULT,
                user_id="test-user",
            )

        recent = await feedback_service.get_recent_feedback(limit=10)

        assert len(recent) == 5
        # Should be ordered by created_at desc (most recent first)

    @pytest.mark.asyncio
    async def test_get_recent_feedback_with_filter(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test getting recent feedback filtered by rating."""
        # Create mixed feedback
        for i in range(3):
            _, turn = await create_test_turn(
                conversation_repo,
                turn_repo,
                confidence=0.9,
                user_input=f"Good query {i}",
                generated_query=f"SELECT {i}",
            )
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=FeedbackRating.UP,
                category=FeedbackCategory.GREAT_RESULT,
                user_id="test-user",
            )

        for i in range(2):
            _, turn = await create_test_turn(
                conversation_repo,
                turn_repo,
                confidence=0.5,
                user_input=f"Bad query {i}",
                generated_query=f"SELECT BAD {i}",
            )
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=FeedbackRating.DOWN,
                category=FeedbackCategory.INCORRECT_RESULT,
                user_id="test-user",
            )

        # Get only negative feedback
        recent_negative = await feedback_service.get_recent_feedback(
            limit=10,
            rating_filter=FeedbackRating.DOWN,
        )

        assert len(recent_negative) == 2
        assert all(f.rating == FeedbackRating.DOWN for f in recent_negative)

        # Get only positive feedback
        recent_positive = await feedback_service.get_recent_feedback(
            limit=10,
            rating_filter=FeedbackRating.UP,
        )

        assert len(recent_positive) == 3
        assert all(f.rating == FeedbackRating.UP for f in recent_positive)

    @pytest.mark.asyncio
    async def test_get_recent_feedback_limit(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test limit parameter for recent feedback."""
        # Create many feedback entries
        for i in range(10):
            _, turn = await create_test_turn(
                conversation_repo,
                turn_repo,
                confidence=0.9,
                user_input=f"Query {i}",
                generated_query=f"SELECT {i}",
            )
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=FeedbackRating.UP,
                category=FeedbackCategory.GREAT_RESULT,
                user_id="test-user",
            )

        # Get only 5
        recent = await feedback_service.get_recent_feedback(limit=5)
        assert len(recent) == 5


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestFeedbackEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_duplicate_feedback_error(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test that duplicate feedback for same turn raises error."""
        _, turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.9,
        )

        # Submit first feedback
        await feedback_service.submit_feedback(
            turn_id=turn.id,
            rating=FeedbackRating.UP,
            category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        # Try to submit duplicate feedback - should raise error
        with pytest.raises(Exception):  # IntegrityError from unique constraint
            await feedback_service.submit_feedback(
                turn_id=turn.id,
                rating=FeedbackRating.DOWN,
                category=FeedbackCategory.INCORRECT_RESULT,
                user_id="test-user",
            )

    @pytest.mark.asyncio
    async def test_feedback_without_text(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test submitting feedback without optional text."""
        _, turn = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.9,
        )

        feedback = await feedback_service.submit_feedback(
            turn_id=turn.id,
            rating=FeedbackRating.UP,
            category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
            feedback_text=None,  # No text
        )

        assert feedback is not None
        assert feedback.feedback_text is None

    @pytest.mark.asyncio
    async def test_confidence_boundary_0_9(
        self,
        feedback_service,
        conversation_repo,
        turn_repo,
        setup_db,
    ):
        """Test confidence boundary at exactly 0.9."""
        # Test at boundary: 0.9 should auto-approve
        conversation1, turn1 = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.9,
            user_input="Boundary test 1",
        )

        await feedback_service.submit_feedback(
            turn_id=turn1.id,
            rating=FeedbackRating.UP,
            category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        db = get_db()
        async with db.session() as session:
            stmt = select(RAGExample).where(
                RAGExample.source_conversation_id == conversation1.id
            )
            result = await session.execute(stmt)
            example = result.scalar_one_or_none()

            assert example.status == ExampleStatus.APPROVED  # Should auto-approve

        # Test just below: 0.89 should queue for review
        conversation2, turn2 = await create_test_turn(
            conversation_repo,
            turn_repo,
            confidence=0.89,
            user_input="Boundary test 2",
        )

        await feedback_service.submit_feedback(
            turn_id=turn2.id,
            rating=FeedbackRating.UP,
            category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        async with db.session() as session:
            stmt = select(RAGExample).where(
                RAGExample.source_conversation_id == conversation2.id
            )
            result = await session.execute(stmt)
            example = result.scalar_one_or_none()

            assert example.status == ExampleStatus.PENDING_REVIEW  # Should queue
