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
