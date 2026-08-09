from collections.abc import Iterator, Sequence
import os
import anthropic
import litellm
import requests


def get_secret(credential_ref: str) -> str:
    """Resolve a credential reference to its key from the environment.

    Keeps keys out of database rows: a row holds only the reference, and the
    key lives in the secret store (the environment) read at call time.
    """
    key = os.environ.get(credential_ref)
    if not key:
        raise Exception('secret for `%s` is unspecified' % credential_ref)
    return key


def is_anthropic_model(model: str) -> bool:
    """Select the native path for Claude configs (LiteLLM's `anthropic/` prefix)."""
    return bool(model) and model.startswith('anthropic/')


def split_system(messages: Sequence[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    """Separate the system prompt from the conversation turns.

    The Anthropic Messages API takes `system` as a top-level field, not a role
    inside `messages`, so we lift it out here.
    """
    system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
    turns = [m for m in messages if m['role'] != 'system']
    return system, turns


class Provider:
    """Thin seam over LiteLLM so we can reach many model hosts through one interface."""

    def chat(
            self,
            messages: Sequence[dict[str, str]],
            credential_ref: str = None,
            **kwargs) -> str:
        if is_anthropic_model(kwargs.get('model')):
            return self._anthropic_chat(messages, credential_ref, **kwargs)
        if credential_ref is not None:
            kwargs['api_key'] = get_secret(credential_ref)
        response = litellm.completion(messages=list(messages), **kwargs)
        return response.choices[0].message.content

    def _anthropic_chat(
            self,
            messages: Sequence[dict[str, str]],
            credential_ref: str = None,
            **kwargs) -> str:
        """Native Anthropic path: cache the system prompt to cut repeat cost."""
        api_key = get_secret(credential_ref) if credential_ref is not None else None
        # Strip LiteLLM's `anthropic/` prefix to the bare model id the SDK wants.
        model = kwargs.pop('model').removeprefix('anthropic/')
        kwargs.setdefault('max_tokens', 16000)
        system, turns = split_system(messages)

        response = anthropic.Anthropic(api_key=api_key).messages.create(
            model=model,
            system=[{
                'type': 'text',
                'text': system,
                'cache_control': {'type': 'ephemeral'},
            }],
            messages=turns,
            **kwargs)
        return response.content[0].text

    def stream(
            self,
            messages: Sequence[dict[str, str]],
            credential_ref: str = None,
            **kwargs) -> Iterator[str]:
        """Yield the reply as a uniform iterator of content chunks."""
        if credential_ref is not None:
            kwargs['api_key'] = get_secret(credential_ref)
        response = litellm.completion(
            messages=list(messages), stream=True, **kwargs)
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content


def message_tuple_to_dict(values: tuple[str, str]):
    return dict(zip(('role', 'content'), values))


def get_prompt_message(s: str) -> tuple[str, str]:
    return ('system', s)


def create_prompt_from_conversation(conversation: dict[str, str]) -> str:
    return conversation.get('agent_prompt').format(**conversation)


def get_prompt_message_from_conversation(conversation: dict[str, str]) -> tuple[str, str]:
    content = create_prompt_from_conversation(conversation)
    return get_prompt_message(content)


def chat(messages: Sequence[dict[str, str]], **kwargs):
    if not messages:
        raise Exception('messages is empty or unspecified')

    model = kwargs.get('model')
    if not model:
        raise Exception('model is unspecified')

    url = kwargs.get('url')
    if not url:
        raise Exception('url is unspecified')

    data = {
      "model": model,
      "messages": messages,
      "stream": False
    }

    response = requests.post(url, json=data)
    # throw an error if we got a failure from the LLM
    response.raise_for_status()

    json = response.json()
    return json['message']['content']
