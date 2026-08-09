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
            user = db.create_user('Alice', 'alice@example.com', 'hash')
            agent = db.create_agent('Boku', 'French', 'A1', 'You are {agent_name}.')
            self.conversation_one = db.create_conversation(
                user_id=user[0], agent_id=agent[0],
                proficiency='A1', model='m')[0]

        with open_db(self.db_path, account_id=self.account_two) as db:
            user = db.create_user('Bob', 'bob@example.com', 'hash')
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
                db.create_user('Eve', 'eve@example.com', 'hash')

    def test_model_round_trips_and_reuses_config(self):
        with open_db(self.db_path, account_id=self.account_one) as db:
            user = db.create_user('Carol', 'carol@example.com', 'hash')
            agent = db.create_agent(
                'Momo', 'French', 'A1', 'You are {agent_name}.')
            other = db.create_agent(
                'Nono', 'French', 'A2', 'You are {agent_name}.')
            first = db.create_conversation(
                user_id=user[0], agent_id=agent[0],
                proficiency='A1', model='ollama/llama3')[0]
            # A different agent keeps the UNIQUE key distinct while the same
            # model string must still reuse the one model_config row.
            second = db.create_conversation(
                user_id=user[0], agent_id=other[0],
                proficiency='A2', model='ollama/llama3')[0]

            # The model string round-trips through the JOIN unchanged.
            conversation = db.conversation_to_dict(db.get_conversation(first))
            self.assertEqual(conversation['model'], 'ollama/llama3')

            # Both conversations reference the same model_config row.
            rows = db.connection.execute(
                "SELECT model_config_id FROM conversations WHERE id IN (?, ?)",
                (first, second)).fetchall()
            self.assertEqual(rows[0][0], rows[1][0])
            count = db.connection.execute(
                "SELECT COUNT(*) FROM model_configs "
                "WHERE model_id = 'ollama/llama3'").fetchone()[0]
            self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main()
