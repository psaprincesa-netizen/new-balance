import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from server.store import Store, InvalidInput, MfaRequired, totp
from tests.test_api import ApiTest

PASSWORD = 'uma-senha-segura-123'


class MfaStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'db.sqlite')
        self.user = self.store.register('ana@example.org', 'Ana', PASSWORD)

    def code(self, secret, offset=0):
        return totp(secret, int(time.time()) // 30 + offset)

    def enable(self):
        setup = self.store.mfa_setup(self.user['id'], PASSWORD, 'ana@example.org')
        self.assertIn('secret=' + setup['secret'], setup['uri'])
        codes = self.store.mfa_enable(self.user['id'], self.code(setup['secret']))['backup_codes']
        return setup['secret'], codes

    def test_rfc6238_reference_value(self):
        # RFC 6238 appendix B, SHA-1 secret "12345678901234567890" at T=59s -> 94287082 (8 digits).
        import base64
        secret = base64.b32encode(b'12345678901234567890').decode()
        self.assertEqual(totp(secret, 59 // 30), '287082')

    def test_setup_requires_password_and_a_valid_code(self):
        with self.assertRaises(PermissionError):
            self.store.mfa_setup(self.user['id'], 'errada-errada-1', 'ana@example.org')
        setup = self.store.mfa_setup(self.user['id'], PASSWORD, 'ana@example.org')
        with self.assertRaises(InvalidInput):
            self.store.mfa_enable(self.user['id'], '000000' if self.code(setup['secret']) != '000000' else '111111')
        self.assertIsNotNone(self.store.login('ana@example.org', PASSWORD))

    def test_login_requires_code_and_rejects_replay(self):
        secret, _ = self.enable()
        with self.assertRaises(MfaRequired):
            self.store.login('ana@example.org', PASSWORD)
        self.assertIsNone(self.store.login('ana@example.org', 'senha-errada-000', '123456'))
        # The code used to enable is already consumed; the next step works once.
        future = self.code(secret, 1)
        token = self.store.login('ana@example.org', PASSWORD, future)
        self.assertTrue(self.store.session_user(token)['mfa_enabled'])
        with self.assertRaises(MfaRequired):
            self.store.login('ana@example.org', PASSWORD, future)

    def test_backup_codes_work_once(self):
        _, codes = self.enable()
        self.assertEqual(len(codes), 8)
        self.assertTrue(self.store.login('ana@example.org', PASSWORD, codes[0].upper()))
        with self.assertRaises(MfaRequired):
            self.store.login('ana@example.org', PASSWORD, codes[0])
        kinds = [e['kind'] for e in self.store.events(self.user['id'])]
        self.assertIn('backup_code_used', kinds)
        self.assertIn('mfa_enabled', kinds)

    def test_disable_requires_password_and_code(self):
        secret, codes = self.enable()
        with self.assertRaises(PermissionError):
            self.store.mfa_disable(self.user['id'], PASSWORD, '000000' if self.code(secret, 1) != '000000' else '111111')
        self.store.mfa_disable(self.user['id'], PASSWORD, codes[1])
        self.assertTrue(self.store.login('ana@example.org', PASSWORD))

    def test_password_reset_does_not_bypass_mfa(self):
        self.store.set_recovery(self.user['id'], PASSWORD, 'pet', 'Rex')
        self.enable()
        self.store.recover('ana@example.org', 'rex', 'nova-senha-segura-456')
        with self.assertRaises(MfaRequired):
            self.store.login('ana@example.org', 'nova-senha-segura-456')

    def test_events_are_capped(self):
        for _ in range(205):
            self.store.log_event('login', user_id=self.user['id'])
        self.assertEqual(len(self.store.events(self.user['id'], limit=500)), 200)


class MfaApiTest(ApiTest):
    def test_mfa_and_activity_over_http(self):
        account = {'email': 'ana@example.org', 'name': 'Ana', 'password': PASSWORD, 'question': 'pet', 'answer': 'Rex'}
        self.assertEqual(self.request('POST', '/api/register', account)[0], 201)
        self.assertEqual(self.request('POST', '/api/login', {**account, 'password': 'errada-errada-1'})[0], 401)
        status, user, cookie = self.request('POST', '/api/login', account)
        headers = {'Cookie': cookie.split(';')[0], 'Content-Type': 'application/json'}
        status, setup, _ = self.request('POST', '/api/account/mfa/setup', {'password': PASSWORD}, headers)
        self.assertEqual(status, 200)
        code = totp(setup['secret'], int(time.time()) // 30)
        status, enabled, _ = self.request('POST', '/api/account/mfa/enable', {'code': code}, headers)
        self.assertEqual((status, len(enabled['backup_codes'])), (200, 8))
        status, body, _ = self.request('POST', '/api/login', account)
        self.assertEqual((status, body.get('mfa_required')), (401, True))
        status, body, _ = self.request('POST', '/api/login', {**account, 'code': enabled['backup_codes'][0]})
        self.assertEqual((status, body['mfa_enabled']), (200, True))
        status, events, _ = self.request('GET', '/api/account/events', headers=headers)
        kinds = [e['kind'] for e in events['items']]
        for kind in ('register', 'login_failed', 'login', 'mfa_enabled', 'backup_code_used'):
            self.assertIn(kind, kinds)
        self.assertTrue(all(e['label'] for e in events['items']))
        self.assertEqual(self.request('GET', '/api/account/events')[0], 401)


if __name__ == '__main__':
    unittest.main()


class ConcurrentMfaTest(unittest.TestCase):
    def test_backup_code_is_consumed_once_under_concurrent_login(self):
        from concurrent.futures import ThreadPoolExecutor
        import tempfile,time
        from pathlib import Path
        from server.store import Store,totp,MfaRequired
        with tempfile.TemporaryDirectory() as temp:
            store=Store(Path(temp)/'test.sqlite');user=store.register('concurrent@example.org','Teste','password-long-test')
            setup=store.mfa_setup(user['id'],'password-long-test',user['email']);codes=store.mfa_enable(user['id'],totp(setup['secret'],int(time.time())//30))['backup_codes']
            def login(_):
                try:return bool(store.login(user['email'],'password-long-test',codes[0]))
                except MfaRequired:return False
            with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(login,range(2)))
            self.assertEqual(sorted(result),[False,True])
