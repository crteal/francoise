import hashlib
import hmac
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head

API_KEY = 'signing-key'


def sign(timestamp: str, token: str) -> str:
    return hmac.new(
        key=API_KEY.encode(),
        msg=(timestamp + token).encode(),
        digestmod=hashlib.sha256).hexdigest()


class TestMailgunRoute(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        with open_db(self.db_path, account_id=account[0]) as db:
            user = db.create_user('Alice', 'alice@example.com', 'hash')
            agent = db.create_agent('Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation = db.create_conversation(
                user_id=user[0],
                agent_id=agent[0],
                proficiency='A1',
                model='test-model')

        self.app = App(
            DATABASE_URL=self.db_path,
            MAILGUN_API_KEY=API_KEY,
            MAILGUN_API_SENDER='boku@example.com',
            MAILGUN_API_URL='https://api.example.com')
        self.client = TestClient(self.app)

    def tearDown(self):
        os.remove(self.db_path)

    def _post(self, sender):
        conversation_id = self.conversation[0]
        headers = '[["To","\"Boku.%d\" <boku@example.com>"]]' % conversation_id
        return self.client.post('/mailgun', data={
            'message-headers': headers,
            'body-plain': 'Hello',
            'sender': sender,
            'subject': 'Salut',
            'timestamp': '12345',
            'token': 'abc',
            'signature': sign('12345', 'abc')})

    def test_exact_sender_calls_core_and_sends_reply(self):
        conversation_id = self.conversation[0]
        with patch('françoise.app.handle_inbound', return_value='Bonjour !') as mock_core, \
                patch('françoise.app.send_mail') as mock_send:
            response = self._post('alice@example.com')

        self.assertEqual(response.status_code, 200)
        mock_core.assert_called_once_with(conversation_id, 'Hello')
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        self.assertEqual(kwargs['data']['text'], 'Bonjour !')

    def test_near_match_sender_is_rejected(self):
        # 'lice@example.com' is a substring of the user email, so the old
        # substring check let it through; an exact match must reject it.
        with patch('françoise.app.handle_inbound') as mock_core, \
                patch('françoise.app.send_mail') as mock_send:
            # the reply runs as a background task; the rejection surfaces
            # as the exception TestClient re-raises after the response.
            with self.assertRaises(Exception):
                self._post('lice@example.com')

        mock_core.assert_not_called()
        mock_send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
