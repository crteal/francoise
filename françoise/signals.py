"""External signals a persona can be grounded in.

A signal is a small structured fact about the persona's world (currently the
weather at its location) with a `topic`, a `place`, and a `time`, ready to fold
into prompt context.
"""

from datetime import date, datetime

import requests

OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'

# ponytail: fixed-date holidays only; add a lib (e.g. `holidays`) if moving
# feasts (Easter) or locale-specific days are ever needed.
HOLIDAYS = {
    (1, 1): "New Year's Day",
    (2, 14): "Valentine's Day",
    (7, 14): 'Bastille Day',
    (10, 31): 'Halloween',
    (12, 25): 'Christmas',
    (12, 31): "New Year's Eve",
}


def _season(when: date) -> str:
    """Northern-hemisphere season for a date, by month (meteorological)."""
    return ('winter', 'spring', 'summer', 'autumn')[(when.month % 12) // 3]


def weather_signal(latitude: float, longitude: float, place: str = None,
                   get=requests.get) -> dict:
    """Fetch current weather from Open-Meteo for a lat/long.

    Returns a signal with `topic='weather'`, the `place` label, the observation
    `time`, and the current `temperature` and `weather_code`. `get` is injected
    for testing.
    """
    response = get(OPEN_METEO_URL, params={
        'latitude': latitude,
        'longitude': longitude,
        'current': 'temperature_2m,weather_code',
    })
    response.raise_for_status()
    current = response.json().get('current', {})
    return {
        'topic': 'weather',
        'place': place or '%s,%s' % (latitude, longitude),
        'time': current.get('time') or datetime.now().isoformat(),
        'temperature': current.get('temperature_2m'),
        'weather_code': current.get('weather_code'),
    }


def calendar_signal(when: date = None) -> dict:
    """Seasonal and holiday signal for a date (defaults to today).

    Returns a signal with `topic='calendar'`, the `time`, the `season`, and the
    `holiday` name (or `None` when the date is not a known holiday).
    """
    when = when or date.today()
    return {
        'topic': 'calendar',
        'time': when.isoformat(),
        'season': _season(when),
        'holiday': HOLIDAYS.get((when.month, when.day)),
    }


def region_signals(graph, region: str, latitude: float, longitude: float,
                   when: date = None, get=requests.get, cache: dict = None):
    """Signals for a region, fetched once and asserted into the `world` graph.

    Fetches the weather and calendar signals for a region, asserts each into
    the graph's `world` graph, and caches them under `region` so a later call
    for the same region reuses them without hitting the provider again. Two
    agents in one region therefore share one fetch. `cache` is the per-run
    memo (a dict), `get` the injected weather provider.
    """
    cache = {} if cache is None else cache
    if region in cache:
        return cache[region]
    signals = [
        weather_signal(latitude, longitude, region, get=get),
        calendar_signal(when),
    ]
    for signal in signals:
        graph.assert_signal(region, signal)
    cache[region] = signals
    return signals


def _signal_terms(signal: dict) -> set[str]:
    """The lowercased string values of a signal, used to match the persona."""
    return {
        str(value).lower()
        for value in signal.values()
        if isinstance(value, str)
    }


def ground_signals(graph, agent_id: int, signals) -> list[dict]:
    """Keep only the signals that fit the agent's persona.

    A signal stays when one of its values matches a persona term: an interest
    edge, the home location, or a known topic (see `Graph.persona_terms`). A
    signal that matches nothing drops.
    """
    terms = graph.persona_terms(agent_id)
    return [s for s in signals if _signal_terms(s) & terms]


def default_model(persona: str, past_events, signal: dict) -> str:
    """Draft a first-person event from a grounded signal.

    A placeholder for the LLM synthesis step. Returns nothing so an unwired
    deployment synthesizes nothing rather than guessing. Inject a real model
    via `synthesize`.
    """
    # ponytail: no-op until the LLM model lands; inject one via `synthesize`.
    return ''


def synthesize(graph, agent_id: int, signal: dict, model=default_model) -> str:
    """Make a first-person synthetic event from a grounded world signal.

    Asks `model` for an event that fits the persona and the past events, checks
    it against the graph for a conflict (an identical event already asserted),
    and asserts it into the `synthetic` graph linked to the region's world
    node. Returns the event text, or '' when the model drafts nothing or the
    event conflicts. `model` is injected so the assert flow stays testable.
    """
    terms = graph.persona_terms(agent_id)
    persona = ', '.join(sorted(terms))
    text = model(persona, graph.read_events(agent_id), signal).strip()
    if not text:
        return ''
    region = signal.get('place', '')
    if not graph.assert_synthetic_event(agent_id, region, text):
        return ''
    return text


if __name__ == '__main__':
    xmas = calendar_signal(date(2026, 12, 25))
    assert xmas['topic'] == 'calendar'
    assert xmas['holiday'] == 'Christmas'
    assert xmas['season'] == 'winter'
    assert calendar_signal(date(2026, 8, 9))['holiday'] is None

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {'current': {
                'time': '2026-08-09T12:00',
                'temperature_2m': 21.3,
                'weather_code': 1,
            }}

    signal = weather_signal(48.85, 2.35, 'Paris', get=lambda *a, **k: _Resp())
    assert signal['topic'] == 'weather'
    assert signal['place'] == 'Paris'
    assert signal['time'] == '2026-08-09T12:00'
    print('ok')
