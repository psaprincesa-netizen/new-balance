import sqlite3
import tempfile
import unittest
from pathlib import Path
from server.store import Store, InvalidInput


class AccountsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'platform.sqlite'
        self.store = Store(self.path)
        self.user = self.store.register('ana@example.org', 'Ana', 'uma-senha-segura-123')

    def test_persistence_and_password_storage(self):
        store = Store(self.path)
        token = store.login('ANA@example.org', 'uma-senha-segura-123')
        self.assertEqual(store.session_user(token), self.user)
        with store.connect() as db:
            row = db.execute('SELECT * FROM users').fetchone()
            self.assertNotEqual(row['password'], 'uma-senha-segura-123')
            self.assertEqual(len(row['salt']), 32)

    def test_wrong_password_and_unknown_user(self):
        self.assertIsNone(self.store.login('ana@example.org', 'incorreta'))
        self.assertIsNone(self.store.login('nobody@example.org', 'incorreta'))

    def test_session_isolation_and_logout(self):
        other = self.store.register('bia@example.org', 'Bia', 'outra-senha-segura-123')
        token = self.store.login('ana@example.org', 'uma-senha-segura-123')
        other_token = self.store.login('bia@example.org', 'outra-senha-segura-123')
        self.assertEqual(self.store.session_user(token)['id'], self.user['id'])
        self.assertEqual(self.store.session_user(other_token)['id'], other['id'])
        self.store.logout(token)
        self.assertIsNone(self.store.session_user(token))
        self.assertIsNotNone(self.store.session_user(other_token))
        self.assertIsNone(self.store.session_user('forged'))

    def test_expired_session(self):
        token = self.store.login('ana@example.org', 'uma-senha-segura-123')
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET expires = 0')
        self.assertIsNone(self.store.session_user(token))

    def test_invalid_and_duplicate_accounts(self):
        for args in [('invalid', 'Ana', 'uma-senha-segura-123'),
                     ('b@example.org', '', 'uma-senha-segura-123'),
                     ('b@example.org', 'Bia', 'short'),
                     ('ANA@example.org', 'Ana', 'uma-senha-segura-123')]:
            with self.assertRaises(InvalidInput):
                self.store.register(*args)


if __name__ == '__main__':
    unittest.main()
