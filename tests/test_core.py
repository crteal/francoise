import os
import tempfile
import unittest
from unittest.mock import patch

from françoise.core import handle_inbound
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestCore(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.environ['DATABASE_URL'] = self.db_path

        upgrade_to_head(self.db_path)
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        self.account_id = account[0]
        with open_db(self.db_path, account_id=self.account_id) as db:
            user = db.create_user('Alice', 'alice@example.com', 'hash')
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

    @patch('françoise.core.chat', return_value='Bonjour !')
    def test_handle_inbound_persists_messages(self, mock_chat):
        conversation_id = self.conversation[0]
        handle_inbound(conversation_id, 'Hello')

        with open_db(self.db_path, account_id=self.account_id) as db:
            messages = db.get_messages_by_conversation(conversation_id)

        # get_messages_by_conversation now returns (role, content, created_at);
        # core ignores the timestamp (message_tuple_to_dict zips role/content).
        pairs = [(role, content) for role, content, *_ in messages]
        self.assertIn(('user', 'Hello'), pairs)
        self.assertIn(('assistant', 'Bonjour !'), pairs)

    def test_handle_inbound_raises_when_conversation_missing(self):
        with self.assertRaises(Exception):
            handle_inbound(999999, 'Hello')


if __name__ == '__main__':
    unittest.main()
