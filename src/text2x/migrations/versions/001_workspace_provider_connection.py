"""Add workspace, provider, and connection tables

Revision ID: 001_workspace_provider_connection
Revises:
Create Date: 2025-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workspaces_slug', 'workspaces', ['slug'], unique=True)
    
    # Create providers table
    op.create_table(
        'providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_provider_workspace_name')
    )
    op.create_index('ix_providers_workspace_id', 'providers', ['workspace_id'])
    op.create_index('ix_providers_workspace_type', 'providers', ['workspace_id', 'type'])
    
    # Create connections table
    op.create_table(
        'connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('host', sa.String(512), nullable=False),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('database', sa.String(255), nullable=False),
        sa.Column('schema_name', sa.String(255), nullable=True),
        sa.Column('credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('connection_options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('schema_cache_key', sa.String(255), nullable=True),
        sa.Column('schema_last_refreshed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_id', 'name', name='uq_connection_provider_name')
    )
    op.create_index('ix_connections_provider_id', 'connections', ['provider_id'])
    op.create_index('ix_connections_status', 'connections', ['status'])
    op.create_index('ix_connections_provider_database', 'connections', ['provider_id', 'database'])


def downgrade() -> None:
    # Drop connections table
    op.drop_index('ix_connections_provider_database', table_name='connections')
    op.drop_index('ix_connections_status', table_name='connections')
    op.drop_index('ix_connections_provider_id', table_name='connections')
    op.drop_table('connections')
    
    # Drop providers table
    op.drop_index('ix_providers_workspace_type', table_name='providers')
    op.drop_index('ix_providers_workspace_id', table_name='providers')
    op.drop_table('providers')
    
    # Drop workspaces table
    op.drop_index('ix_workspaces_slug', table_name='workspaces')
    op.drop_table('workspaces')
