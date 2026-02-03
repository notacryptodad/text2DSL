"""Add query generation hint columns to schema_annotations

Revision ID: add_query_hints_001
Revises: 
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = 'add_query_hints_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for query generation hints
    op.add_column('schema_annotations', sa.Column('primary_lookup_column', sa.String(255), nullable=True))
    op.add_column('schema_annotations', sa.Column('represents', sa.String(255), nullable=True))
    op.add_column('schema_annotations', sa.Column('is_searchable', sa.Boolean(), nullable=True))
    op.add_column('schema_annotations', sa.Column('search_type', sa.String(50), nullable=True))
    op.add_column('schema_annotations', sa.Column('aggregation', sa.String(50), nullable=True))
    op.add_column('schema_annotations', sa.Column('data_format', sa.String(100), nullable=True))
    op.add_column('schema_annotations', sa.Column('join_hints', JSONB(), nullable=True))


def downgrade():
    op.drop_column('schema_annotations', 'join_hints')
    op.drop_column('schema_annotations', 'data_format')
    op.drop_column('schema_annotations', 'aggregation')
    op.drop_column('schema_annotations', 'search_type')
    op.drop_column('schema_annotations', 'is_searchable')
    op.drop_column('schema_annotations', 'represents')
    op.drop_column('schema_annotations', 'primary_lookup_column')
