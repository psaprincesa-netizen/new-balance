"""Development HTTP server for the unified productivity workspace."""
import json
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from functools import cache
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from server.store import Store, InvalidInput
from server.workspace import Workspace, Conflict
from server.database import ConfigurationError, store_from_environment

WEB = Path(__file__).resolve().parent.parent / 'web'


def handler_for(store):
    @cache
    def workspace():
        return Workspace(store)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def respond(self, status, data, cookie=None, mime=None, filename=None):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime or 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            if filename:
                self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The client navigated away; the committed operation remains valid.

        def token(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie', ''))
                return cookie['session'].value if 'session' in cookie else ''
            except Exception:
                return ''

        def page_response(self, rows, offset, limit):
            # Keep responses below the provider's 4.5 MB serverless limit.
            count=len(rows)
            while len(rows)>1 and len(json.dumps(rows).encode())>3_000_000:
                rows=rows[:-1]
            return self.respond(200, {'items':rows, 'next_offset':offset+len(rows) if len(rows)<count or count==limit else None})

        def dispatch(self, method):
            path = urlsplit(self.path).path
            query = parse_qs(urlsplit(self.path).query)
            if path in ('/api/index', '/api/index.py') and query.get('route'):
                path = '/api/' + query['route'][0].strip('/')
            offset_text = query.get('offset', ['0'])[0]
            if not offset_text.isdecimal() or len(offset_text) > 7:
                raise InvalidInput('Paginação inválida.')
            offset = int(offset_text)
            if method == 'GET':
                assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                          '/chart.js': ('chart.js', 'text/javascript; charset=utf-8'),
                          '/spreadsheet.js': ('spreadsheet.js', 'text/javascript; charset=utf-8'),
                          '/spreadsheet.css': ('spreadsheet.css', 'text/css; charset=utf-8'),
                          '/formula.js': ('formula.js', 'text/javascript; charset=utf-8'),
                          '/formula-engine.js': ('formula-engine.js', 'text/javascript; charset=utf-8'),
                          '/style.css': ('style.css', 'text/css; charset=utf-8')}
                if path in ('/downloads/nexo.zip', '/downloads/drap-office.zip'):
                    package = WEB.parent / 'public' / 'downloads' / path.rsplit('/', 1)[1]
                    if package.is_file():
                        return self.respond(200, package.read_bytes(), mime='application/zip')
                    return self.respond(404, {'error': 'Pacote não disponível.'})
                if path in assets:
                    file, mime = assets[path]
                    return self.respond(200, (WEB / file).read_bytes(), mime=mime)
                if path == '/api/health':
                    workspace()
                    with store.connect() as db:
                        db.execute('SELECT id FROM users LIMIT 1').fetchone()
                        db.execute('SELECT id FROM items LIMIT 1').fetchone()
                    return self.respond(200, {'status': 'ok'})
                if path.startswith('/api/forms/'):
                    return self.respond(200, workspace().public_form(path.removeprefix('/api/forms/')))
                user = store.session_user(self.token())
                if path == '/api/me':
                    return self.respond(200 if user else 401, user or {'error': 'Entre na sua conta.'})
                if not path.startswith('/api/items'):
                    return self.respond(404, {'error': 'Rota não encontrada.'})
                if not user:
                    return self.respond(401, {'error': 'Entre na sua conta.'})
                if path == '/api/items':
                    rows = workspace().list(user['id'], limit=4, offset=offset)
                    return self.page_response(rows, offset, 4)
                parts = path.strip('/').split('/')
                if len(parts) == 4 and parts[3] == 'shares':
                    return self.respond(200, {'items': workspace().shares(user['id'], parts[2])})
                if len(parts) == 4 and parts[3] == 'publication':
                    return self.respond(200, workspace().publication(user['id'], parts[2]))
                if len(parts) == 4 and parts[3] == 'comments':
                    rows = workspace().comments(user['id'], parts[2], offset)
                    return self.respond(200, {'items': rows, 'next_offset': offset + 50 if len(rows) == 50 else None})
                if len(parts) == 4 and parts[3] == 'export':
                    from server.office import export_file
                    extension = query.get('format', [''])[0]
                    item = workspace().get(user['id'], parts[2])
                    body, mime = export_file(item, extension)
                    return self.respond(200, body, mime=mime, filename='drap-office.' + extension)
                if len(parts) == 4 and parts[3] == 'history':
                    rows = workspace().history(user['id'], parts[2], limit=4, offset=offset)
                    return self.page_response(rows, offset, 4)
                if len(parts) == 3:
                    return self.respond(200, workspace().get(user['id'], parts[2]))
                return self.respond(404, {'error': 'Rota não encontrada.'})

            origin = self.headers.get('Origin')
            if (origin and urlsplit(origin).netloc != self.headers.get('Host')) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.respond(403, {'error': 'Origem não permitida.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond(415, {'error': 'Envie application/json.'})
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 3_500_000:
                return self.respond(413, {'error': 'Tamanho de pedido inválido.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise InvalidInput('Envie um objeto JSON.')
            if path.startswith('/api/forms/'):
                ip = self.headers.get('x-forwarded-for', self.client_address[0]).split(',')[0].strip() if os.environ.get('VERCEL') else self.client_address[0]
                if not store.auth_allowed('public-form:' + ip, limit=20):
                    return self.respond(429, {'error': 'Muitas respostas. Aguarde um minuto.'})
                return self.respond(201, workspace().submit_form(path.removeprefix('/api/forms/'), data.get('answers'), data.get('schema_id')))
            if path in ('/api/register', '/api/login'):
                if any(not isinstance(v, str) for v in data.values()):
                    raise InvalidInput('Campos devem ser textos.')
                if len(data.get('password', '')) > 128:
                    raise InvalidInput('Senha muito longa.')
                email_key = 'email:' + data.get('email', '')
                ip = self.client_address[0]
                if os.environ.get('VERCEL'):
                    ip = self.headers.get('x-forwarded-for', ip).split(',')[0].strip()
                if not store.auth_allowed('ip:' + ip, limit=60) or not store.auth_allowed(email_key):
                    return self.respond(429, {'error': 'Muitas tentativas. Aguarde um minuto.'})
                if path == '/api/register':
                    return self.respond(201, store.register(data.get('email', ''), data.get('name', ''), data.get('password', '')))
                token = store.login(data.get('email', ''), data.get('password', ''))
                if not token:
                    return self.respond(401, {'error': 'E-mail ou senha incorretos.'})
                secure = '; Secure' if (os.environ.get('COOKIE_SECURE') == '1' or bool(os.environ.get('VERCEL'))) else ''
                return self.respond(200, store.session_user(token),
                                    'session=' + token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400' + secure)
            if path == '/api/logout':
                store.logout(self.token())
                return self.respond(200, {'ok': True}, 'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
            user = store.session_user(self.token())
            if not user:
                return self.respond(401, {'error': 'Entre na sua conta.'})
            if path == '/api/import':
                from server.office import import_file
                item, warnings = import_file(data.get('name'), data.get('data'))
                return self.respond(201, {'item': workspace().create(user['id'], item), 'warnings': warnings})
            if path == '/api/items':
                return self.respond(201, workspace().create(user['id'], data))
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api', 'items'] and parts[3] == 'publication':
                if type(data.get('enabled')) is not bool:
                    raise InvalidInput('Estado de publicação inválido.')
                return self.respond(200, workspace().publication(user['id'], parts[2], data['enabled']))
            if len(parts) == 4 and parts[:2] == ['api', 'items'] and parts[3] == 'comments':
                if not store.auth_allowed('comment:' + user['id'], limit=30):
                    return self.respond(429, {'error': 'Aguarde um minuto antes de comentar novamente.'})
                return self.respond(201, workspace().comment(user['id'], parts[2], data.get('body')))
            if len(parts) == 4 and parts[:2] == ['api', 'items'] and parts[3] == 'share':
                return self.respond(200, workspace().share(user['id'], parts[2], data.get('email'), data.get('role')))
            if len(parts) == 3 and parts[:2] == ['api', 'items']:
                return self.respond(200, workspace().update(user['id'], parts[2], data))
            self.respond(404, {'error': 'Rota não encontrada.'})

        def dispatch_application_request(self, method):
            try:
                self.dispatch(method)
            except ConfigurationError as exc:
                self.respond(503, {'error': str(exc)})
            except Conflict as exc:
                self.respond(409, {'error': str(exc)})
            except PermissionError as exc:
                self.respond(403, {'error': str(exc)})
            except LookupError as exc:
                self.respond(404, {'error': str(exc)})
            except (ValueError, UnicodeDecodeError, TypeError, RecursionError) as exc:
                self.respond(400, {'error': str(exc) if isinstance(exc, InvalidInput) else 'Dados inválidos.'})

        def do_GET(self):
            self.dispatch_application_request('GET')

        def do_POST(self):
            self.dispatch_application_request('POST')

    return Handler


def main():
    store = store_from_environment()
    server = ThreadingHTTPServer((os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8000'))), handler_for(store))
    print('Plataforma iniciada na porta', server.server_port, flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
