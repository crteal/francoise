import os
import shutil
import tempfile
import unittest

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.graph import open_graph
from françoise.migrate import upgrade_to_head
from françoise.vocab import GRAPHS, SCHEMA_PREDICATES, agent_iri


class TestAgentRoutes(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.graph_path = tempfile.mkdtemp()

        upgrade_to_head(self.db_path)
        password_hash = PasswordHasher().hash('correct horse')
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        with open_db(self.db_path, account_id=account[0]) as db:
            self.user = db.create_user(
                'Alice', 'alice@example.com', password_hash)

        self.app = App(
            DATABASE_URL=self.db_path,
            GRAPH_PATH=self.graph_path)
        self.client = TestClient(self.app)
        self._login()

    def tearDown(self):
        os.remove(self.db_path)
        shutil.rmtree(self.graph_path)

    def _login(self):
        response = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})
        self.assertEqual(response.status_code, 200)

    def _valid_form(self, **overrides):
        data = {
            'name': 'Boku',
            'native_language': 'English',
            'language': 'French',
            'proficiency': 'A1',
            'location': '48.85, 2.35',
            'timezone': 'Europe/Paris',
            'interests': 'cinema, cooking',
            'age': '10',
        }
        data.update(overrides)
        return data

    def test_get_new_shows_form(self):
        response = self.client.get('/agents/new')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<form', response.text)
        # the CEFR select is populated
        self.assertIn('A1', response.text)
        self.assertIn('C2', response.text)

    def test_create_persists_fields_seeds_graph_and_lists(self):
        response = self.client.post(
            '/agents', data=self._valid_form(), follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/agents')

        # The agent row has the structured fields set.
        with open_db(self.db_path, account_id=1) as db:
            rows = db.list_agents()
            self.assertEqual(len(rows), 1)
            agent_id = rows[0][0]
            full = db.connection.execute(
                'SELECT timezone, age, interests, location, native_language '
                'FROM agents WHERE id = ?', (agent_id,)).fetchone()
        self.assertEqual(full[0], 'Europe/Paris')
        self.assertEqual(full[1], 10)
        self.assertEqual(full[2], 'cinema, cooking')
        self.assertEqual(full[3], '48.85, 2.35')
        self.assertEqual(full[4], 'English')

        # The persona's self quad is seeded into the real graph.
        with open_graph(self.graph_path) as graph:
            rows = list(graph.query(
                'SELECT ?o WHERE { GRAPH <%s> { <%s> <%s> ?o } }'
                % (GRAPHS['real'], agent_iri(agent_id),
                   SCHEMA_PREDICATES['name'])))
        self.assertEqual(str(rows[0]['o']), '"Boku"')

        # GET /agents shows the new persona.
        response = self.client.get('/agents')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Boku', response.text)
        self.assertIn('French', response.text)

    def test_start_creates_conversation_and_redirects(self):
        self.client.post('/agents', data=self._valid_form())
        with open_db(self.db_path, account_id=1) as db:
            agent_id = db.list_agents()[0][0]

        response = self.client.post(
            '/agents/%d/start' % agent_id, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        with open_db(self.db_path, account_id=1) as db:
            row = db.connection.execute(
                'SELECT id FROM conversations WHERE agent_id = ?',
                (agent_id,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(response.headers['location'], '/c/%d' % row[0])

    def test_start_twice_opens_same_conversation(self):
        # Starting with a friend you already have a conversation with must open
        # the existing one, not 500 on UNIQUE(model_config_id, user_id, agent_id).
        self.client.post('/agents', data=self._valid_form())
        with open_db(self.db_path, account_id=1) as db:
            agent_id = db.list_agents()[0][0]

        first = self.client.post(
            '/agents/%d/start' % agent_id, follow_redirects=False)
        second = self.client.post(
            '/agents/%d/start' % agent_id, follow_redirects=False)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(first.headers['location'], second.headers['location'])

    def test_invalid_cefr_is_rejected(self):
        response = self.client.post(
            '/agents', data=self._valid_form(proficiency='Z9'))
        self.assertEqual(response.status_code, 400)
        with open_db(self.db_path, account_id=1) as db:
            self.assertEqual(len(db.list_agents()), 0)

    def test_invalid_timezone_is_rejected(self):
        response = self.client.post(
            '/agents', data=self._valid_form(timezone='Not/AZone'))
        self.assertEqual(response.status_code, 400)
        with open_db(self.db_path, account_id=1) as db:
            self.assertEqual(len(db.list_agents()), 0)

    def test_non_numeric_age_is_rejected(self):
        response = self.client.post(
            '/agents', data=self._valid_form(age='ten'))
        self.assertEqual(response.status_code, 400)
        with open_db(self.db_path, account_id=1) as db:
            self.assertEqual(len(db.list_agents()), 0)

    def test_routes_require_session(self):
        anon = TestClient(self.app)
        for method, path in (
                ('get', '/agents'),
                ('get', '/agents/new'),
                ('post', '/agents'),
                ('post', '/agents/1/start')):
            response = getattr(anon, method)(path, follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertEqual(response.headers['location'], '/login')


if __name__ == '__main__':
    unittest.main()
