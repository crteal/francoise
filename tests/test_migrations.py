import os
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config

from françoise.db import open_db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEMA_TABLES = {'accounts', 'users', 'agents', 'conversations', 'messages'}


def existing_tables(db_path):
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    finally:
        connection.close()
    return {row[0] for row in rows}


class TestMigrations(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.environ['DATABASE_URL'] = self.db_path
        self.config = Config(os.path.join(ROOT, 'alembic.ini'))
        self.config.set_main_option('script_location', os.path.join(ROOT, 'migrations'))

    def tearDown(self):
        os.environ.pop('DATABASE_URL', None)
        os.remove(self.db_path)

    def test_upgrade_head_creates_version_table(self):
        command.upgrade(self.config, 'head')
        self.assertIn('alembic_version', existing_tables(self.db_path))

    def test_upgrade_creates_schema_tables(self):
        command.upgrade(self.config, 'head')
        self.assertTrue(SCHEMA_TABLES.issubset(existing_tables(self.db_path)))

    def test_downgrade_drops_schema_tables(self):
        command.upgrade(self.config, 'head')
        command.downgrade(self.config, 'base')
        self.assertEqual(SCHEMA_TABLES & existing_tables(self.db_path), set())

    def test_insert_and_read_account(self):
        command.upgrade(self.config, 'head')
        with open_db(self.db_path) as db:
            created = db.create_account('Acme')
            read = db.get_account(created[0])
        self.assertEqual(read[0], created[0])
        self.assertEqual(read[1], 'Acme')
        self.assertTrue(read[2])


if __name__ == '__main__':
    unittest.main()
