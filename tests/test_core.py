import os
import tempfile
import unittest
from unittest.mock import patch

from françoise.core import handle_inbound
from françoise.db import open_db


class TestCore(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.environ['DATABASE_URL'] = self.db_path

        with open_db(self.db_path) as db:
            db.create_schema()
            user = db.create_user('Alice', 'alice@example.com', 'salt', 'password')
            agent = db.create_agent('Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation = db.create_conversation(
                user_id=user[0],
                agent_id=agent[0],
                proficiency='A1',
                model='test-model')

    def tearDown(self):
        os.environ.pop('DATABASE_URL', None)
        os.remove(self.db_path)

    @patch('françoise.core.chat', return_value='Bonjour !')
    def test_handle_inbound_returns_reply_text(self, mock_chat):
        reply = handle_inbound(self.conversation[0], 'Hello')
        self.assertEqual(reply, 'Bonjour !')
        mock_chat.assert_called_once()


if __name__ == '__main__':
    unittest.main()
