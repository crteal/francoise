import os
import tempfile
import unittest

from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from françoise.app import App
from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestStreamRoute(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        upgrade_to_head(self.db_path)
        password_hash = PasswordHasher().hash('correct horse')
        with open_db(self.db_path) as db:
            account = db.create_account('Acme')
        with open_db(self.db_path, account_id=account[0]) as db:
            self.user = db.create_user(
                'Alice', 'alice@example.com', password_hash)

        self.app = App(DATABASE_URL=self.db_path)
        self.client = TestClient(self.app)

    def tearDown(self):
        os.remove(self.db_path)

    def test_stream_requires_session(self):
        response = self.client.get('/stream', follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['location'], '/login')

    def test_stream_sends_the_user_event_then_stops(self):
        self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'correct horse'})
        session = self.client.cookies['session']

        # Push a test event onto the user's channel.
        self.app.state.get_channel(self.user[0]).put_nowait('hello')

        # Drive the ASGI app directly: disconnect after the first body chunk
        # so the stream stops instead of blocking forever.
        import asyncio

        body = bytearray()
        disconnected = asyncio.Event()

        async def drive():
            scope = {
                'type': 'http',
                'method': 'GET',
                'path': '/stream',
                'raw_path': b'/stream',
                'query_string': b'',
                'headers': [(b'cookie', ('session=%s' % session).encode())],
            }

            async def receive():
                await disconnected.wait()
                return {'type': 'http.disconnect'}

            async def send(message):
                if message['type'] == 'http.response.body':
                    body.extend(message.get('body', b''))
                    if body:
                        disconnected.set()

            await self.app(scope, receive, send)

        asyncio.run(asyncio.wait_for(drive(), timeout=5))

        self.assertEqual(bytes(body), b'data: hello\n\n')


if __name__ == '__main__':
    unittest.main()
