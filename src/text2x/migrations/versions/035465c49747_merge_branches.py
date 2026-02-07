"""merge_branches

Revision ID: 035465c49747
Revises: 81cbfeaef060
Create Date: 2026-02-07 15:17:48.079179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '035465c49747'
down_revision: Union[str, Sequence[str], None] = '81cbfeaef060'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
