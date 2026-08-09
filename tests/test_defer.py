import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head
from françoise.presence import is_free


def _at(hour):
    return datetime(2026, 1, 1, hour, tzinfo=ZoneInfo('UTC'))


class TestIsFree(unittest.TestCase):
    def test_asleep_is_not_free(self):
        self.assertFalse(is_free({'timezone': 'UTC', 'age': 10}, _at(2)))

    def test_school_is_not_free(self):
        self.assertFalse(is_free({'timezone': 'UTC', 'age': 10}, _at(10)))

    def test_free_window_is_free(self):
        self.assertTrue(is_free({'timezone': 'UTC', 'age': 10}, _at(16)))


class TestDeferReply(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        password_hash = PasswordHasher().hash('correct horse')
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        with open_db(self.db_path, account_id=account[0]) as db:
            self.user = db.create_user('Alice', 'alice@example.com', password_hash)
            agent = db.create_agent('Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation = db.create_conversation(
                user_id=self.user[0],
                agent_id=agent[0],
                proficiency='A1',
                model='test-model')

        self.app = App(DATABASE_URL=self.db_path)
        self.client = TestClient(self.app)
        self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})

    def tearDown(self):
        os.remove(self.db_path)

    def _post(self):
        # No wall-clock waits: the poll sleep is a no-op in the test.
        with patch('françoise.app.asyncio.sleep', return_value=None), \
                patch('françoise.app.stream_inbound', return_value=iter(['Bonjour !'])):
            self.client.post(
                '/c/%d/message' % self.conversation[0],
                data={'message': 'Hello'})

    def test_reply_waits_while_asleep_then_sends_when_free(self):
        channel = self.app.state.get_channel(self.user[0])

        # Asleep now, free on the next check: the persona holds the reply
        # through the sleep window and sends it in the first free window.
        states = iter([False, True])
        with patch('françoise.app.is_free', side_effect=lambda *a: next(states)):
            self._post()

        # The reply reached the stream once the persona was free.
        self.assertFalse(channel.empty())
        self.assertIn('Bonjour !', channel.get_nowait())


if __name__ == '__main__':
    unittest.main()
