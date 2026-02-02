"""Add workspace_admins table

Revision ID: 003_workspace_admins
Revises: 002
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workspace_admins table
    op.create_table(
        'workspace_admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('invited_by', sa.String(255), nullable=False),
        sa.Column('invited_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', 'role', name='uq_workspace_admin_user_role')
    )
    
    # Create indexes
    op.create_index('ix_workspace_admins_workspace_user', 'workspace_admins', ['workspace_id', 'user_id'])
    op.create_index('ix_workspace_admins_workspace_role', 'workspace_admins', ['workspace_id', 'role'])
    op.create_index('ix_workspace_admins_user', 'workspace_admins', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_workspace_admins_user', table_name='workspace_admins')
    op.drop_index('ix_workspace_admins_workspace_role', table_name='workspace_admins')
    op.drop_index('ix_workspace_admins_workspace_user', table_name='workspace_admins')
    op.drop_table('workspace_admins')
