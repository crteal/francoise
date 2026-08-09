"""add iri columns to users and agents

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-09 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ponytail: generated column derives the IRI from the surrogate id, so it stays
# correct for existing and future rows with no backfill or trigger.
def upgrade() -> None:
    """Upgrade schema."""
    for table, kind in (('users', 'user'), ('agents', 'agent')):
        op.execute(
            "ALTER TABLE %s ADD COLUMN iri TEXT "
            "GENERATED ALWAYS AS ('urn:francoise:%s:' || id) VIRTUAL;"
            % (table, kind)
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('users', 'agents'):
        op.execute("ALTER TABLE %s DROP COLUMN iri;" % table)
