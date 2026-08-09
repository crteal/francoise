from contextlib import contextmanager

from pyoxigraph import DefaultGraph, Literal, NamedNode, Quad, Store

from françoise.vocab import (
    FR_PREDICATES,
    GRAPHS,
    PREDICATES,
    SCHEMA_PREDICATES,
    agent_iri,
    topic_iri,
)


class Graph:
    def __init__(self, store):
        self.store = store

    def assert_quad(
            self,
            subject: str,
            predicate: str,
            object: str,
            graph: str = None,
            literal: bool = False):
        if predicate not in PREDICATES:
            raise ValueError('unknown predicate: %s' % predicate)
        self.store.add(Quad(
            NamedNode(subject),
            NamedNode(predicate),
            Literal(object) if literal else NamedNode(object),
            NamedNode(graph) if graph else DefaultGraph()))

    def query(self, sparql: str):
        return self.store.query(sparql)

    def read_facts(self, agent_id: int, topics=(), limit: int = 20) -> list[str]:
        """Read the agent's facts from the `real` graph as readable lines.

        Returns the agent's own facts plus any facts about the given topic
        nodes, each rendered `subject predicate object` using the `name`
        literal of a node when it has one, else its IRI. pyoxigraph keeps no
        assertion time, so `limit` bounds the window rather than ordering it.
        """
        real = GRAPHS['real']
        subjects = [agent_iri(agent_id)] + [topic_iri(t) for t in topics]
        values = ' '.join('<%s>' % s for s in subjects)
        rows = self.query("""
            SELECT ?s ?p ?o
            WHERE {
                GRAPH <%s> { ?s ?p ?o }
                VALUES ?s { %s }
            } LIMIT %d
        """ % (real, values, limit))
        return [
            '%s %s %s' % (self._label(r['s']), self._label(r['p']), self._label(r['o']))
            for r in rows
        ]

    def _label(self, node) -> str:
        """A readable label for a node: its `name` literal, else its IRI/value."""
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, NamedNode):
            real = GRAPHS['real']
            names = list(self.query(
                'SELECT ?n WHERE { GRAPH <%s> { <%s> <%s> ?n } } LIMIT 1'
                % (real, node.value, SCHEMA_PREDICATES['name'])))
            if names:
                return names[0]['n'].value
            return node.value
        return str(node)

    def seed_persona(self, agent_id: int, name: str, interests=()):
        """Write an agent's persona facts into the `real` graph: its own
        name, and for each interest a topic node linked by a trait edge."""
        real = GRAPHS['real']
        agent = agent_iri(agent_id)
        self.assert_quad(
            agent, SCHEMA_PREDICATES['name'], name,
            graph=real, literal=True)
        for interest in interests:
            topic = topic_iri(interest)
            self.assert_quad(
                topic, SCHEMA_PREDICATES['name'], interest,
                graph=real, literal=True)
            self.assert_quad(
                agent, FR_PREDICATES['enjoys'], topic, graph=real)


@contextmanager
def open_graph(path: str):
    store = Store(path)
    try:
        yield Graph(store)
    finally:
        store.flush()
