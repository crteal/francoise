from collections.abc import Iterator, Sequence
import os
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


class Provider:
    """Thin seam over LiteLLM so we can reach many model hosts through one interface."""

    def chat(
            self,
            messages: Sequence[dict[str, str]],
            credential_ref: str = None,
            **kwargs) -> str:
        if credential_ref is not None:
            kwargs['api_key'] = get_secret(credential_ref)
        response = litellm.completion(messages=list(messages), **kwargs)
        return response.choices[0].message.content

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
