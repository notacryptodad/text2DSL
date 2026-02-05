"""remove_workspace_expert_role

Revision ID: 81cbfeaef060
Revises: 789ab4f987e7
Create Date: 2026-02-05 22:43:29.615491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81cbfeaef060'
down_revision: Union[str, Sequence[str], None] = '789ab4f987e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove workspace expert role - convert to member."""
    # Convert workspace experts to members
    op.execute("""
        UPDATE workspace_admins 
        SET role = 'member' 
        WHERE role = 'expert'
    """)


def downgrade() -> None:
    """Downgrade schema - no-op."""
    pass
