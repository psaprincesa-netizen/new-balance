import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from server.app import handler_for
from server.store import Store


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(Store(Path(self.tmp.name) / 'db.sqlite')))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, path, data=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request(method, path, json.dumps(data) if data is not None else None,
                           headers or {'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, json.loads(response.read()), response.getheader('Set-Cookie')
        connection.close()
        return result

    def test_account_journey(self):
        account = {'email': 'ana@example.org', 'name': 'Ana', 'password': 'uma-senha-segura-123'}
        self.assertEqual(self.request('GET', '/api/health')[0], 200)
        self.assertEqual(self.request('GET', '/api/me')[0], 401)
        self.assertEqual(self.request('POST', '/api/register', account)[0], 201)
        status, user, cookie = self.request('POST', '/api/login', account)
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', cookie)
        headers = {'Cookie': cookie.split(';')[0], 'Content-Type': 'application/json'}
        self.assertEqual(self.request('GET', '/api/me', headers=headers)[1], user)
        self.assertEqual(self.request('POST', '/api/logout', {}, headers)[0], 200)
        self.assertEqual(self.request('GET', '/api/me', headers=headers)[0], 401)

    def test_untrusted_origin_and_invalid_data(self):
        self.assertEqual(self.request('POST', '/api/register', {}, {
            'Content-Type': 'application/json', 'Origin': 'https://attacker.example'})[0], 403)
        self.assertEqual(self.request('POST', '/api/login', {'password': []})[0], 400)
        self.assertEqual(self.request('GET', '/missing')[0], 404)

    def test_workspace_permissions_and_conflict_over_http(self):
        cookies = []
        for name in ('ana', 'bia'):
            data = {'email': name + '@example.org', 'name': name, 'password': 'uma-senha-segura-123'}
            self.assertEqual(self.request('POST', '/api/register', data)[0], 201)
            cookies.append(self.request('POST', '/api/login', data)[2].split(';')[0])
        owner = {'Cookie': cookies[0], 'Content-Type': 'application/json'}
        other = {'Cookie': cookies[1], 'Content-Type': 'application/json'}
        payload = {'kind': 'document', 'title': 'Privado', 'content': {'text': 'confidencial'}}
        self.assertEqual(self.request('POST', '/api/items', payload)[0], 401)
        status, item, _ = self.request('POST', '/api/items', payload, owner)
        self.assertEqual(status, 201)
        path = '/api/items/' + item['id']
        self.assertEqual(self.request('GET', path, headers=other)[0], 404)
        self.assertEqual(self.request('GET', path + '/history', headers=other)[0], 404)
        self.assertEqual(self.request('POST', path, item, other)[0], 404)
        self.assertEqual(self.request('POST', path + '/share', {'email':'bia@example.org','role':'read'}, owner)[0], 200)
        self.assertEqual(self.request('GET', path, headers=other)[0], 200)
        self.assertEqual(self.request('POST', path, item, other)[0], 403)
        self.assertEqual(self.request('POST', path + '/share', {'email':'bia@example.org','role':'edit'}, owner)[0], 200)
        self.assertEqual(self.request('POST', path, item, other)[0], 200)
        self.assertEqual(self.request('POST', path, item, owner)[0], 409)
        self.assertEqual(self.request('POST', path + '/share', {'email':'bia@example.org','role':'remove'}, owner)[0], 200)
        self.assertEqual(self.request('GET', path, headers=other)[0], 404)
        payload['content'] = {'wrong': 'schema'}
        self.assertEqual(self.request('POST', '/api/items', payload, owner)[0], 400)
