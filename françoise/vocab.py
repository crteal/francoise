"""The vocabulary: Schema.org classes and predicates, local fr: predicates,
and the names of the provenance graphs. Everything lives here in one place."""

from urllib.parse import quote

SCHEMA = 'https://schema.org/'
FR = 'https://françoise.example/vocab#'

# Schema.org classes we use.
CLASSES = {
    'Person': SCHEMA + 'Person',
    'Organization': SCHEMA + 'Organization',
    'Place': SCHEMA + 'Place',
    'Event': SCHEMA + 'Event',
    'CreativeWork': SCHEMA + 'CreativeWork',
}

# Schema.org predicates we use.
SCHEMA_PREDICATES = {
    'name': SCHEMA + 'name',
    'knows': SCHEMA + 'knows',
    'memberOf': SCHEMA + 'memberOf',
    'homeLocation': SCHEMA + 'homeLocation',
    'mentions': SCHEMA + 'mentions',
}

# Local fr: predicates.
FR_PREDICATES = {
    'enjoys': FR + 'enjoys',
    'practices': FR + 'practices',
    'learning': FR + 'learning',
}

# Every predicate that may appear in a quad, keyed by its full IRI.
PREDICATES = frozenset(SCHEMA_PREDICATES.values()) | frozenset(FR_PREDICATES.values())

# The provenance graphs.
GRAPHS = {
    'real': FR + 'graph/real',
    'world': FR + 'graph/world',
    'synthetic': FR + 'graph/synthetic',
    'inferred': FR + 'graph/inferred',
}


def agent_iri(agent_id: int) -> str:
    """The IRI for an agent's self node."""
    return FR + 'agent/%d' % agent_id


def topic_iri(interest: str) -> str:
    """The IRI for an interest's topic node."""
    return FR + 'topic/' + quote(interest.strip().lower(), safe='')


def entity_iri(name: str) -> str:
    """A fresh IRI for an entity, minted from its name."""
    return FR + 'entity/' + quote(name.strip().lower(), safe='')


def message_iri(message_id: int) -> str:
    """The IRI for a source message node."""
    return FR + 'message/%d' % message_id
