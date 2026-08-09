import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from françoise.presence import presence_state


def _at(hour, tz='UTC'):
    return datetime(2026, 1, 1, hour, tzinfo=ZoneInfo(tz))


class TestPresence(unittest.TestCase):
    def setUp(self):
        self.child = {'timezone': 'UTC', 'age': 10}
        self.adult = {'timezone': 'UTC', 'age': 34}

    def test_child_asleep_at_night(self):
        self.assertEqual(presence_state(self.child, _at(2)), 'asleep')

    def test_child_free_in_afternoon(self):
        self.assertEqual(presence_state(self.child, _at(16)), 'free')

    def test_child_at_school(self):
        self.assertEqual(presence_state(self.child, _at(10)), 'school')

    def test_adult_busy_during_day(self):
        self.assertEqual(presence_state(self.adult, _at(10)), 'busy')

    def test_timezone_is_applied(self):
        # 02:00 UTC is 03:00 in Paris; still night -> asleep
        self.assertEqual(
            presence_state({'timezone': 'Europe/Paris', 'age': 34}, _at(2)),
            'asleep')


if __name__ == '__main__':
    unittest.main()
