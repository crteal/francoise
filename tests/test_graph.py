import shutil
import tempfile
import unittest

from françoise.graph import open_graph
from françoise.vocab import (
    FR_PREDICATES,
    GRAPHS,
    SCHEMA_PREDICATES,
    agent_iri,
    topic_iri,
)


class TestGraph(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)

    def test_assert_then_query(self):
        subject = 'http://example.com/subject'
        predicate = FR_PREDICATES['enjoys']
        object = 'http://example.com/object'

        with open_graph(self.path) as graph:
            graph.assert_quad(subject, predicate, object)
            rows = list(graph.query(
                'SELECT ?s ?p ?o WHERE { ?s ?p ?o }'))

        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0]['s']), '<%s>' % subject)
        self.assertEqual(str(rows[0]['p']), '<%s>' % predicate)
        self.assertEqual(str(rows[0]['o']), '<%s>' % object)

    def test_assert_unknown_predicate_fails(self):
        with open_graph(self.path) as graph:
            with self.assertRaises(ValueError):
                graph.assert_quad(
                    'http://example.com/subject',
                    'http://example.com/unknown',
                    'http://example.com/object')


    def test_seed_persona(self):
        with open_graph(self.path) as graph:
            graph.seed_persona(1, 'Boku', interests=['cinema', 'cooking'])

            agent = agent_iri(1)
            real = GRAPHS['real']

            # The agent has a self name fact in the real graph.
            rows = list(graph.query(
                'SELECT ?o WHERE { GRAPH <%s> { <%s> <%s> ?o } }'
                % (real, agent, SCHEMA_PREDICATES['name'])))
            self.assertEqual(len(rows), 1)
            self.assertEqual(str(rows[0]['o']), '"Boku"')

            # Each interest has a topic node and a trait edge.
            for interest in ('cinema', 'cooking'):
                topic = topic_iri(interest)
                self.assertTrue(bool(graph.query(
                    'ASK { GRAPH <%s> { <%s> <%s> <%s> } }'
                    % (real, agent, FR_PREDICATES['enjoys'], topic))))


    def test_read_facts_by_agent_and_topic(self):
        with open_graph(self.path) as graph:
            graph.seed_persona(1, 'Boku', interests=['cinema'])

            facts = graph.read_facts(1, topics=['cinema'])

            joined = '\n'.join(facts)
            # the agent's own name fact is present, rendered by label
            self.assertIn('Boku', joined)
            # a topic-relevant fact (the topic's name) is present
            self.assertIn('cinema', joined)


if __name__ == '__main__':
    unittest.main()
