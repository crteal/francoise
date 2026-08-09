"""The vocabulary: Schema.org classes and predicates, local fr: predicates,
and the names of the provenance graphs. Everything lives here in one place."""

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
