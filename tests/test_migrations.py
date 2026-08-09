import os
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMigrations(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.environ['DATABASE_URL'] = self.db_path

    def tearDown(self):
        os.environ.pop('DATABASE_URL', None)
        os.remove(self.db_path)

    def test_upgrade_head_creates_version_table(self):
        config = Config(os.path.join(ROOT, 'alembic.ini'))
        config.set_main_option('script_location', os.path.join(ROOT, 'migrations'))
        command.upgrade(config, 'head')

        connection = sqlite3.connect(self.db_path)
        try:
            row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'alembic_version'"
            ).fetchone()
        finally:
            connection.close()

        self.assertIsNotNone(row)


if __name__ == '__main__':
    unittest.main()
