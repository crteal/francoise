"""External signals a persona can be grounded in.

A signal is a small structured fact about the persona's world (currently the
weather at its location) with a `topic`, a `place`, and a `time`, ready to fold
into prompt context.
"""

from datetime import datetime

import requests

OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'


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


if __name__ == '__main__':
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
