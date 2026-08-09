import os
import tempfile
import unittest

from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestAccountScope(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        upgrade_to_head(self.db_path)

        # Seed two accounts, each with its own conversation.
        with open_db(self.db_path) as db:
            self.account_one = db.create_account('One')[0]
            self.account_two = db.create_account('Two')[0]

        with open_db(self.db_path, account_id=self.account_one) as db:
            user = db.create_user('Alice', 'alice@example.com', 'salt', 'pw')
            agent = db.create_agent('Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation_one = db.create_conversation(
                user_id=user[0], agent_id=agent[0],
                proficiency='A1', model='m')[0]

        with open_db(self.db_path, account_id=self.account_two) as db:
            user = db.create_user('Bob', 'bob@example.com', 'salt', 'pw')
            agent = db.create_agent('Kimi', 'French', 'A1', 'You are {agent_name}.')
            self.conversation_two = db.create_conversation(
                user_id=user[0], agent_id=agent[0],
                proficiency='A1', model='m')[0]

    def tearDown(self):
        os.remove(self.db_path)

    def test_read_excludes_other_account(self):
        with open_db(self.db_path, account_id=self.account_one) as db:
            self.assertIsNotNone(db.get_conversation(self.conversation_one))
            # account two's conversation is invisible to account one
            self.assertIsNone(db.get_conversation(self.conversation_two))

    def test_query_without_account_raises(self):
        with open_db(self.db_path) as db:
            with self.assertRaises(Exception):
                db.get_conversation(self.conversation_one)
            with self.assertRaises(Exception):
                db.create_user('Eve', 'eve@example.com', 'salt', 'pw')


if __name__ == '__main__':
    unittest.main()
