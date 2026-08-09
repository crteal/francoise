import unittest
from datetime import date

from françoise.signals import calendar_signal, weather_signal


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class TestSignals(unittest.TestCase):
    def _get(self, payload):
        return lambda *a, **k: _Resp(payload)

    def test_returns_weather_signal(self):
        get = self._get({'current': {
            'time': '2026-08-09T12:00',
            'temperature_2m': 21.3,
            'weather_code': 1,
        }})
        signal = weather_signal(48.85, 2.35, 'Paris', get=get)
        self.assertEqual(signal['topic'], 'weather')

    def test_signal_holds_place_and_time(self):
        get = self._get({'current': {
            'time': '2026-08-09T12:00',
            'temperature_2m': 21.3,
            'weather_code': 1,
        }})
        signal = weather_signal(48.85, 2.35, 'Paris', get=get)
        self.assertEqual(signal['place'], 'Paris')
        self.assertEqual(signal['time'], '2026-08-09T12:00')

    def test_place_defaults_to_coordinates(self):
        get = self._get({'current': {'time': '2026-08-09T12:00'}})
        signal = weather_signal(48.85, 2.35, get=get)
        self.assertEqual(signal['place'], '48.85,2.35')


class TestCalendarSignal(unittest.TestCase):
    def test_marks_a_holiday(self):
        signal = calendar_signal(date(2026, 12, 25))
        self.assertEqual(signal['topic'], 'calendar')
        self.assertEqual(signal['holiday'], 'Christmas')

    def test_holiday_is_none_off_holiday(self):
        signal = calendar_signal(date(2026, 8, 9))
        self.assertIsNone(signal['holiday'])

    def test_reports_the_season(self):
        signal = calendar_signal(date(2026, 8, 9))
        self.assertEqual(signal['season'], 'summer')
        self.assertEqual(signal['time'], '2026-08-09')


if __name__ == '__main__':
    unittest.main()
