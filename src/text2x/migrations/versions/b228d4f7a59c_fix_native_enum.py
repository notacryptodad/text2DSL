"""fix_native_enum

Revision ID: b228d4f7a59c
Revises: 5b3be3c854cc
Create Date: 2026-02-04 23:14:20.031991

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b228d4f7a59c"
down_revision: Union[str, Sequence[str], None] = "5b3be3c854cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "rag_examples",
        "status",
        existing_type=sa.Enum("pending_review", "approved", "rejected", name="examplestatus"),
        type_=sa.Enum(
            "PENDING_REVIEW", "APPROVED", "REJECTED", name="examplestatus", native_enum=False
        ),
        existing_nullable=False,
        existing_server_default=sa.text("'pending_review'::examplestatus"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "rag_examples",
        "status",
        existing_type=sa.Enum(
            "PENDING_REVIEW", "APPROVED", "REJECTED", name="examplestatus", native_enum=False
        ),
        type_=sa.Enum("pending_review", "approved", "rejected", name="examplestatus"),
        existing_nullable=False,
        existing_server_default=sa.text("'pending_review'::examplestatus"),
    )
