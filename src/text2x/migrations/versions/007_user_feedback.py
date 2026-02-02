"""Add user_feedback table.

Revision ID: 007
Revises: 006
Create Date: 2025-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create user_feedback table."""
    op.create_table(
        "user_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "turn_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversation_turns.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "rating",
            sa.Enum("up", "down", name="feedbackrating"),
            nullable=False,
        ),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column(
            "feedback_category",
            sa.Enum(
                "incorrect_result",
                "syntax_error",
                "missing_context",
                "performance_issue",
                "clarification_needed",
                "great_result",
                "other",
                name="feedbackcategory",
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_feedback_turn_id", "user_feedback", ["turn_id"])
    op.create_index("ix_user_feedback_rating", "user_feedback", ["rating"])
    op.create_index("ix_user_feedback_feedback_category", "user_feedback", ["feedback_category"])
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])


def downgrade() -> None:
    """Drop user_feedback table."""
    op.drop_table("user_feedback")
    op.execute("DROP TYPE IF EXISTS feedbackrating")
    op.execute("DROP TYPE IF EXISTS feedbackcategory")
