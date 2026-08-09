import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from françoise.app import presence_fragment
from françoise.presence import presence_label, presence_local_time


def _at(hour, tz='UTC'):
    return datetime(2026, 1, 1, hour, tzinfo=ZoneInfo(tz))


class TestPresenceIndicator(unittest.TestCase):
    def setUp(self):
        self.adult = {'timezone': 'UTC', 'age': 34}

    def test_label_shows_sleeping(self):
        # Open the chat for a sleeping persona: header shows `Sleeping`.
        self.assertEqual(presence_label(self.adult, _at(2)), 'Sleeping')

    def test_label_updates_when_free(self):
        # Move to a free time and check that the label updates.
        self.assertEqual(presence_label(self.adult, _at(20)), 'Free')

    def test_local_time_in_agent_timezone(self):
        # 02:00 UTC is 03:00 in Paris.
        agent = {'timezone': 'Europe/Paris', 'age': 34}
        self.assertEqual(presence_local_time(agent, _at(2)), '03:00')

    def test_fragment_is_out_of_band(self):
        fragment = presence_fragment(1, self.adult)
        self.assertIn('id="presence-1"', fragment)
        self.assertIn('hx-swap-oob="true"', fragment)


if __name__ == '__main__':
    unittest.main()
