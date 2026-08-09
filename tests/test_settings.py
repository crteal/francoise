import os
import tempfile
import unittest
from unittest.mock import patch

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class _Break(Exception):
    pass


class TestSettings(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        password_hash = PasswordHasher().hash('correct horse')
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        self.account = account
        with open_db(self.db_path, account_id=account[0]) as db:
            self.user = db.create_user(
                'Alice', 'alice@example.com', password_hash)
            # Adult persona.
            adult = db.create_agent(
                'Boku', 'French', 'A1', 'You are {agent_name}.', age=30)
            self.adult_conversation = db.create_conversation(
                user_id=self.user[0], agent_id=adult[0],
                proficiency='A1', model='test-model')
            # Child persona.
            child = db.create_agent(
                'Kiki', 'French', 'A1', 'You are {agent_name}.', age=10)
            self.child_conversation = db.create_conversation(
                user_id=self.user[0], agent_id=child[0],
                proficiency='A1', model='test-model')

        self.app = App(DATABASE_URL=self.db_path)
        self.client = TestClient(self.app)
        response = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        os.remove(self.db_path)

    # --- per-conversation settings ---

    def test_change_proficiency_persists(self):
        response = self.client.post(
            '/c/%d/settings' % self.adult_conversation[0],
            data={'proficiency': 'B2', 'model': 'test-model'},
            follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        # The persisted level round-trips: reading it back shows B2 selected.
        with open_db(self.db_path, account_id=self.account[0]) as db:
            conversation = db.conversation_to_dict(
                db.get_conversation(self.adult_conversation[0]))
        self.assertEqual(conversation['user_proficiency'], 'B2')
        get = self.client.get(
            '/c/%d/settings' % self.adult_conversation[0])
        self.assertRegex(get.text, r'value="B2"\s*\n?\s*selected')

    def test_change_model_round_trips(self):
        self.client.post(
            '/c/%d/settings' % self.adult_conversation[0],
            data={'proficiency': 'A1',
                  'model': 'anthropic/claude-opus-4-8'})
        with open_db(self.db_path, account_id=self.account[0]) as db:
            conversation = db.conversation_to_dict(
                db.get_conversation(self.adult_conversation[0]))
        self.assertEqual(
            conversation['model'], 'anthropic/claude-opus-4-8')

    def test_invalid_proficiency_rejected(self):
        response = self.client.post(
            '/c/%d/settings' % self.adult_conversation[0],
            data={'proficiency': 'Z9', 'model': 'test-model'})
        self.assertEqual(response.status_code, 400)
        with open_db(self.db_path, account_id=self.account[0]) as db:
            conversation = db.conversation_to_dict(
                db.get_conversation(self.adult_conversation[0]))
        self.assertEqual(conversation['user_proficiency'], 'A1')

    def test_settings_missing_conversation_is_404(self):
        response = self.client.get('/c/999/settings')
        self.assertEqual(response.status_code, 404)

    # --- account settings ---

    def test_toggle_always_available_persists(self):
        response = self.client.post(
            '/settings', data={'always_available': 'yes'},
            follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        with open_db(self.db_path, account_id=self.account[0]) as db:
            account = db.get_account(self.account[0])
        self.assertEqual(account[3], 1)
        get = self.client.get('/settings')
        self.assertIn('checked', get.text)

    def test_toggle_off_persists(self):
        with open_db(self.db_path, account_id=self.account[0]) as db:
            db.set_account_always_available(self.account[0], True)
        # Unchecked box sends no field.
        self.client.post('/settings', data={})
        with open_db(self.db_path, account_id=self.account[0]) as db:
            account = db.get_account(self.account[0])
        self.assertEqual(account[3], 0)

    # --- presence override in reply_and_push ---

    def _post(self, conversation_id, sleep):
        with patch('françoise.app.asyncio.sleep', side_effect=sleep), \
                patch('françoise.app.stream_inbound',
                      return_value=iter(['Bonjour !'])):
            try:
                self.client.post(
                    '/c/%d/message' % conversation_id,
                    data={'message': 'Hello'})
            except _Break:
                pass

    def test_always_available_adult_replies_without_waiting(self):
        # always-available ON: an adult persona replies immediately even while
        # asleep. asyncio.sleep raising proves the wait loop is never entered.
        self.client.post('/settings', data={'always_available': 'yes'})
        channel = self.app.state.get_channel(self.user[0])

        def sleep(*a, **k):
            raise _Break()

        # Asleep hours in UTC for an adult; without the override this defers.
        with patch('françoise.app.is_free', return_value=False):
            self._post(self.adult_conversation[0], sleep)

        fragments = []
        while not channel.empty():
            fragments.append(channel.get_nowait())
        self.assertTrue(any('Bonjour !' in f for f in fragments))

    def test_always_available_child_still_defers(self):
        # always-available ON must NEVER bypass a child persona's sleep: the
        # wait loop IS entered, so asyncio.sleep raising breaks out with no
        # reply pushed.
        self.client.post('/settings', data={'always_available': 'yes'})
        channel = self.app.state.get_channel(self.user[0])

        def sleep(*a, **k):
            raise _Break()

        with patch('françoise.app.is_free', return_value=False):
            self._post(self.child_conversation[0], sleep)

        fragments = []
        while not channel.empty():
            fragments.append(channel.get_nowait())
        self.assertFalse(any('Bonjour !' in f for f in fragments))


if __name__ == '__main__':
    unittest.main()
