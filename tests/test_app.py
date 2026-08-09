import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestMailgunRoute(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        with open_db(self.db_path) as db:
            user = db.create_user('Alice', 'alice@example.com', 'salt', 'password')
            agent = db.create_agent('Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation = db.create_conversation(
                user_id=user[0],
                agent_id=agent[0],
                proficiency='A1',
                model='test-model')

        self.app = App(
            DATABASE_URL=self.db_path,
            MAILGUN_API_KEY='key',
            MAILGUN_API_SENDER='boku@example.com',
            MAILGUN_API_URL='https://api.example.com')
        self.client = TestClient(self.app)

    def tearDown(self):
        os.remove(self.db_path)

    def test_mailgun_calls_core_and_sends_reply(self):
        conversation_id = self.conversation[0]
        headers = '[["To","\"Boku.%d\" <boku@example.com>"]]' % conversation_id

        with patch('françoise.app.handle_inbound', return_value='Bonjour !') as mock_core, \
                patch('françoise.app.send_mail') as mock_send:
            response = self.client.post('/mailgun', data={
                'message-headers': headers,
                'body-plain': 'Hello',
                'sender': 'alice@example.com',
                'subject': 'Salut'})

        self.assertEqual(response.status_code, 200)
        mock_core.assert_called_once_with(conversation_id, 'Hello')
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        self.assertEqual(kwargs['data']['text'], 'Bonjour !')


if __name__ == '__main__':
    unittest.main()
