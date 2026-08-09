"""add model_configs table and reference it from conversations

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-09 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialect TEXT,
            host TEXT,
            endpoint TEXT,
            model_id TEXT NOT NULL,
            params TEXT,
            credential_ref TEXT,
            UNIQUE(model_id)
        );
    """)
    # Backfill a model_config per distinct existing model string.
    op.execute("""
        INSERT INTO model_configs (model_id)
        SELECT DISTINCT model FROM conversations;
    """)
    # SQLite cannot drop a column a table constraint references, so rebuild
    # `conversations`, swapping the `model` string for a `model_config_id` FK.
    op.execute("""
        CREATE TABLE conversations_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_id INTEGER NOT NULL,
            model_config_id INTEGER NOT NULL,
            proficiency TEXT NOT NULL,
            account_id INTEGER REFERENCES accounts(id),
            UNIQUE(model_config_id, user_id, agent_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(agent_id) REFERENCES agents(id),
            FOREIGN KEY(model_config_id) REFERENCES model_configs(id)
        );
    """)
    op.execute("""
        INSERT INTO conversations_new
            (id, user_id, agent_id, model_config_id, proficiency, account_id)
        SELECT
            conversation.id,
            conversation.user_id,
            conversation.agent_id,
            model_config.id,
            conversation.proficiency,
            conversation.account_id
        FROM conversations conversation
        JOIN model_configs model_config
        ON model_config.model_id = conversation.model;
    """)
    op.execute("DROP TABLE conversations;")
    op.execute("ALTER TABLE conversations_new RENAME TO conversations;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        CREATE TABLE conversations_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            proficiency TEXT NOT NULL,
            account_id INTEGER REFERENCES accounts(id),
            UNIQUE(model, user_id, agent_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(agent_id) REFERENCES agents(id)
        );
    """)
    op.execute("""
        INSERT INTO conversations_old
            (id, user_id, agent_id, model, proficiency, account_id)
        SELECT
            conversation.id,
            conversation.user_id,
            conversation.agent_id,
            model_config.model_id,
            conversation.proficiency,
            conversation.account_id
        FROM conversations conversation
        JOIN model_configs model_config
        ON model_config.id = conversation.model_config_id;
    """)
    op.execute("DROP TABLE conversations;")
    op.execute("ALTER TABLE conversations_old RENAME TO conversations;")
    op.execute("DROP TABLE IF EXISTS model_configs;")
