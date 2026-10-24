import io
import json
import os
import tempfile
import threading
import unittest
import zipfile
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from server.database import LazyStore, ConfigurationError, store_from_environment
from server.app import handler_for
from server.store import Store
from scripts.package_release import package


class DeploymentTest(unittest.TestCase):
    def test_vercel_never_falls_back_to_ephemeral_sqlite(self):
        with patch.dict(os.environ, {'VERCEL':'1'}, clear=True):
            with self.assertRaises(ConfigurationError):
                store_from_environment()

    def test_unconfigured_function_can_import_and_returns_safe_error(self):
        with patch.dict(os.environ, {'VERCEL':'1'}, clear=True):
            server = ThreadingHTTPServer(('127.0.0.1',0),handler_for(LazyStore()))
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                connection = HTTPConnection('127.0.0.1',server.server_port)
                connection.request('GET','/api/health')
                response = connection.getresponse()
                self.assertEqual(response.status,503)
                self.assertIn('DATABASE_URL', json.loads(response.read())['error'])
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_package_excludes_secrets_database_and_generated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            result = package(Path(temp)/'nexo.zip')
            with zipfile.ZipFile(result) as archive:
                names = archive.namelist()
                self.assertIn('drap-office/vercel.json', names)
                self.assertIn('drap-office/api/index.py', names)
                self.assertIn('drap-office/.env.example', names)
                for name in names:
                    parts = Path(name).parts
                    self.assertFalse(any(p in parts for p in ('.data','.git','node_modules','__pycache__','.vercel','public','dist')))
                    self.assertNotEqual(Path(name).name, '.env')
                    self.assertNotIn(Path(name).suffix, ('.sqlite','.db','.key','.pyc'))
            self.assertTrue(result.with_suffix('.zip.sha256').is_file())

    def test_rate_limit_is_shared_between_instances(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'db.sqlite'
            a,b = Store(path),Store(path)
            for _ in range(20):
                self.assertTrue(a.auth_allowed('email:ana@example.org'))
            self.assertFalse(b.auth_allowed('email:ana@example.org'))

    def test_remote_package_restores_omitted_ignore_files(self):
        from scripts import package_release
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in package_release.FILES:
                if name not in ('.gitignore', '.vercelignore'):
                    (root / name).write_text('fixture')
            with patch.object(package_release, 'ROOT', root):
                result = package(root / 'release.zip')
            with zipfile.ZipFile(result) as archive:
                self.assertIsNone(archive.testzip())
                for name in ('.gitignore', '.vercelignore'):
                    self.assertIn('.env\n', archive.read('drap-office/' + name).decode())

    def test_rewritten_function_route_and_secure_cookie(self):
        with tempfile.TemporaryDirectory() as temp:
            class RuntimeHandler(handler_for(Store(Path(temp)/'db.sqlite'))):
                # Vercel wraps the application class with this zero-argument
                # method. Application dispatch must not call that reserved name.
                def handle_request(self):
                    getattr(self, 'do_' + self.command)()

            server = ThreadingHTTPServer(('127.0.0.1',0),RuntimeHandler)
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                with patch.dict(os.environ, {'VERCEL':'1'}):
                    def post(route, data):
                        connection = HTTPConnection('127.0.0.1',server.server_port)
                        connection.request('POST','/api/index?route='+route,json.dumps(data),{'Content-Type':'application/json'})
                        response = connection.getresponse()
                        result = response.status, json.loads(response.read()), response.getheader('Set-Cookie')
                        connection.close()
                        return result
                    data = {'name':'Ana','email':'ana@example.org','password':'senha-de-teste-longa'}
                    self.assertEqual(post('register',data)[0],201)
                    status, body, cookie = post('login',data)
                    self.assertEqual(status,200)
                    self.assertIn('; Secure',cookie)
                    self.assertIn('; HttpOnly',cookie)
                    self.assertIn('; SameSite=Strict',cookie)
                    connection = HTTPConnection('127.0.0.1',server.server_port)
                    connection.request('GET','/api/index?route=items&offset=0',headers={'Cookie':cookie.split(';')[0]})
                    response = connection.getresponse()
                    self.assertEqual(response.status,200)
                    self.assertEqual(json.loads(response.read()),{'items':[],'next_offset':None})
                    connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_pagination_bounds_items_and_history(self):
        from server.workspace import Workspace
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp)/'db.sqlite')
            user = store.register('ana@example.org','Ana','senha-de-teste-longa')['id']
            ws = Workspace(store)
            first = None
            for i in range(5):
                item = ws.create(user,{'kind':'document','title':str(i),'content':{'text':str(i)}})
                if first is None:
                    first = item
            self.assertEqual(len(ws.list(user,limit=4,offset=0)),4)
            self.assertEqual(len(ws.list(user,limit=4,offset=4)),1)
            for i in range(4):
                first = ws.update(user,first['id'],{'title':first['title'],'content':{'text':str(i)},'version':first['version']})
            self.assertEqual(len(ws.history(user,first['id'],limit=4)),4)
            self.assertEqual(len(ws.history(user,first['id'],limit=4,offset=4)),1)
