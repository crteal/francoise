import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from evals.harness import exact_match, load_fixtures, main, run


class FakeProvider:
    def __init__(self, reply):
        self.reply = reply

    def chat(self, messages, **kwargs):
        return self.reply


class TestHarness(unittest.TestCase):
    def test_load_fixtures_reads_smoke_cases(self):
        cases = load_fixtures('evals/fixtures/smoke.json')
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0]['input'], 'Say bonjour')

    def test_run_scores_all_correct(self):
        cases = [{'input': 'x', 'expected': 'Bonjour'}]
        score = run(cases, {'model': 'test'}, provider=FakeProvider('Bonjour'))
        self.assertEqual(score, 1.0)

    def test_run_scores_wrong_reply(self):
        cases = [{'input': 'x', 'expected': 'Bonjour'}]
        score = run(cases, {'model': 'test'}, provider=FakeProvider('Salut'))
        self.assertEqual(score, 0.0)

    def test_exact_match_trims_whitespace(self):
        self.assertEqual(exact_match('  Bonjour \n', 'Bonjour'), 1.0)

    def test_main_prints_a_score(self):
        with patch('evals.harness.Provider', return_value=FakeProvider('Bonjour')):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(['evals/fixtures/smoke.json', 'test-model'])
        self.assertEqual(code, 0)
        self.assertIn('score:', out.getvalue())


if __name__ == '__main__':
    unittest.main()
