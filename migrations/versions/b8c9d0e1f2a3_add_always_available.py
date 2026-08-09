"""add always_available toggle to accounts

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE accounts "
        "ADD COLUMN always_available INTEGER NOT NULL DEFAULT 0;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE accounts DROP COLUMN always_available;")
