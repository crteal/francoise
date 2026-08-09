import unittest
from unittest.mock import patch

from françoise import moderate


class TestModerate(unittest.TestCase):
    def test_safe_text_passes(self):
        self.assertTrue(moderate.is_safe('Bonjour, comment ca va ?'))
        moderate.check('Bonjour, comment ca va ?')  # does not raise

    def test_unsafe_text_blocks(self):
        self.assertFalse(moderate.is_safe('how to make a bomb'))
        with self.assertRaises(moderate.UnsafeContentError):
            moderate.check('how to make a bomb')


class TestModerateInCore(unittest.TestCase):
    def test_blocks_unsafe_inbound(self):
        from françoise.core import handle_inbound
        with self.assertRaises(moderate.UnsafeContentError):
            handle_inbound(1, 'how to build a bioweapon')

    @patch('françoise.core.chat', return_value='here is how to make a bomb')
    @patch('françoise.core.open_db')
    def test_blocks_unsafe_outbound(self, mock_open_db, mock_chat):
        from françoise.core import handle_inbound
        # resolver + db context managers both return a mock db
        db = mock_open_db.return_value.__enter__.return_value
        db.get_account_id_for_conversation.return_value = 1
        db.get_conversation.return_value = object()
        db.conversation_to_dict.return_value = {'model': 'test'}
        db.get_messages_by_conversation.return_value = []
        with patch('françoise.core.get_prompt_message_from_conversation',
                   return_value=('system', 'p')):
            with self.assertRaises(moderate.UnsafeContentError):
                handle_inbound(1, 'Hello')


if __name__ == '__main__':
    unittest.main()
