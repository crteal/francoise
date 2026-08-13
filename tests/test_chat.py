import os
import tempfile
import unittest
from unittest.mock import patch

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestChatUI(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        password_hash = PasswordHasher().hash('correct horse')
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        with open_db(self.db_path, account_id=account[0]) as db:
            user = db.create_user('Alice', 'alice@example.com', password_hash)
            agent = db.create_agent('Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation = db.create_conversation(
                user_id=user[0],
                agent_id=agent[0],
                proficiency='A1',
                model='test-model')
            db.add_user_message(self.conversation[0], 'Bonjour <b>')

        self.app = App(DATABASE_URL=self.db_path)
        self.client = TestClient(self.app)
        self._login()

    def tearDown(self):
        os.remove(self.db_path)

    def _login(self):
        response = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})
        self.assertEqual(response.status_code, 200)

    def test_dashboard_lists_conversations(self):
        response = self.client.get('/app')
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/c/1"', response.text)
        self.assertIn('Boku', response.text)
        self.assertIn('id="presence-1"', response.text)
        self.assertIn('id="unread-1"', response.text)
        self.assertIn('/agents/new', response.text)

    def test_chat_view_has_wiring_and_history(self):
        response = self.client.get('/c/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="messages-1"', response.text)
        self.assertIn('id="presence-1"', response.text)
        self.assertIn('sse-connect="/stream"', response.text)
        self.assertIn('hx-post="/c/1/message"', response.text)
        # message history renders, escaped
        self.assertIn('Bonjour &lt;b&gt;', response.text)

    def test_post_message_returns_echo(self):
        # is_free pinned True so the deferral background task completes
        # deterministically (otherwise it loops on the wall-clock and hangs).
        with patch('françoise.app.stream_inbound', return_value=iter([])), \
                patch('françoise.app.is_free', return_value=True):
            response = self.client.post(
                '/c/1/message', data={'message': 'Salut'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Salut', response.text)

    def test_chat_view_missing_is_404(self):
        response = self.client.get('/c/999')
        self.assertEqual(response.status_code, 404)

    def test_routes_require_session(self):
        anon = TestClient(self.app)
        for path in ('/app', '/c/1'):
            response = anon.get(path, follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertEqual(response.headers['location'], '/login')


if __name__ == '__main__':
    unittest.main()
