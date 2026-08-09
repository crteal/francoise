from collections.abc import Sequence
import litellm
import requests


class Provider:
    """Thin seam over LiteLLM so we can reach many model hosts through one interface."""

    def chat(self, messages: Sequence[dict[str, str]], **kwargs) -> str:
        response = litellm.completion(messages=list(messages), **kwargs)
        return response.choices[0].message.content


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
