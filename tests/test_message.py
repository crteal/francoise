import os
import re
import tempfile
import unittest
from unittest.mock import patch

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestMessageRoute(unittest.TestCase):
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

    def test_post_message_echoes_calls_core_and_streams_reply(self):
        conversation_id = self.conversation[0]

        with patch('françoise.app.stream_inbound',
                   return_value=iter(['Sa', 'lut', ' !'])) as mock_core:
            response = self.client.post(
                '/c/%d/message' % conversation_id,
                data={'message': 'Bonjour'})

        self.assertEqual(response.status_code, 200)
        # response holds the immediate user echo partial
        self.assertIn('Bonjour', response.text)
        self.assertIn('<div>', response.text)

        # the web path streams the reply through the core
        mock_core.assert_called_once_with(conversation_id, 'Bonjour')

        # each chunk reaches the user's channel as its own OOB fragment
        channel = self.app.state.get_channel(self.user[0])
        fragments = []
        while not channel.empty():
            fragments.append(channel.get_nowait())

        self.assertEqual(len(fragments), 3)
        for fragment in fragments:
            self.assertIn('id="messages-%d"' % conversation_id, fragment)
        self.assertEqual(
            ''.join(re.search(r'<div>(.*)</div></div>', f).group(1)
                    for f in fragments),
            'Salut !')


if __name__ == '__main__':
    unittest.main()
