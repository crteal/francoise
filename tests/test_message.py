import os
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

    def test_post_message_echoes_calls_core_and_pushes_reply(self):
        conversation_id = self.conversation[0]

        with patch('françoise.app.handle_inbound', return_value='Salut !') as mock_core:
            response = self.client.post(
                '/c/%d/message' % conversation_id,
                data={'message': 'Bonjour'})

        self.assertEqual(response.status_code, 200)
        # response holds the immediate user echo partial
        self.assertIn('Bonjour', response.text)
        self.assertIn('<div>', response.text)

        # the web path runs the core with the posted message
        mock_core.assert_called_once_with(conversation_id, 'Bonjour')

        # the reply reaches the user's channel as an OOB fragment
        channel = self.app.state.get_channel(self.user[0])
        fragment = channel.get_nowait()
        self.assertIn('id="messages-%d"' % conversation_id, fragment)
        self.assertIn('Salut !', fragment)


if __name__ == '__main__':
    unittest.main()
