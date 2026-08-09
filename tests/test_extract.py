import os
import shutil
import tempfile
import unittest

from françoise.extract import extract
from françoise.graph import open_graph
from françoise.vocab import (
    GRAPHS,
    SCHEMA_PREDICATES,
    message_iri,
)


class TestExtract(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()
        os.environ['GRAPH_PATH'] = self.path

    def tearDown(self):
        os.environ.pop('GRAPH_PATH', None)
        shutil.rmtree(self.path)

    def test_asserts_fact_from_message(self):
        # A message with a clear fact: Alice knows Bob.
        def extractor(text):
            return [('Alice', SCHEMA_PREDICATES['knows'], 'Bob')]

        extract(7, 'Alice knows Bob.', extractor=extractor)

        real = GRAPHS['real']
        with open_graph(self.path) as graph:
            # The fact is asserted, exactly once.
            rows = list(graph.query(
                'SELECT ?s ?o WHERE { GRAPH <%s> { ?s <%s> ?o } }'
                % (real, SCHEMA_PREDICATES['knows'])))
            self.assertEqual(len(rows), 1)
            # It is linked to its source message.
            self.assertTrue(bool(graph.query(
                'ASK { GRAPH <%s> { <%s> <%s> ?s } }'
                % (real, message_iri(7), SCHEMA_PREDICATES['mentions']))))

    def test_reuses_iri_for_known_entity(self):
        def extractor(text):
            return [('Alice', SCHEMA_PREDICATES['knows'], 'Bob')]

        extract(1, 'Alice knows Bob.', extractor=extractor)
        extract(2, 'Alice knows Bob.', extractor=extractor)

        real = GRAPHS['real']
        with open_graph(self.path) as graph:
            # Alice keeps one IRI across both messages, so one name node.
            rows = list(graph.query(
                'SELECT ?s WHERE { GRAPH <%s> { ?s <%s> "Alice" } }'
                % (real, SCHEMA_PREDICATES['name'])))
            self.assertEqual(len(rows), 1)
            # The fact itself is held once, not duplicated.
            facts = list(graph.query(
                'SELECT ?s ?o WHERE { GRAPH <%s> { ?s <%s> ?o } }'
                % (real, SCHEMA_PREDICATES['knows'])))
            self.assertEqual(len(facts), 1)


if __name__ == '__main__':
    unittest.main()
