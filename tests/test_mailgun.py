import hashlib
import hmac
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from françoise.app import App
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
        self.app = App(DATABASE_URL=self.db_path, MAILGUN_API_KEY=API_KEY)
        self.client = TestClient(self.app)

    def tearDown(self):
        os.remove(self.db_path)

    def _payload(self, timestamp, token, signature):
        return {
            'message-headers': '[["To","\"Boku.1\" <foo@bar.com>"]]',
            'body-plain': 'Bonjour',
            'sender': 'alice@example.com',
            'subject': 'Salut',
            'timestamp': timestamp,
            'token': token,
            'signature': signature,
        }

    def test_valid_signature_passes(self):
        # stub the scheduled work so a valid post does not run the real reply
        with patch('fastapi.BackgroundTasks.add_task') as mock_add_task:
            response = self.client.post(
                '/mailgun',
                data=self._payload('12345', 'abc', sign('12345', 'abc')))
        self.assertEqual(response.status_code, 200)
        mock_add_task.assert_called_once()

    def test_forged_signature_rejected(self):
        with patch('fastapi.BackgroundTasks.add_task') as mock_add_task:
            response = self.client.post(
                '/mailgun',
                data=self._payload('12345', 'abc', 'forged'))
        self.assertEqual(response.status_code, 401)
        mock_add_task.assert_not_called()


if __name__ == '__main__':
    unittest.main()
