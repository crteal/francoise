import os
import tempfile
import unittest

from françoise.db import open_db
from françoise.migrate import upgrade_to_head


class TestSessions(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        upgrade_to_head(self.db_path)

        with open_db(self.db_path) as db:
            account = db.create_account('One')[0]
        with open_db(self.db_path, account_id=account) as db:
            self.user_id = db.create_user(
                'Alice', 'alice@example.com', 'hash')[0]

    def tearDown(self):
        os.remove(self.db_path)

    def test_create_read_delete(self):
        with open_db(self.db_path) as db:
            db.create_session('sid', self.user_id, '2099-01-01T00:00:00+00:00')

            session = db.get_session('sid')
            self.assertIsNotNone(session)
            self.assertEqual(session[0], 'sid')
            self.assertEqual(session[1], self.user_id)

            db.delete_session('sid')
            self.assertIsNone(db.get_session('sid'))


if __name__ == '__main__':
    unittest.main()
