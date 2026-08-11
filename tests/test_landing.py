import os
import tempfile
import unittest

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestLanding(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        password_hash = PasswordHasher().hash('correct horse')
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        with open_db(self.db_path, account_id=account[0]) as db:
            db.create_user('Alice', 'alice@example.com', password_hash)

        self.app = App(DATABASE_URL=self.db_path)
        self.client = TestClient(self.app)

    def tearDown(self):
        os.remove(self.db_path)

    def test_anonymous_landing_renders_without_redirect(self):
        # Anonymous GET / is the public cover-series landing: 200, no redirect,
        # masthead nameplate present, sign-up CTA shown.
        anon = TestClient(self.app)
        response = anon.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('masthead', response.text)
        self.assertIn('françoise', response.text)
        self.assertIn('cover', response.text)
        self.assertIn('href="/signup"', response.text)

    def test_dashboard_redirects_anonymous_to_login(self):
        anon = TestClient(self.app)
        response = anon.get('/app', follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['location'], '/login')

    def test_logged_in_landing_links_into_app(self):
        self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/app"', response.text)
        self.assertNotIn('href="/signup"', response.text)


if __name__ == '__main__':
    unittest.main()
