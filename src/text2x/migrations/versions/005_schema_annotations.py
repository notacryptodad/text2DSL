"""Add schema_annotations table.

Revision ID: 005
Revises: 004
Create Date: 2025-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create schema_annotations table."""
    op.create_table(
        "schema_annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        sa.Column("table_name", sa.String(255), nullable=True),
        sa.Column("column_name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("business_terms", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("examples", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("relationships", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("date_format", sa.String(100), nullable=True),
        sa.Column("enum_values", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("sensitive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(255), nullable=False),
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
    op.create_index("ix_schema_annotations_provider_id", "schema_annotations", ["provider_id"])
    op.create_index("ix_schema_annotations_table_name", "schema_annotations", ["table_name"])
    op.create_index("ix_schema_annotations_column_name", "schema_annotations", ["column_name"])


def downgrade() -> None:
    """Drop schema_annotations table."""
    op.drop_table("schema_annotations")
