"""Tests for UserFeedback Repository.

Uses PostgreSQL test container for proper integration testing.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text

from text2x.models.base import Base, DatabaseConfig, init_db, close_db, get_db
from text2x.models.workspace import Workspace, Provider, Connection, ProviderType, ConnectionStatus
from text2x.models.conversation import Conversation, ConversationTurn, ConversationStatus
from text2x.models.feedback import UserFeedback, FeedbackRating, FeedbackCategory

from text2x.repositories.conversation import ConversationRepository, ConversationTurnRepository
from text2x.repositories.feedback import FeedbackRepository

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
        await conn.execute(text("DROP TABLE IF EXISTS user_feedback CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversation_turns CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS connections CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS workspaces CASCADE"))

    await close_db()


@pytest_asyncio.fixture
async def feedback_repo(setup_db):
    return FeedbackRepository()


@pytest_asyncio.fixture
async def conversation_repo(setup_db):
    return ConversationRepository()


@pytest_asyncio.fixture
async def turn_repo(setup_db):
    return ConversationTurnRepository()


@pytest_asyncio.fixture
async def sample_turn(setup_db, conversation_repo, turn_repo):
    """Create a sample conversation turn for feedback testing."""
    conversation = await conversation_repo.create(
        user_id="test-user",
        provider_id="test-provider",
    )

    turn = await turn_repo.create(
        conversation_id=conversation.id,
        turn_number=1,
        user_input="Show me all orders",
        generated_query="SELECT * FROM orders",
        confidence_score=0.95,
        reasoning_trace={"steps": ["analyzed", "generated"]},
    )

    return turn


# ============================================================================
# UserFeedback Repository Tests
# ============================================================================

class TestFeedbackRepository:
    """Test FeedbackRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_positive_feedback(self, feedback_repo, sample_turn):
        """Test creating positive feedback (thumbs up)."""
        feedback = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
            feedback_text="Perfect query!",
        )

        assert feedback is not None
        assert feedback.turn_id == sample_turn.id
        assert feedback.rating == FeedbackRating.UP
        assert feedback.feedback_category == FeedbackCategory.GREAT_RESULT
        assert feedback.feedback_text == "Perfect query!"
        assert feedback.is_positive is True
        assert feedback.is_negative is False

    @pytest.mark.asyncio
    async def test_create_negative_feedback(self, feedback_repo, sample_turn):
        """Test creating negative feedback (thumbs down)."""
        feedback = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            user_id="test-user",
            feedback_text="Wrong results returned",
        )

        assert feedback is not None
        assert feedback.rating == FeedbackRating.DOWN
        assert feedback.feedback_category == FeedbackCategory.INCORRECT_RESULT
        assert feedback.is_positive is False
        assert feedback.is_negative is True

    @pytest.mark.asyncio
    async def test_create_feedback_without_text(self, feedback_repo, sample_turn):
        """Test creating feedback without optional text."""
        feedback = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        assert feedback is not None
        assert feedback.feedback_text is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, feedback_repo, sample_turn):
        """Test getting feedback by ID."""
        created = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        fetched = await feedback_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, feedback_repo):
        """Test getting non-existent feedback."""
        result = await feedback_repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_turn_id(self, feedback_repo, sample_turn):
        """Test getting feedback by turn ID."""
        created = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        fetched = await feedback_repo.get_by_turn_id(sample_turn.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.turn_id == sample_turn.id

    @pytest.mark.asyncio
    async def test_get_by_turn_id_not_found(self, feedback_repo):
        """Test getting feedback for turn with no feedback."""
        result = await feedback_repo.get_by_turn_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_user(
        self,
        feedback_repo,
        conversation_repo,
        turn_repo
    ):
        """Test listing feedback by user."""
        # Create multiple turns
        conv = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn1 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=1,
            user_input="Query 1",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        turn2 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=2,
            user_input="Query 2",
            generated_query="SELECT 2",
            confidence_score=0.85,
            reasoning_trace={},
        )

        # Create feedback for different users
        await feedback_repo.create(
            turn_id=turn1.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="user-1",
        )
        await feedback_repo.create(
            turn_id=turn2.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            user_id="user-1",
        )

        results = await feedback_repo.list_by_user("user-1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_by_user_with_rating_filter(
        self,
        feedback_repo,
        conversation_repo,
        turn_repo
    ):
        """Test listing feedback by user with rating filter."""
        conv = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn1 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=1,
            user_input="Query 1",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        turn2 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=2,
            user_input="Query 2",
            generated_query="SELECT 2",
            confidence_score=0.85,
            reasoning_trace={},
        )

        await feedback_repo.create(
            turn_id=turn1.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="user-1",
        )
        await feedback_repo.create(
            turn_id=turn2.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            user_id="user-1",
        )

        positive = await feedback_repo.list_by_user("user-1", rating=FeedbackRating.UP)
        assert len(positive) == 1
        assert positive[0].rating == FeedbackRating.UP

    @pytest.mark.asyncio
    async def test_list_by_rating(
        self,
        feedback_repo,
        conversation_repo,
        turn_repo
    ):
        """Test listing feedback by rating."""
        conv = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn1 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=1,
            user_input="Query 1",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        turn2 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=2,
            user_input="Query 2",
            generated_query="SELECT 2",
            confidence_score=0.85,
            reasoning_trace={},
        )

        await feedback_repo.create(
            turn_id=turn1.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="user-1",
        )
        await feedback_repo.create(
            turn_id=turn2.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            user_id="user-2",
        )

        negative = await feedback_repo.list_by_rating(FeedbackRating.DOWN)
        assert len(negative) == 1
        assert negative[0].rating == FeedbackRating.DOWN

    @pytest.mark.asyncio
    async def test_list_by_category(
        self,
        feedback_repo,
        conversation_repo,
        turn_repo
    ):
        """Test listing feedback by category."""
        conv = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn1 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=1,
            user_input="Query 1",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        turn2 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=2,
            user_input="Query 2",
            generated_query="SELECT 2",
            confidence_score=0.85,
            reasoning_trace={},
        )

        await feedback_repo.create(
            turn_id=turn1.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            user_id="user-1",
        )
        await feedback_repo.create(
            turn_id=turn2.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.SYNTAX_ERROR,
            user_id="user-1",
        )

        incorrect = await feedback_repo.list_by_category(
            FeedbackCategory.INCORRECT_RESULT
        )
        assert len(incorrect) == 1
        assert incorrect[0].feedback_category == FeedbackCategory.INCORRECT_RESULT

    @pytest.mark.asyncio
    async def test_list_negative_feedback(
        self,
        feedback_repo,
        conversation_repo,
        turn_repo
    ):
        """Test listing negative feedback for analysis."""
        conv = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn1 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=1,
            user_input="Query 1",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        turn2 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=2,
            user_input="Query 2",
            generated_query="SELECT 2",
            confidence_score=0.85,
            reasoning_trace={},
        )
        turn3 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=3,
            user_input="Query 3",
            generated_query="SELECT 3",
            confidence_score=0.8,
            reasoning_trace={},
        )

        await feedback_repo.create(
            turn_id=turn1.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="user-1",
        )
        await feedback_repo.create(
            turn_id=turn2.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            user_id="user-1",
        )
        await feedback_repo.create(
            turn_id=turn3.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.SYNTAX_ERROR,
            user_id="user-1",
        )

        negative = await feedback_repo.list_negative_feedback()
        assert len(negative) == 2
        assert all(f.rating == FeedbackRating.DOWN for f in negative)

    @pytest.mark.asyncio
    async def test_list_negative_feedback_with_category(
        self,
        feedback_repo,
        conversation_repo,
        turn_repo
    ):
        """Test listing negative feedback filtered by category."""
        conv = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn1 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=1,
            user_input="Query 1",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )
        turn2 = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=2,
            user_input="Query 2",
            generated_query="SELECT 2",
            confidence_score=0.85,
            reasoning_trace={},
        )

        await feedback_repo.create(
            turn_id=turn1.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            user_id="user-1",
        )
        await feedback_repo.create(
            turn_id=turn2.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.SYNTAX_ERROR,
            user_id="user-1",
        )

        negative_syntax = await feedback_repo.list_negative_feedback(
            category=FeedbackCategory.SYNTAX_ERROR
        )
        assert len(negative_syntax) == 1
        assert negative_syntax[0].feedback_category == FeedbackCategory.SYNTAX_ERROR

    @pytest.mark.asyncio
    async def test_list_recent(
        self,
        feedback_repo,
        conversation_repo,
        turn_repo
    ):
        """Test listing recent feedback."""
        conv = await conversation_repo.create(
            user_id="user-1", provider_id="prov"
        )
        turn = await turn_repo.create(
            conversation_id=conv.id,
            turn_number=1,
            user_input="Query",
            generated_query="SELECT 1",
            confidence_score=0.9,
            reasoning_trace={},
        )

        await feedback_repo.create(
            turn_id=turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="user-1",
        )

        recent = await feedback_repo.list_recent(limit=10)
        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_update_feedback(self, feedback_repo, sample_turn):
        """Test updating feedback."""
        created = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
            feedback_text="Original text",
        )

        updated = await feedback_repo.update(
            created.id,
            rating=FeedbackRating.DOWN,
            feedback_category=FeedbackCategory.INCORRECT_RESULT,
            feedback_text="Updated text",
        )

        assert updated is not None
        assert updated.rating == FeedbackRating.DOWN
        assert updated.feedback_category == FeedbackCategory.INCORRECT_RESULT
        assert updated.feedback_text == "Updated text"

    @pytest.mark.asyncio
    async def test_update_feedback_partial(self, feedback_repo, sample_turn):
        """Test partially updating feedback."""
        created = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
            feedback_text="Original text",
        )

        updated = await feedback_repo.update(
            created.id,
            feedback_text="Only text updated",
        )

        assert updated is not None
        assert updated.rating == FeedbackRating.UP  # Unchanged
        assert updated.feedback_text == "Only text updated"

    @pytest.mark.asyncio
    async def test_update_feedback_not_found(self, feedback_repo):
        """Test updating non-existent feedback."""
        result = await feedback_repo.update(
            uuid4(),
            rating=FeedbackRating.DOWN,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_feedback(self, feedback_repo, sample_turn):
        """Test deleting feedback."""
        created = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
        )

        result = await feedback_repo.delete(created.id)
        assert result is True

        fetched = await feedback_repo.get_by_id(created.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_feedback_not_found(self, feedback_repo):
        """Test deleting non-existent feedback."""
        result = await feedback_repo.delete(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_feedback_to_dict(self, feedback_repo, sample_turn):
        """Test converting feedback to dictionary."""
        feedback = await feedback_repo.create(
            turn_id=sample_turn.id,
            rating=FeedbackRating.UP,
            feedback_category=FeedbackCategory.GREAT_RESULT,
            user_id="test-user",
            feedback_text="Great!",
        )

        feedback_dict = feedback.to_dict()

        assert feedback_dict["id"] == str(feedback.id)
        assert feedback_dict["turn_id"] == str(sample_turn.id)
        assert feedback_dict["rating"] == "up"
        assert feedback_dict["feedback_category"] == "great_result"
        assert feedback_dict["user_id"] == "test-user"
        assert feedback_dict["feedback_text"] == "Great!"
        assert "created_at" in feedback_dict
        assert "updated_at" in feedback_dict
