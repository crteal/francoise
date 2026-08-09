import shutil
import tempfile
import unittest
from datetime import date

from françoise.graph import open_graph
from françoise.signals import (
    calendar_signal,
    ground_signals,
    region_signals,
    weather_signal,
)
from françoise.vocab import FR_PREDICATES, GRAPHS, place_iri


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


class TestRegionSignals(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)

    def _counting_get(self):
        calls = []

        def get(*a, **k):
            calls.append((a, k))
            return _Resp({'current': {
                'time': '2026-08-09T12:00',
                'temperature_2m': 21.3,
                'weather_code': 1,
            }})

        return get, calls

    def test_two_agents_in_one_region_share_one_fetch(self):
        get, calls = self._counting_get()
        cache = {}
        with open_graph(self.path) as graph:
            # Two agents, same region, one shared cache.
            region_signals(graph, 'Paris', 48.85, 2.35, get=get, cache=cache)
            region_signals(graph, 'Paris', 48.85, 2.35, get=get, cache=cache)

        self.assertEqual(len(calls), 1)

    def test_world_graph_holds_the_signals(self):
        get, _ = self._counting_get()
        with open_graph(self.path) as graph:
            region_signals(graph, 'Paris', 48.85, 2.35, get=get)
            rows = list(graph.query(
                'SELECT ?o WHERE { GRAPH <%s> { <%s> <%s> ?o } }'
                % (GRAPHS['world'], place_iri('Paris'), FR_PREDICATES['signal'])))

        # Both the weather and calendar signals are held for the region.
        self.assertEqual(len(rows), 2)


class TestGroundSignals(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)

    def test_keeps_only_the_matching_signal(self):
        matching = {'topic': 'cinema', 'note': 'a new film'}
        non_matching = {'topic': 'weather', 'note': 'it rains'}
        with open_graph(self.path) as graph:
            graph.seed_persona(1, 'Boku', interests=['cinema'])

            grounded = ground_signals(graph, 1, [matching, non_matching])

        self.assertEqual(grounded, [matching])


if __name__ == '__main__':
    unittest.main()
