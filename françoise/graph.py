from contextlib import contextmanager

from pyoxigraph import NamedNode, Quad, Store

from françoise.vocab import PREDICATES


class Graph:
    def __init__(self, store):
        self.store = store

    def assert_quad(self, subject: str, predicate: str, object: str):
        if predicate not in PREDICATES:
            raise ValueError('unknown predicate: %s' % predicate)
        self.store.add(Quad(
            NamedNode(subject),
            NamedNode(predicate),
            NamedNode(object)))

    def query(self, sparql: str):
        return self.store.query(sparql)


@contextmanager
def open_graph(path: str):
    store = Store(path)
    try:
        yield Graph(store)
    finally:
        store.flush()
