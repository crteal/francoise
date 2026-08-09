import unittest

from evals.harness import contains, load_fixtures, run


class FakeProvider:
    """Replies with a fixed persona description for every input."""

    def __init__(self, reply):
        self.reply = reply

    def chat(self, messages, **kwargs):
        return self.reply


class TestIdentityEval(unittest.TestCase):
    def setUp(self):
        self.cases = load_fixtures('evals/fixtures/identity.json')

    def test_fixtures_ask_for_persona_facts(self):
        self.assertTrue(self.cases)
        expected = {c['expected'] for c in self.cases}
        self.assertIn('Paris', expected)
        self.assertIn('French', expected)

    def test_passes_for_correct_persona(self):
        reply = "I am Françoise. I live in Paris and my native language is French."
        score = run(self.cases, {'model': 'test'}, score=contains,
                    provider=FakeProvider(reply))
        self.assertEqual(score, 1.0)

    def test_fails_for_wrong_fact(self):
        reply = "I am Bob. I live in Berlin and my native language is German."
        score = run(self.cases, {'model': 'test'}, score=contains,
                    provider=FakeProvider(reply))
        self.assertEqual(score, 0.0)

    def test_contains_is_case_insensitive(self):
        self.assertEqual(contains('i live in paris', 'Paris'), 1.0)
        self.assertEqual(contains('i live in Berlin', 'Paris'), 0.0)


if __name__ == '__main__':
    unittest.main()
