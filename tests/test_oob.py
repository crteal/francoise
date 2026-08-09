import unittest

from françoise.app import reply_fragment, unread_badge_fragment


class TestOobFragments(unittest.TestCase):
    def test_reply_appends_to_open_conversation(self):
        fragment = reply_fragment(1, 'Bonjour !')
        self.assertIn('id="messages-1"', fragment)
        self.assertIn('hx-swap-oob="beforeend"', fragment)
        self.assertIn('Bonjour !', fragment)

    def test_reply_escapes_message(self):
        fragment = reply_fragment(1, '<script>')
        self.assertNotIn('<script>', fragment)
        self.assertIn('&lt;script&gt;', fragment)

    def test_unread_badge_raises_count_on_background_conversation(self):
        # Open conversation one; a reply arrives for conversation two.
        badge = unread_badge_fragment(2, 3)
        self.assertIn('id="unread-2"', badge)
        self.assertIn('hx-swap-oob="true"', badge)
        self.assertIn('>3<', badge)


if __name__ == '__main__':
    unittest.main()
