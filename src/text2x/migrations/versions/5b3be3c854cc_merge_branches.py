"""merge_branches

Revision ID: 5b3be3c854cc
Revises: 008, add_query_hints_001
Create Date: 2026-02-04 22:58:44.337236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b3be3c854cc'
down_revision: Union[str, Sequence[str], None] = ('008', 'add_query_hints_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
