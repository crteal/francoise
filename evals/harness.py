"""Minimal eval harness: run fixtures against a model config, record a score.

A fixture is a JSON list of cases; each case is `{"input": str, "expected": str}`.
`run` sends each input through the Provider under the given config and scores the
reply. The default score is exact match; later evals pass their own `score` fn.
"""
import json
import sys
from collections.abc import Callable, Sequence

from françoise.chat import Provider


def load_fixtures(path: str) -> list[dict]:
    """Load a JSON fixture file into a list of cases."""
    with open(path) as f:
        return json.load(f)


def exact_match(reply: str, expected: str) -> float:
    """Score 1.0 on an exact (trimmed) match, else 0.0."""
    return 1.0 if reply.strip() == expected.strip() else 0.0


def run(
        cases: Sequence[dict],
        config: dict,
        score: Callable[[str, str], float] = exact_match,
        provider: Provider = None) -> float:
    """Run each case through the config and return the mean score."""
    provider = provider or Provider()
    if not cases:
        return 0.0
    total = 0.0
    for case in cases:
        reply = provider.chat(
            [{'role': 'user', 'content': case['input']}], **config)
        total += score(reply, case['expected'])
    return total / len(cases)


def main(argv: Sequence[str] = None) -> int:
    """CLI: `python -m evals.harness <fixtures.json> <model>` prints the score."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print('usage: python -m evals.harness <fixtures.json> <model>')
        return 1
    fixtures_path, model = argv
    score = run(load_fixtures(fixtures_path), {'model': model})
    print('score: %.3f' % score)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
