import os
import tempfile
import unittest
from unittest.mock import patch

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestRateLimit(unittest.TestCase):
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
            agent = db.create_agent(
                'Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation = db.create_conversation(
                user_id=self.user[0],
                agent_id=agent[0],
                proficiency='A1',
                model='test-model')

        # small limit so the test crosses it quickly
        self.app = App(DATABASE_URL=self.db_path, RATE_LIMIT='2')
        self.client = TestClient(self.app)
        self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})

    def tearDown(self):
        os.remove(self.db_path)

    def test_requests_under_the_limit_pass_and_over_the_limit_error(self):
        conversation_id = self.conversation[0]

        with patch('françoise.app.stream_inbound',
                   return_value=iter([])):
            # under the limit: passes
            for _ in range(2):
                ok = self.client.post(
                    '/c/%d/message' % conversation_id,
                    data={'message': 'Bonjour'})
                self.assertEqual(ok.status_code, 200)

            # over the limit: rejected
            over = self.client.post(
                '/c/%d/message' % conversation_id,
                data={'message': 'Bonjour'})
        self.assertEqual(over.status_code, 429)


if __name__ == '__main__':
    unittest.main()
