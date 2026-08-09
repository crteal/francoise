import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db

from scripts.provision import provision


class TestProvision(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.seeded = provision(database=self.db_path, reset=True)

    def tearDown(self):
        os.remove(self.db_path)

    def test_seeds_four_rows(self):
        with open_db(self.db_path) as db:
            for table in ('accounts', 'users', 'agents', 'conversations'):
                count = db.connection.execute(
                    'SELECT COUNT(*) FROM %s' % table).fetchone()[0]
                self.assertEqual(count, 1, table)

    def test_seeded_user_can_log_in(self):
        app = App(DATABASE_URL=self.db_path)
        client = TestClient(app)
        response = client.post('/login', data={
            'email': self.seeded['email'],
            'password': self.seeded['password']})
        self.assertEqual(response.status_code, 200)
        self.assertIn('session', response.cookies)


if __name__ == '__main__':
    unittest.main()
