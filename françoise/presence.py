"""Compute an agent's presence state from its local time and age.

The state (`asleep`, `school`, `free`, or `busy`) is derived from the hour in
the agent's own timezone and an age-appropriate schedule, so the agent appears
awake, in class, or occupied at plausible times of day.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

STATES = ('asleep', 'school', 'free', 'busy')


def _schedule(age) -> dict:
    """Map each hour (0-23) to a state for the given age.

    Children have earlier bedtimes and school hours; adults work instead of
    attending school. `age` may be None or non-numeric, treated as an adult.
    """
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 30
    child = age < 18
    hours = {}
    for h in range(24):
        if child:
            if h < 7 or h >= 21:
                state = 'asleep'
            elif 8 <= h < 15:
                state = 'school'
            else:
                state = 'free'
        else:
            if h < 6 or h >= 23:
                state = 'asleep'
            elif 9 <= h < 17:
                state = 'busy'
            else:
                state = 'free'
        hours[h] = state
    return hours


def presence_state(agent: dict, now: datetime = None) -> str:
    """Return the agent's presence state for `now` (defaults to current time).

    Reads the local hour with the agent's `timezone` (falling back to UTC) and
    looks it up in the age schedule.
    """
    tz = ZoneInfo(agent.get('timezone') or 'UTC')
    if now is None:
        now = datetime.now(tz)
    else:
        now = now.astimezone(tz)
    return _schedule(agent.get('age'))[now.hour]


if __name__ == '__main__':
    child = {'timezone': 'UTC', 'age': 10}
    at = lambda h: datetime(2026, 1, 1, h, tzinfo=ZoneInfo('UTC'))
    assert presence_state(child, at(2)) == 'asleep'
    assert presence_state(child, at(16)) == 'free'
    assert presence_state(child, at(10)) == 'school'
    print('ok')
