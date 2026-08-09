from contextlib import contextmanager

from pyoxigraph import DefaultGraph, Literal, NamedNode, Quad, Store

from françoise.vocab import (
    FR,
    FR_PREDICATES,
    GRAPHS,
    PREDICATES,
    SCHEMA_PREDICATES,
    agent_iri,
    entity_iri,
    message_iri,
    place_iri,
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

    def resolve_iri(self, name: str) -> str:
        """The IRI of an existing entity with this `name`, else a fresh one.

        Matches the `name` literal of any node already in the `real` graph so a
        known entity keeps its IRI instead of being asserted twice.
        """
        real = GRAPHS['real']
        rows = list(self.query(
            'SELECT ?s WHERE { GRAPH <%s> { ?s <%s> %s } } LIMIT 1'
            % (real, SCHEMA_PREDICATES['name'], Literal(name))))
        if rows:
            return rows[0]['s'].value
        return entity_iri(name)

    def extract_facts(self, message_id: int, facts):
        """Assert extracted `(subject, predicate, object)` facts into `real`.

        Each subject and object is resolved to an existing IRI when its name is
        already known, else minted fresh and given a `name` literal. Every
        asserted subject is linked to its source message so the fact's
        provenance is kept. `facts` is an iterable of name/predicate/name
        triples, e.g. from an extractor over the message text.
        """
        real = GRAPHS['real']
        source = message_iri(message_id)
        for subject_name, predicate, object_name in facts:
            subject = self.resolve_iri(subject_name)
            object = self.resolve_iri(object_name)
            self._ensure_name(subject, subject_name)
            self._ensure_name(object, object_name)
            self.assert_quad(subject, predicate, object, graph=real)
            self.assert_quad(
                source, SCHEMA_PREDICATES['mentions'], subject, graph=real)

    def _ensure_name(self, iri: str, name: str):
        """Give a node its `name` literal in `real` if it lacks one."""
        real = GRAPHS['real']
        if not bool(self.query(
                'ASK { GRAPH <%s> { <%s> <%s> ?n } }'
                % (real, iri, SCHEMA_PREDICATES['name']))):
            self.assert_quad(
                iri, SCHEMA_PREDICATES['name'], name, graph=real, literal=True)

    def assert_signal(self, region: str, signal: dict):
        """Assert a world signal into the `world` graph, keyed by region.

        Links the region's place node to a `signal` literal rendering the
        signal dict, so the graph holds each real-world fact fetched for a
        region (e.g. its weather or calendar).
        """
        summary = ' '.join(
            '%s=%s' % (key, signal[key]) for key in sorted(signal))
        self.assert_quad(
            place_iri(region), FR_PREDICATES['signal'], summary,
            graph=GRAPHS['world'], literal=True)

    def persona_terms(self, agent_id: int) -> set[str]:
        """The agent's grounding terms: its interests, home location, and the
        names of known topics, lowercased.

        Read from the `real` graph, these are the terms a world signal must
        touch to fit the persona: an interest edge (`enjoys` a named topic),
        the `homeLocation` name, or any known topic node's name.
        """
        real = GRAPHS['real']
        agent = agent_iri(agent_id)
        rows = self.query("""
            SELECT ?name WHERE { GRAPH <%s> {
                { <%s> <%s> ?t . ?t <%s> ?name }
                UNION { <%s> <%s> ?h . ?h <%s> ?name }
                UNION { ?t <%s> ?name . FILTER(STRSTARTS(STR(?t), "%s")) }
            } }
        """ % (
            real,
            agent, FR_PREDICATES['enjoys'], SCHEMA_PREDICATES['name'],
            agent, SCHEMA_PREDICATES['homeLocation'], SCHEMA_PREDICATES['name'],
            SCHEMA_PREDICATES['name'], FR + 'topic/',
        ))
        return {r['name'].value.lower() for r in rows}

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
