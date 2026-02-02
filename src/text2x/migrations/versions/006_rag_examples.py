"""Add rag_examples table.

Revision ID: 006
Revises: 005
Create Date: 2025-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create rag_examples table."""
    op.create_table(
        "rag_examples",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        sa.Column("natural_language_query", sa.Text(), nullable=False),
        sa.Column("generated_query", sa.Text(), nullable=False),
        sa.Column("is_good_example", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "status",
            sa.Enum("pending_review", "approved", "rejected", name="examplestatus"),
            nullable=False,
            server_default="pending_review",
        ),
        sa.Column("involved_tables", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("query_intent", sa.String(100), nullable=False),
        sa.Column("complexity_level", sa.String(50), nullable=False),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("expert_corrected_query", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "source_conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("embeddings_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
    op.create_index("ix_rag_examples_provider_id", "rag_examples", ["provider_id"])
    op.create_index("ix_rag_examples_is_good_example", "rag_examples", ["is_good_example"])
    op.create_index("ix_rag_examples_status", "rag_examples", ["status"])
    op.create_index("ix_rag_examples_involved_tables", "rag_examples", ["involved_tables"])
    op.create_index("ix_rag_examples_query_intent", "rag_examples", ["query_intent"])
    op.create_index("ix_rag_examples_complexity_level", "rag_examples", ["complexity_level"])
    op.create_index("ix_rag_examples_source_conversation_id", "rag_examples", ["source_conversation_id"])


def downgrade() -> None:
    """Drop rag_examples table."""
    op.drop_table("rag_examples")
    op.execute("DROP TYPE IF EXISTS examplestatus")
