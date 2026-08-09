import asyncio
import unittest

from françoise.app import App


class TestChannels(unittest.TestCase):
    def test_each_user_has_a_separate_channel(self):
        app = App(DATABASE_URL=':memory:')
        get_channel = app.state.get_channel

        one = get_channel(1)
        two = get_channel(2)

        self.assertIsNot(one, two)
        # same user reuses the same channel
        self.assertIs(one, get_channel(1))

    def test_event_routes_to_only_one_user(self):
        app = App(DATABASE_URL=':memory:')
        get_channel = app.state.get_channel

        asyncio.run(get_channel(1).put('hello'))

        self.assertEqual(get_channel(1).qsize(), 1)
        # user two receives nothing
        self.assertEqual(get_channel(2).qsize(), 0)


if __name__ == '__main__':
    unittest.main()
