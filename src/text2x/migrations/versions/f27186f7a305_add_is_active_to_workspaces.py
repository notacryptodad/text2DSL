"""add_is_active_to_workspaces

Revision ID: f27186f7a305
Revises: b4b5bc67eb34
Create Date: 2026-02-07 15:39:10.083567

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f27186f7a305"
down_revision: Union[str, Sequence[str], None] = "b4b5bc67eb34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add is_active column to workspaces."""
    op.add_column("workspaces", sa.Column("is_active", sa.Boolean(), nullable=False, default=True))


def downgrade() -> None:
    """Downgrade schema - remove is_active column from workspaces."""
    op.drop_column("workspaces", "is_active")
