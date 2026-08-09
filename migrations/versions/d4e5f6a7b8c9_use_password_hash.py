"""replace user salt and password with a single password_hash

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-09 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT '';")
    op.execute("ALTER TABLE users DROP COLUMN salt;")
    op.execute("ALTER TABLE users DROP COLUMN password;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE users ADD COLUMN salt TEXT NOT NULL DEFAULT '';")
    op.execute("ALTER TABLE users ADD COLUMN password TEXT NOT NULL DEFAULT '';")
    op.execute("ALTER TABLE users DROP COLUMN password_hash;")
