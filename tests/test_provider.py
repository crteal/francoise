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

    @patch.dict(os.environ, {'OPENAI_CRED': 'sk-secret'})
    @patch('françoise.chat.litellm.completion')
    def test_chat_reads_key_by_reference(self, mock_completion):
        mock_completion.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='Bonjour !'))])

        messages = [{'role': 'user', 'content': 'Hello'}]
        Provider().chat(messages, model='gpt-4', credential_ref='OPENAI_CRED')

        mock_completion.assert_called_once_with(
            messages=messages, model='gpt-4', api_key='sk-secret')


if __name__ == '__main__':
    unittest.main()
