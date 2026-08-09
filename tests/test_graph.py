import shutil
import tempfile
import unittest

from françoise.graph import open_graph
from françoise.vocab import FR_PREDICATES


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


if __name__ == '__main__':
    unittest.main()
