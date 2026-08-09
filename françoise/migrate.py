import os

from alembic import command
from alembic.config import Config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def upgrade_to_head(database_url: str) -> None:
    """Bring a database up to the latest migration."""
    os.environ['DATABASE_URL'] = database_url
    config = Config(os.path.join(ROOT, 'alembic.ini'))
    command.upgrade(config, 'head')
