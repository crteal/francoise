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


class TestMinorSafety(unittest.TestCase):
    def test_blocks_logs_and_flags(self):
        blocked = 'sexual roleplay with a child'
        with patch.object(moderate, 'flag_account') as flag:
            with self.assertLogs(moderate.logger, level='WARNING') as logs:
                with self.assertRaises(moderate.MinorSafetyError):
                    moderate.minor_safety(blocked, account_id=7)
            flag.assert_called_once_with(7)
        self.assertTrue(any('minor-safety block' in m for m in logs.output))

    def test_check_routes_before_permissive_policy(self):
        # A MinorSafetyError (not a plain UnsafeContentError) proves the
        # specialized check ran instead of the permissive gate.
        with patch.object(moderate, 'flag_account'):
            with self.assertLogs(moderate.logger, level='WARNING'):
                with self.assertRaises(moderate.MinorSafetyError):
                    moderate.check('naked child', account_id=1)

    def test_safe_text_passes_minor_safety(self):
        moderate.minor_safety('Bonjour, comment ca va ?')  # does not raise


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
