"""The extraction pass: turn a message into facts in the background.

Reads a message's text, extracts entities and events from it, resolves each
entity against the IRIs already in the `real` graph, and asserts the new facts
with the source message id. The extractor — the natural-language step — is
injectable so the resolve-and-assert flow stays deterministic and testable.
"""

import os

from .graph import open_graph


def default_extractor(text: str) -> list[tuple[str, str, str]]:
    """Extract `(subject, predicate, object)` facts from message text.

    A placeholder for the LLM extraction step. Returns nothing so an unwired
    deployment asserts nothing rather than guessing.
    """
    # ponytail: no-op until the LLM extractor lands; inject one via `extract`.
    return []


def extract(message_id: int, text: str, extractor=default_extractor):
    """Extract facts from a message and assert them into the `real` graph.

    Medium-agnostic and safe to run in the background: it opens the graph,
    runs the extractor over the text, and hands the facts to the graph, which
    resolves each entity to an existing IRI before asserting it.
    """
    graph_path = os.environ.get('GRAPH_PATH', 'graph.db')
    facts = extractor(text)
    if not facts:
        return
    with open_graph(graph_path) as graph:
        graph.extract_facts(message_id, facts)
