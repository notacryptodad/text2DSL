"""fix_feedback_native_enum

Revision ID: 789ab4f987e7
Revises: b228d4f7a59c
Create Date: 2026-02-04 23:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "789ab4f987e7"
down_revision: Union[str, Sequence[str], None] = "b228d4f7a59c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "user_feedback",
        "rating",
        existing_type=sa.Enum("up", "down", name="feedbackrating"),
        type_=sa.Enum("UP", "DOWN", name="feedbackrating", native_enum=False),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "user_feedback",
        "rating",
        existing_type=sa.Enum("UP", "DOWN", name="feedbackrating", native_enum=False),
        type_=sa.Enum("up", "down", name="feedbackrating"),
        existing_nullable=False,
    )
