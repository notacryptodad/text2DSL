"""Add conversations and conversation_turns tables.

Revision ID: 004
Revises: 003
Create Date: 2025-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create conversations and conversation_turns tables."""
    # Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "abandoned", name="conversationstatus"),
            nullable=False,
            server_default="active",
        ),
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
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_connection_id", "conversations", ["connection_id"])
    op.create_index("ix_conversations_provider_id", "conversations", ["provider_id"])
    op.create_index("ix_conversations_status", "conversations", ["status"])

    # Create conversation_turns table
    op.create_table(
        "conversation_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("generated_query", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "clarification_needed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("clarification_question", sa.Text(), nullable=True),
        sa.Column("validation_result", postgresql.JSON(), nullable=True),
        sa.Column("execution_result", postgresql.JSON(), nullable=True),
        sa.Column("reasoning_trace", postgresql.JSON(), nullable=False),
        sa.Column("schema_context", postgresql.JSON(), nullable=True),
        sa.Column("rag_examples_used", postgresql.JSON(), nullable=True),
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
    op.create_index(
        "ix_conversation_turns_conversation_id",
        "conversation_turns",
        ["conversation_id"],
    )


def downgrade() -> None:
    """Drop conversations and conversation_turns tables."""
    op.drop_table("conversation_turns")
    op.drop_table("conversations")
    op.execute("DROP TYPE IF EXISTS conversationstatus")
