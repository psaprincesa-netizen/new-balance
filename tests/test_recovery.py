import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from server.store import Store, InvalidInput, SECURITY_QUESTIONS, RECOVERY_MAX_FAILURES, normalize_answer
from tests.test_api import ApiTest

PASSWORD = 'uma-senha-segura-123'
NEW_PASSWORD = 'outra-senha-segura-456'


class RecoveryStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'db.sqlite')

    def tearDown(self):
        self.tmp.cleanup()

    def register(self, email='ana@example.org', answer='São Paulo'):
        return self.store.register(email, 'Ana', PASSWORD, 'city', answer, require_recovery=True)

    def test_answer_normalization_ignores_case_accents_and_spaces(self):
        self.assertEqual(normalize_answer('  SÃO   paulo '), 'sao paulo')

    def test_registration_requires_valid_question_and_answer(self):
        with self.assertRaises(InvalidInput):
            self.store.register('a@example.org', 'Ana', PASSWORD, require_recovery=True)
        with self.assertRaises(InvalidInput):
            self.store.register('a@example.org', 'Ana', PASSWORD, 'invented', 'resposta', require_recovery=True)
        with self.assertRaises(InvalidInput):
            self.store.register('a@example.org', 'Ana', PASSWORD, 'pet', 'ab', require_recovery=True)

    def test_answer_is_not_stored_in_plain_text(self):
        self.register(answer='Resposta Única')
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM account_recovery').fetchone()
        self.assertNotIn('resposta', ' '.join(str(v) for v in dict(row).values()).lower())

    def test_recover_resets_password_and_ends_sessions(self):
        self.register()
        token = self.store.login('ana@example.org', PASSWORD)
        self.assertEqual(self.store.recovery_question('ANA@example.org')['text'], SECURITY_QUESTIONS['city'])
        self.store.recover('ana@example.org', 'sao PAULO', NEW_PASSWORD)
        self.assertIsNone(self.store.session_user(token))
        self.assertIsNone(self.store.login('ana@example.org', PASSWORD))
        self.assertTrue(self.store.login('ana@example.org', NEW_PASSWORD))

    def test_wrong_answers_lock_recovery(self):
        self.register()
        for _ in range(RECOVERY_MAX_FAILURES):
            with self.assertRaises(PermissionError):
                self.store.recover('ana@example.org', 'errada', NEW_PASSWORD)
        with self.assertRaisesRegex(PermissionError, 'Tente novamente'):
            self.store.recover('ana@example.org', 'São Paulo', NEW_PASSWORD)
        self.assertTrue(self.store.login('ana@example.org', PASSWORD))
        with patch('server.store.time.time', return_value=time.time() + 16 * 60):
            self.store.recover('ana@example.org', 'São Paulo', NEW_PASSWORD)
        self.assertTrue(self.store.login('ana@example.org', NEW_PASSWORD))

    def test_unknown_account_and_account_without_question(self):
        self.store.register('old@example.org', 'Old', PASSWORD)
        for email in ('old@example.org', 'nobody@example.org'):
            with self.assertRaises(LookupError):
                self.store.recovery_question(email)
            with self.assertRaises(PermissionError):
                self.store.recover(email, 'qualquer', NEW_PASSWORD)

    def test_set_recovery_requires_current_password(self):
        user = self.store.register('old@example.org', 'Old', PASSWORD)
        with self.assertRaises(PermissionError):
            self.store.set_recovery(user['id'], 'senha-errada-000', 'pet', 'Rex')
        self.store.set_recovery(user['id'], PASSWORD, 'pet', 'Rex')
        token = self.store.login('old@example.org', PASSWORD)
        self.assertEqual(self.store.session_user(token)['recovery_question'], 'pet')
        self.store.recover('old@example.org', 'rex', NEW_PASSWORD)
        self.assertTrue(self.store.login('old@example.org', NEW_PASSWORD))


class RecoveryApiTest(ApiTest):
    def test_recovery_over_http(self):
        status, questions, _ = self.request('GET', '/api/recovery/questions')
        self.assertEqual(status, 200)
        self.assertIn('pet', [q['id'] for q in questions['items']])
        account = {'email': 'ana@example.org', 'name': 'Ana', 'password': PASSWORD}
        self.assertEqual(self.request('POST', '/api/register', account)[0], 400)
        account.update(question='pet', answer='Rex')
        self.assertEqual(self.request('POST', '/api/register', account)[0], 201)
        status, user, cookie = self.request('POST', '/api/login', account)
        self.assertEqual(user['recovery_question'], 'pet')
        status, data, _ = self.request('POST', '/api/recovery/question', {'email': 'ana@example.org'})
        self.assertEqual((status, data['question']), (200, 'pet'))
        self.assertEqual(self.request('POST', '/api/recovery/question', {'email': 'x@example.org'})[0], 404)
        self.assertEqual(self.request('POST', '/api/recovery/reset', {'email': 'ana@example.org', 'answer': 'Bob', 'password': NEW_PASSWORD})[0], 403)
        self.assertEqual(self.request('POST', '/api/recovery/reset', {'email': 'ana@example.org', 'answer': ' REX ', 'password': 'curta'})[0], 400)
        self.assertEqual(self.request('POST', '/api/recovery/reset', {'email': 'ana@example.org', 'answer': ' REX ', 'password': NEW_PASSWORD})[0], 200)
        headers = {'Cookie': cookie.split(';')[0], 'Content-Type': 'application/json'}
        self.assertEqual(self.request('GET', '/api/me', headers=headers)[0], 401)
        self.assertEqual(self.request('POST', '/api/login', account)[0], 401)
        status, _, cookie = self.request('POST', '/api/login', {**account, 'password': NEW_PASSWORD})
        self.assertEqual(status, 200)
        headers = {'Cookie': cookie.split(';')[0], 'Content-Type': 'application/json'}
        change = {'password': NEW_PASSWORD, 'question': 'school', 'answer': 'Escola Azul'}
        self.assertEqual(self.request('POST', '/api/account/recovery', {**change, 'password': 'errada-errada-1'}, headers)[0], 403)
        status, user, _ = self.request('POST', '/api/account/recovery', change, headers)
        self.assertEqual((status, user['recovery_question']), (200, 'school'))

    def test_recovery_attempts_are_rate_limited(self):
        statuses = [self.request('POST', '/api/recovery/question', {'email': 'ana@example.org'})[0] for _ in range(12)]
        self.assertIn(429, statuses)


if __name__ == '__main__':
    unittest.main()
