"""add structured persona fields to agents

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-09 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERSONA_COLUMNS = (
    ('location', 'TEXT'),
    ('timezone', 'TEXT'),
    ('interests', 'TEXT'),
    ('age', 'INTEGER'),
    ('native_language', 'TEXT'),
)


def upgrade() -> None:
    """Upgrade schema."""
    for name, kind in PERSONA_COLUMNS:
        op.execute("ALTER TABLE agents ADD COLUMN %s %s;" % (name, kind))


def downgrade() -> None:
    """Downgrade schema."""
    for name, _ in reversed(PERSONA_COLUMNS):
        op.execute("ALTER TABLE agents DROP COLUMN %s;" % name)
