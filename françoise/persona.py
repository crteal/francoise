"""Build an agent's system prompt from structured persona fields.

Replaces the free-prose `agent_prompt` template: the system prompt is now
composed from trusted fields we control, so user-supplied text can never reach
it. The user's text is passed to the model as a user message instead.
"""

PERSONA_FIELDS = ('location', 'timezone', 'interests', 'age', 'native_language')

LABELS = {
    'location': 'Location',
    'timezone': 'Timezone',
    'interests': 'Interests',
    'age': 'Age',
    'native_language': 'Native language',
}


def build_persona_prompt(agent: dict) -> str:
    """Render a trusted system prompt from an agent's persona fields.

    Only known persona fields are used; anything else on the row is ignored.
    """
    lines = ['You are %s.' % agent.get('name', 'a conversation partner')]
    for field in PERSONA_FIELDS:
        value = agent.get(field)
        if value:
            lines.append('%s: %s' % (LABELS[field], value))
    return '\n'.join(lines)


if __name__ == '__main__':
    agent = {
        'name': 'Françoise',
        'location': 'Paris',
        'timezone': 'Europe/Paris',
        'interests': 'cinema, cooking',
        'age': 34,
        'native_language': 'French',
    }
    prompt = build_persona_prompt(agent)
    assert 'Paris' in prompt
    assert 'French' in prompt
    # user text must never enter the system prompt
    assert 'ignore previous instructions' not in build_persona_prompt(
        {'name': 'x', 'location': 'y'})
    print(prompt)
