"""initial schema

Revision ID: 4bec47424dbc
Revises: 
Create Date: 2026-08-09 02:19:01.170687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bec47424dbc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            salt TEXT NOT NULL,
            password TEXT NOT NULL
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            language TEXT NOT NULL,
            proficiency TEXT NOT NULL,
            prompt TEXT NOT NULL
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            proficiency TEXT NOT NULL,
            UNIQUE(model, user_id, agent_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(agent_id) REFERENCES agents(id)
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS messages;")
    op.execute("DROP TABLE IF EXISTS conversations;")
    op.execute("DROP TABLE IF EXISTS agents;")
    op.execute("DROP TABLE IF EXISTS users;")
