import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from françoise.chat import Provider


class TestProvider(unittest.TestCase):
    @patch('françoise.chat.litellm.completion')
    def test_chat_sends_request_and_returns_reply_text(self, mock_completion):
        mock_completion.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='Bonjour !'))])

        messages = [{'role': 'user', 'content': 'Hello'}]
        reply = Provider().chat(messages, model='ollama/llama3')

        self.assertEqual(reply, 'Bonjour !')
        mock_completion.assert_called_once_with(
            messages=messages, model='ollama/llama3')

    @patch('françoise.chat.litellm.completion')
    def test_stream_yields_content_chunks(self, mock_completion):
        def delta(content):
            return SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])

        # a trailing None delta (finish chunk) is skipped
        mock_completion.return_value = iter(
            [delta('Bon'), delta('jour'), delta(None)])

        messages = [{'role': 'user', 'content': 'Hello'}]
        chunks = list(Provider().stream(messages, model='ollama/llama3'))

        self.assertEqual(chunks, ['Bon', 'jour'])
        mock_completion.assert_called_once_with(
            messages=messages, stream=True, model='ollama/llama3')

    @patch.dict(os.environ, {'OPENAI_CRED': 'sk-secret'})
    @patch('françoise.chat.litellm.completion')
    def test_chat_reads_key_by_reference(self, mock_completion):
        mock_completion.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='Bonjour !'))])

        messages = [{'role': 'user', 'content': 'Hello'}]
        Provider().chat(messages, model='gpt-4', credential_ref='OPENAI_CRED')

        mock_completion.assert_called_once_with(
            messages=messages, model='gpt-4', api_key='sk-secret')

    @patch('françoise.chat.litellm.completion')
    @patch('françoise.chat.anthropic.Anthropic')
    def test_chat_uses_native_anthropic_path_with_caching(
            self, mock_anthropic, mock_completion):
        mock_anthropic.return_value.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(text='Bonjour !')])

        messages = [
            {'role': 'system', 'content': 'You are Françoise.'},
            {'role': 'user', 'content': 'Hello'}]
        reply = Provider().chat(messages, model='anthropic/claude-opus-4-8')

        self.assertEqual(reply, 'Bonjour !')
        # The native path runs, not LiteLLM.
        mock_completion.assert_not_called()

        _, kwargs = mock_anthropic.return_value.messages.create.call_args
        # The bare model id reaches the SDK, the system prompt is lifted out
        # of the turns, and it is cached.
        self.assertEqual(kwargs['model'], 'claude-opus-4-8')
        self.assertEqual(kwargs['messages'], [{'role': 'user', 'content': 'Hello'}])
        self.assertEqual(kwargs['system'], [{
            'type': 'text',
            'text': 'You are Françoise.',
            'cache_control': {'type': 'ephemeral'},
        }])


if __name__ == '__main__':
    unittest.main()
