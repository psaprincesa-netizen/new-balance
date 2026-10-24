"""Unified, versioned workspace shared by every editor."""
import json
import secrets
import sqlite3
import time
from server.store import InvalidInput
from server.schema import validate_content

KINDS = {'document', 'sheet', 'slides', 'note', 'board', 'calendar', 'form', 'table', 'diagram', 'portal'}


class Conflict(Exception):
    pass


class Workspace:
    def __init__(self, store, initialize=None):
        self.store = store
        if initialize is None:
            initialize = not getattr(store, "schema_managed", False)
        if not initialize:
            return
        with store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
                    kind TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL,
                    version INTEGER NOT NULL, updated INTEGER NOT NULL, deleted INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS versions (
                    item_id TEXT NOT NULL REFERENCES items(id), version INTEGER NOT NULL,
                    title TEXT NOT NULL, content TEXT NOT NULL, updated INTEGER NOT NULL,
                    PRIMARY KEY(item_id, version));
                CREATE TABLE IF NOT EXISTS shares (
                    item_id TEXT NOT NULL REFERENCES items(id), user_id TEXT NOT NULL REFERENCES users(id),
                    role TEXT NOT NULL, PRIMARY KEY(item_id, user_id));
                CREATE INDEX IF NOT EXISTS items_owner ON items(owner);
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
                    author TEXT NOT NULL REFERENCES users(id), body TEXT NOT NULL, created INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS comments_item ON comments(item_id, created);
                CREATE TABLE IF NOT EXISTS form_publications (
                    token TEXT PRIMARY KEY, item_id TEXT UNIQUE NOT NULL REFERENCES items(id));
            ''')

    @staticmethod
    def public(row):
        result = dict(row)
        result['content'] = json.loads(result['content'])
        result['deleted'] = bool(result['deleted'])
        return result

    def accessible(self, db, user, item_id):
        return db.execute('''SELECT i.*, CASE WHEN i.owner = ? THEN 'owner' ELSE s.role END AS role
            FROM items i LEFT JOIN shares s ON s.item_id = i.id AND s.user_id = ?
            WHERE i.id = ? AND (i.owner = ? OR s.user_id = ?)''',
            (user, user, item_id, user, user)).fetchone()

    def get(self, user, item_id):
        with self.store.connect() as db:
            row = self.accessible(db, user, item_id)
            if not row:
                raise LookupError('Arquivo não encontrado.')
            return self.public(row)

    def list(self, user, limit=None, offset=0):
        with self.store.connect() as db:
            rows = db.execute('''SELECT i.*, CASE WHEN i.owner = ? THEN 'owner' ELSE s.role END AS role
                FROM items i LEFT JOIN shares s ON s.item_id = i.id AND s.user_id = ?
                WHERE i.owner = ? OR s.user_id = ? ORDER BY updated DESC, title, i.id''' +
                (' LIMIT ? OFFSET ?' if limit is not None else ''),
                (user, user, user, user) + ((limit, offset) if limit is not None else ())).fetchall()
            return [self.public(row) for row in rows]

    @staticmethod
    def validate(data):
        if not isinstance(data.get('title'), str) or not 1 <= len(data['title'].strip()) <= 200:
            raise InvalidInput('O título deve ter de 1 a 200 caracteres.')
        content = data.get('content')
        if not isinstance(content, dict) or len(json.dumps(content, allow_nan=False)) > 2_000_000:
            raise InvalidInput('Conteúdo inválido ou maior que 2 MB.')
        return data['title'].strip(), json.dumps(content, ensure_ascii=False)

    def create(self, user, data):
        title, content = self.validate(data)
        kind = data.get('kind')
        if not isinstance(kind, str) or kind not in KINDS:
            raise InvalidInput('Tipo de arquivo inválido.')
        validate_content(kind, data['content'])
        item_id = secrets.token_hex(16)
        now = time.time_ns() // 1000000
        with self.store.connect() as db:
            db.execute('INSERT INTO items VALUES (?, ?, ?, ?, ?, 1, ?, 0)',
                       (item_id, user, kind, title, content, now))
            db.execute('INSERT INTO versions VALUES (?, 1, ?, ?, ?)', (item_id, title, content, now))
        return self.get(user, item_id)

    def update(self, user, item_id, data):
        title, content = self.validate(data)
        if type(data.get('version')) is not int or type(data.get('deleted', False)) is not bool:
            raise InvalidInput('Versão ou estado inválido.')
        with self.store.connect() as db:
            self.store.begin_write(db, item_id)
            row = self.accessible(db, user, item_id)
            if not row:
                raise LookupError('Arquivo não encontrado.')
            validate_content(row['kind'], data['content'])
            if row['role'] not in ('owner', 'edit'):
                raise PermissionError('Você possui acesso somente de leitura.')
            if data['version'] != row['version']:
                raise Conflict('Este arquivo mudou em outra sessão. Exporte seu rascunho antes de reabrir a versão atual.')
            version, now = row['version'] + 1, time.time_ns() // 1000000
            db.execute('UPDATE items SET title=?, content=?, version=?, updated=?, deleted=? WHERE id=?',
                       (title, content, version, now, int(data.get('deleted', False)), item_id))
            db.execute('INSERT INTO versions VALUES (?, ?, ?, ?, ?)', (item_id, version, title, content, now))
        return self.get(user, item_id)

    def history(self, user, item_id, limit=None, offset=0):
        self.get(user, item_id)
        with self.store.connect() as db:
            return [dict(row) | {'content': json.loads(row['content'])} for row in db.execute(
                'SELECT version, title, content, updated FROM versions WHERE item_id=? ORDER BY version DESC' +
                (' LIMIT ? OFFSET ?' if limit is not None else ''), (item_id,) + ((limit, offset) if limit is not None else ()))]

    def share(self, user, item_id, email, role):
        with self.store.connect() as db:
            row = self.accessible(db, user, item_id)
            if not row:
                raise LookupError('Arquivo não encontrado.')
            if row['role'] != 'owner':
                raise PermissionError('Somente o proprietário pode compartilhar.')
            if role not in ('read', 'edit', 'remove') or not isinstance(email, str):
                raise InvalidInput('Permissão inválida.')
            target = db.execute('SELECT id FROM users WHERE email=?', (email.strip().lower(),)).fetchone()
            if not target:
                raise InvalidInput('A pessoa precisa criar uma conta nesta plataforma primeiro.')
            if target['id'] == user:
                raise InvalidInput('O proprietário já possui acesso.')
            if role == 'remove':
                db.execute('DELETE FROM shares WHERE item_id=? AND user_id=?', (item_id, target['id']))
            else:
                db.execute('INSERT INTO shares VALUES (?, ?, ?) ON CONFLICT(item_id,user_id) DO UPDATE SET role=excluded.role',
                           (item_id, target['id'], role))
        return {'ok': True}

    def shares(self, user, item_id):
        with self.store.connect() as db:
            row = self.accessible(db, user, item_id)
            if not row:
                raise LookupError('Arquivo não encontrado.')
            if row['role'] != 'owner':
                raise PermissionError('Somente o proprietário pode listar os acessos.')
            return [dict(r) for r in db.execute('''SELECT u.name, u.email, s.role FROM shares s
                JOIN users u ON u.id=s.user_id WHERE s.item_id=? ORDER BY u.name''', (item_id,))]

    def comments(self, user, item_id, offset=0):
        with self.store.connect() as db:
            if not self.accessible(db, user, item_id):
                raise LookupError('Arquivo não encontrado.')
            return [dict(r) for r in db.execute('''SELECT c.id, c.body, c.created, u.name AS author
                FROM comments c JOIN users u ON c.author=u.id WHERE c.item_id=?
                ORDER BY c.created, c.id LIMIT 50 OFFSET ?''', (item_id, offset))]

    def comment(self, user, item_id, body):
        if not isinstance(body, str) or not 1 <= len(body.strip()) <= 4000:
            raise InvalidInput('O comentário deve ter de 1 a 4000 caracteres.')
        with self.store.connect() as db:
            self.store.begin_write(db, item_id)
            row = self.accessible(db, user, item_id)
            if not row:
                raise LookupError('Arquivo não encontrado.')
            if row['role'] not in ('owner', 'edit'):
                raise PermissionError('É necessário acesso de edição para comentar.')
            if db.execute('SELECT COUNT(*) AS n FROM comments WHERE item_id=?', (item_id,)).fetchone()['n'] >= 1000:
                raise InvalidInput('Limite de 1000 comentários por arquivo.')
            db.execute('INSERT INTO comments VALUES (?, ?, ?, ?, ?)',
                       (secrets.token_hex(16), item_id, user, body.strip(), time.time_ns() // 1000000))
        return {'ok': True}

    def publication(self, user, item_id, enabled=None):
        with self.store.connect() as db:
            self.store.begin_write(db, item_id)
            row = self.accessible(db, user, item_id)
            if not row:
                raise LookupError('Arquivo não encontrado.')
            if row['role'] != 'owner' or row['kind'] != 'form':
                raise PermissionError('Somente o proprietário de um formulário pode publicar a coleta.')
            if enabled is not None:
                if type(enabled) is not bool:
                    raise InvalidInput('Estado de publicação inválido.')
                if enabled:
                    content = json.loads(row['content'])
                    if row['deleted'] or not content['questions']:
                        raise InvalidInput('Adicione perguntas e restaure o formulário antes de publicar.')
                    db.execute('INSERT INTO form_publications VALUES (?, ?) ON CONFLICT(item_id) DO NOTHING', (secrets.token_urlsafe(32), item_id))
                else:
                    db.execute('DELETE FROM form_publications WHERE item_id=?', (item_id,))
            result = db.execute('SELECT token FROM form_publications WHERE item_id=?', (item_id,)).fetchone()
            return {'token': result['token'] if result else None}

    def public_form(self, token):
        from server.forms import form_schema
        if not isinstance(token, str) or len(token) != 43:
            raise LookupError('Formulário indisponível.')
        with self.store.connect() as db:
            row = db.execute('''SELECT i.title, i.content FROM items i JOIN form_publications p ON p.item_id=i.id
                WHERE p.token=? AND i.kind='form' AND i.deleted=0''', (token,)).fetchone()
            if not row:
                raise LookupError('Formulário indisponível.')
            return {'title': row['title'], **form_schema(json.loads(row['content']))}

    def submit_form(self, token, answers, schema_id):
        from server.forms import validate_answers
        if not isinstance(token, str) or len(token) != 43:
            raise LookupError('Formulário indisponível.')
        with self.store.connect() as db:
            pub = db.execute('SELECT item_id FROM form_publications WHERE token=?', (token,)).fetchone()
            if not pub:
                raise LookupError('Formulário indisponível.')
            item_id = pub['item_id']
            self.store.begin_write(db, item_id)
            # Recheck publication after obtaining the same lock used by revocation.
            row = db.execute('''SELECT i.* FROM items i JOIN form_publications p ON p.item_id=i.id
                WHERE p.token=? AND i.kind='form' AND i.deleted=0''', (token,)).fetchone()
            if not row:
                raise LookupError('Formulário indisponível.')
            content = json.loads(row['content'])
            if len(content['responses']) >= 1000:
                raise InvalidInput('Este formulário atingiu o limite de respostas.')
            answers = validate_answers(content, answers, schema_id)
            now = time.time_ns() // 1000000
            content['responses'].append({'at': now, 'questions': content['questions'][:], 'answers': answers})
            _, encoded = self.validate({'title': row['title'], 'content': content})
            version = row['version'] + 1
            db.execute('UPDATE items SET content=?, version=?, updated=? WHERE id=?', (encoded, version, now, item_id))
            db.execute('INSERT INTO versions VALUES (?, ?, ?, ?, ?)', (item_id, version, row['title'], encoded, now))
        return {'ok': True}
