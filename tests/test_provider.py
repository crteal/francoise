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


if __name__ == '__main__':
    unittest.main()
