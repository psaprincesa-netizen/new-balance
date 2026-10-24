"""Transactional account and session persistence; no external services required."""
from contextlib import contextmanager
import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path


class InvalidInput(ValueError):
    pass


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.initialize()

    def initialize(self):
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL, salt TEXT NOT NULL, password TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_limits (
                    key TEXT PRIMARY KEY, bucket INTEGER NOT NULL, attempts INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    expires INTEGER NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def password_hash(password, salt):
        return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                              n=16384, r=8, p=1).hex()

    def register(self, email, name, password):
        email = email.strip().lower()
        name = name.strip()
        if len(email) > 254 or '@' not in email or not name or len(name) > 100:
            raise InvalidInput('Informe nome e e-mail válidos.')
        if len(password) < 12 or len(password) > 128:
            raise InvalidInput('A senha deve ter entre 12 e 128 caracteres.')
        user_id, salt = secrets.token_hex(16), secrets.token_hex(16)
        hashed = self.password_hash(password, salt)
        try:
            with self.connect() as db:
                db.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?)',
                           (user_id, email, name, salt, hashed))
        except sqlite3.IntegrityError:
            raise InvalidInput('Não foi possível cadastrar essa conta.') from None
        return {'id': user_id, 'email': email, 'name': name}

    def login(self, email, password):
        with self.connect() as db:
            user = db.execute('SELECT * FROM users WHERE email = ?',
                              (email.strip().lower(),)).fetchone()
            salt = user['salt'] if user else '00' * 16
            hashed = self.password_hash(password, salt)
            if not user or not hmac.compare_digest(hashed, user['password']):
                return None
            token = secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires <= ?', (int(time.time()),))
            db.execute('INSERT INTO sessions VALUES (?, ?, ?)',
                       (hashlib.sha256(token.encode()).hexdigest(), user['id'],
                        int(time.time()) + 86400))
            return token

    def session_user(self, token):
        with self.connect() as db:
            row = db.execute('''SELECT u.id, u.email, u.name FROM users u
                JOIN sessions s ON s.user_id = u.id
                WHERE s.digest = ? AND s.expires > ?''',
                (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            return dict(row) if row else None

    def logout(self, token):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE digest = ?',
                       (hashlib.sha256(token.encode()).hexdigest(),))

    def begin_write(self, db, item_id):
        db.execute('BEGIN IMMEDIATE')

    def auth_allowed(self, identifier, limit=20):
        key = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()
        bucket = int(time.time()) // 60
        with self.connect() as db:
            db.execute('DELETE FROM auth_limits WHERE bucket < ?', (bucket - 1,))
            row = db.execute("""INSERT INTO auth_limits VALUES (?, ?, 1)
                ON CONFLICT(key) DO UPDATE SET attempts =
                    CASE WHEN auth_limits.bucket = ? THEN auth_limits.attempts + 1 ELSE 1 END,
                    bucket = excluded.bucket RETURNING attempts""", (key, bucket, bucket)).fetchone()
            return row['attempts'] <= limit
