"""merge_branches

Revision ID: 25dfbf784b86
Revises: f27186f7a305
Create Date: 2026-02-08 16:05:57.461386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25dfbf784b86'
down_revision: Union[str, Sequence[str], None] = 'f27186f7a305'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
