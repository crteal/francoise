import unittest

from evals.harness import load_fixtures, recall, run_memory


class RecallingProvider:
    """Replies with the fact the user stated in an earlier turn."""

    def chat(self, messages, **kwargs):
        for m in messages:
            if m['role'] == 'user' and '.' in m['content']:
                return 'You told me: ' + m['content']
        return 'I do not recall.'


class MisattributingProvider:
    """Treats a synthetic (invented) fact as the user's own."""

    def __init__(self, synthetic):
        self.synthetic = synthetic

    def chat(self, messages, **kwargs):
        return 'You told me your fact is %s.' % self.synthetic


class TestMemoryEval(unittest.TestCase):
    def setUp(self):
        self.cases = load_fixtures('evals/fixtures/memory.json')

    def test_fixtures_are_multi_turn(self):
        self.assertTrue(self.cases)
        for case in self.cases:
            self.assertGreaterEqual(len(case['turns']), 2)
            self.assertIn('expected', case)

    def test_passes_when_persona_recalls(self):
        score = run_memory(self.cases, {'model': 'test'},
                           provider=RecallingProvider())
        self.assertEqual(score, 1.0)

    def test_fails_on_misattributed_synthetic_fact(self):
        score = run_memory(self.cases, {'model': 'test'},
                           provider=MisattributingProvider('Idefix'))
        self.assertEqual(score, 0.0)

    def test_recall_flags_forbidden_fact(self):
        self.assertEqual(recall('your dog is Milou', 'Milou'), 1.0)
        self.assertEqual(recall('your dog is Idefix', 'Milou', 'Idefix'), 0.0)
        self.assertEqual(recall('I forget', 'Milou'), 0.0)


if __name__ == '__main__':
    unittest.main()
