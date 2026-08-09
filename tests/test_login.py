import os
import tempfile
import unittest

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestLoginRoutes(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        password_hash = PasswordHasher().hash('correct horse')
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        with open_db(self.db_path, account_id=account[0]) as db:
            self.user = db.create_user(
                'Alice', 'alice@example.com', password_hash)

        self.app = App(DATABASE_URL=self.db_path)
        self.client = TestClient(self.app)

    def tearDown(self):
        os.remove(self.db_path)

    def test_get_login_shows_form(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<form', response.text)

    def test_correct_password_creates_session(self):
        response = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})
        self.assertEqual(response.status_code, 200)

        with open_db(self.db_path) as db:
            row = db.connection.execute(
                'SELECT COUNT(*) FROM sessions WHERE user_id = ?',
                (self.user[0],)).fetchone()
        self.assertEqual(row[0], 1)

    def test_login_sets_session_cookie_and_guards_page(self):
        # No cookie redirects to /login.
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['location'], '/login')

        # Logging in sets the session cookie.
        response = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('session', self.client.cookies)

        # A request carrying the cookie reaches the page.
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 200)

    def test_wrong_password_shows_error(self):
        response = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'wrong'})
        self.assertEqual(response.status_code, 401)

        with open_db(self.db_path) as db:
            row = db.connection.execute(
                'SELECT COUNT(*) FROM sessions').fetchone()
        self.assertEqual(row[0], 0)


if __name__ == '__main__':
    unittest.main()
