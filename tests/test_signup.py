import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestSignupRoutes(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)

        self.app = App(DATABASE_URL=self.db_path)
        self.client = TestClient(self.app)

    def tearDown(self):
        os.remove(self.db_path)

    def user_count(self) -> int:
        with open_db(self.db_path) as db:
            return db.connection.execute(
                'SELECT COUNT(*) FROM users').fetchone()[0]

    def test_over_18_completes_signup(self):
        response = self.client.post('/signup', data={
            'name': 'Alice',
            'email': 'alice@example.com',
            'password': 'correct horse',
            'over_18': 'yes'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user_count(), 1)

    def test_under_18_cannot_sign_up(self):
        response = self.client.post('/signup', data={
            'name': 'Bob',
            'email': 'bob@example.com',
            'password': 'correct horse'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.user_count(), 0)


if __name__ == '__main__':
    unittest.main()
