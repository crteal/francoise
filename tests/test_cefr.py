import unittest

from evals.harness import CEFR_LEVELS, cefr_level, level_fit, load_fixtures, run


class LevelledProvider:
    """Replies with a fixed sentence-length band per input target level."""

    # Word counts per sentence chosen to land mid-bucket for each level.
    _reply = {
        'A1': ' '.join(['word'] * 4) + '.',    # wps 4  -> A1 (<=6)
        'A2': ' '.join(['word'] * 8) + '.',    # wps 8  -> A2 (<=9)
        'B1': ' '.join(['word'] * 11) + '.',   # wps 11 -> B1 (<=12)
        'B2': ' '.join(['word'] * 14) + '.',   # wps 14 -> B2 (<=16)
        'C1': ' '.join(['word'] * 18) + '.',   # wps 18 -> C1 (<=20)
        'C2': ' '.join(['word'] * 24) + '.',   # wps 24 -> C2 (>20)
    }

    def chat(self, messages, **kwargs):
        target = messages[-1]['content'].strip().rstrip('.').split()[-1]
        return self._reply[target]


class TestCefrEval(unittest.TestCase):
    def setUp(self):
        self.cases = load_fixtures('evals/fixtures/cefr.json')

    def test_fixtures_cover_every_level(self):
        expected = [c['expected'] for c in self.cases]
        self.assertEqual(expected, list(CEFR_LEVELS))

    def test_cefr_level_buckets_by_sentence_length(self):
        self.assertEqual(cefr_level('I like cats.'), 'A1')
        long = ' '.join(['word'] * 30) + '.'
        self.assertEqual(cefr_level(long), 'C2')

    def test_cefr_level_empty_reply(self):
        self.assertEqual(cefr_level(''), 'A1')

    def test_level_fit_matches_expected(self):
        self.assertEqual(level_fit('I like cats.', 'A1'), 1.0)
        self.assertEqual(level_fit('I like cats.', 'C2'), 0.0)

    def test_run_scores_each_level(self):
        score = run(self.cases, {'model': 'test'}, score=level_fit,
                    provider=LevelledProvider())
        self.assertEqual(score, 1.0)


if __name__ == '__main__':
    unittest.main()
