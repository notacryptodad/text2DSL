"""merge_branches

Revision ID: b4b5bc67eb34
Revises: 280659df1085
Create Date: 2026-02-07 15:22:43.560148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4b5bc67eb34'
down_revision: Union[str, Sequence[str], None] = '280659df1085'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
