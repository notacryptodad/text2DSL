"""Add audit_logs table.

Revision ID: 008
Revises: 007
Create Date: 2025-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_logs table."""
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "turn_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversation_turns.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Request details
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        # Processing details
        sa.Column("schema_context_used", postgresql.JSON(), nullable=False),
        sa.Column("rag_examples_retrieved", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("iterations", sa.Integer(), nullable=False, server_default="1"),
        # Agent traces
        sa.Column("schema_agent_trace", postgresql.JSON(), nullable=True),
        sa.Column("query_builder_trace", postgresql.JSON(), nullable=True),
        sa.Column("validator_trace", postgresql.JSON(), nullable=True),
        # Results
        sa.Column("final_query", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("validation_status", sa.String(50), nullable=False),
        sa.Column("execution_success", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("execution_error", sa.Text(), nullable=True),
        # Cost tracking
        sa.Column("total_tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("model_used", sa.String(100), nullable=False),
        # Performance metrics
        sa.Column("total_latency_ms", sa.Integer(), nullable=False),
        sa.Column("schema_agent_latency_ms", sa.Integer(), nullable=True),
        sa.Column("rag_retrieval_latency_ms", sa.Integer(), nullable=True),
        sa.Column("query_builder_latency_ms", sa.Integer(), nullable=True),
        sa.Column("validator_latency_ms", sa.Integer(), nullable=True),
        # Additional metadata (named 'metadata' in DB)
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        # Timestamps
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
    op.create_index("ix_audit_logs_conversation_id", "audit_logs", ["conversation_id"])
    op.create_index("ix_audit_logs_turn_id", "audit_logs", ["turn_id"])
    op.create_index("ix_audit_logs_provider_id", "audit_logs", ["provider_id"])
    op.create_index("ix_audit_logs_validation_status", "audit_logs", ["validation_status"])
    op.create_index("ix_audit_logs_execution_success", "audit_logs", ["execution_success"])


def downgrade() -> None:
    """Drop audit_logs table."""
    op.drop_table("audit_logs")
