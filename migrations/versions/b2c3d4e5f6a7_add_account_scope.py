"""add account scope to core tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-09 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table in ('users', 'agents', 'conversations'):
        op.execute(
            "ALTER TABLE %s ADD COLUMN account_id INTEGER REFERENCES accounts(id);" % table
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('users', 'agents', 'conversations'):
        op.execute("ALTER TABLE %s DROP COLUMN account_id;" % table)
