"""merge_branches

Revision ID: 280659df1085
Revises: 035465c49747
Create Date: 2026-02-07 15:21:34.833686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '280659df1085'
down_revision: Union[str, Sequence[str], None] = '035465c49747'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
