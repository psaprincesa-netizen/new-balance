"""Transactional account and session persistence; no external services required."""
from contextlib import contextmanager
import hashlib
import hmac
import secrets
import sqlite3
import time
import unicodedata
from pathlib import Path


class InvalidInput(ValueError):
    pass


# Fixed list so answers are never free-form questions chosen by the client.
SECURITY_QUESTIONS = {
    'pet': 'Qual era o nome do seu primeiro animal de estimação?',
    'school': 'Qual é o nome da primeira escola em que você estudou?',
    'friend': 'Qual é o nome do seu melhor amigo de infância?',
    'street': 'Em que rua você morava na infância?',
    'grandmother': 'Qual é o primeiro nome da sua avó materna?',
    'first_job': 'Qual foi o seu primeiro emprego?',
    'city': 'Em que cidade seus pais se conheceram?',
}
RECOVERY_MAX_FAILURES = 5
RECOVERY_LOCK_SECONDS = 15 * 60
RECOVERY_FAILED = 'Não foi possível recuperar a conta com esses dados.'


def normalize_answer(answer):
    """Compare answers ignoring case, accents and repeated spaces."""
    if not isinstance(answer, str):
        raise InvalidInput('Informe a resposta secreta.')
    text = unicodedata.normalize('NFKD', answer)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return ' '.join(text.casefold().split())


def valid_recovery(question, answer):
    if question not in SECURITY_QUESTIONS:
        raise InvalidInput('Escolha uma pergunta secreta da lista.')
    normalized = normalize_answer(answer)
    if len(normalized) < 3 or len(answer) > 100:
        raise InvalidInput('A resposta secreta deve ter entre 3 e 100 caracteres.')
    return normalized


def valid_password(password):
    if not isinstance(password, str) or len(password) < 12 or len(password) > 128:
        raise InvalidInput('A senha deve ter entre 12 e 128 caracteres.')


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
                CREATE TABLE IF NOT EXISTS account_recovery (
                    user_id TEXT PRIMARY KEY REFERENCES users(id), question TEXT NOT NULL,
                    salt TEXT NOT NULL, answer TEXT NOT NULL,
                    failures INTEGER NOT NULL DEFAULT 0, locked_until INTEGER NOT NULL DEFAULT 0);
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

    def register(self, email, name, password, question=None, answer=None, require_recovery=False):
        email = email.strip().lower()
        name = name.strip()
        if len(email) > 254 or '@' not in email or not name or len(name) > 100:
            raise InvalidInput('Informe nome e e-mail válidos.')
        valid_password(password)
        normalized = None
        if require_recovery or question or answer:
            normalized = valid_recovery(question, answer)
        user_id, salt = secrets.token_hex(16), secrets.token_hex(16)
        hashed = self.password_hash(password, salt)
        try:
            with self.connect() as db:
                db.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?)',
                           (user_id, email, name, salt, hashed))
                if normalized is not None:
                    self._store_recovery(db, user_id, question, normalized)
        except sqlite3.IntegrityError:
            raise InvalidInput('Não foi possível cadastrar essa conta.') from None
        return {'id': user_id, 'email': email, 'name': name,
                'recovery_question': question if normalized is not None else None}

    def _store_recovery(self, db, user_id, question, normalized):
        salt = secrets.token_hex(16)
        db.execute('DELETE FROM account_recovery WHERE user_id = ?', (user_id,))
        db.execute('INSERT INTO account_recovery (user_id, question, salt, answer, failures, locked_until) '
                   'VALUES (?, ?, ?, ?, 0, 0)',
                   (user_id, question, salt, self.password_hash(normalized, salt)))

    def set_recovery(self, user_id, password, question, answer):
        """Create or replace the secret question; the current password is required."""
        normalized = valid_recovery(question, answer)
        with self.connect() as db:
            user = db.execute('SELECT salt, password FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user or not isinstance(password, str) or not hmac.compare_digest(
                    self.password_hash(password, user['salt']), user['password']):
                raise PermissionError('Senha atual incorreta.')
            self._store_recovery(db, user_id, question, normalized)
        return {'ok': True}

    def recovery_question(self, email):
        with self.connect() as db:
            row = db.execute('''SELECT r.question FROM account_recovery r
                JOIN users u ON u.id = r.user_id WHERE u.email = ?''',
                (str(email).strip().lower(),)).fetchone()
        if not row:
            raise LookupError(RECOVERY_FAILED)
        return {'question': row['question'], 'text': SECURITY_QUESTIONS[row['question']]}

    def recover(self, email, answer, password):
        """Reset the password after a correct answer and end every existing session."""
        valid_password(password)
        normalized = normalize_answer(answer)
        now = int(time.time())
        with self.connect() as db:
            row = db.execute('''SELECT u.id, r.salt, r.answer, r.failures, r.locked_until
                FROM account_recovery r JOIN users u ON u.id = r.user_id WHERE u.email = ?''',
                (str(email).strip().lower(),)).fetchone()
            if not row:
                # Same work and message as a wrong answer.
                self.password_hash(normalized, '00' * 16)
                raise PermissionError(RECOVERY_FAILED)
            if row['locked_until'] > now:
                minutes = max(1, (row['locked_until'] - now + 59) // 60)
                raise PermissionError(f'Muitas respostas incorretas. Tente novamente em {minutes} min.')
            if not hmac.compare_digest(self.password_hash(normalized, row['salt']), row['answer']):
                failures = row['failures'] + 1
                locked = now + RECOVERY_LOCK_SECONDS if failures >= RECOVERY_MAX_FAILURES else 0
                db.execute('UPDATE account_recovery SET failures = ?, locked_until = ? WHERE user_id = ?',
                           (0 if locked else failures, locked, row['id']))
                raise_after = PermissionError(RECOVERY_FAILED)
            else:
                raise_after = None
                salt = secrets.token_hex(16)
                db.execute('UPDATE users SET salt = ?, password = ? WHERE id = ?',
                           (salt, self.password_hash(password, salt), row['id']))
                db.execute('UPDATE account_recovery SET failures = 0, locked_until = 0 WHERE user_id = ?', (row['id'],))
                db.execute('DELETE FROM sessions WHERE user_id = ?', (row['id'],))
        if raise_after:
            # Raised outside the transaction so the failure counter is committed.
            raise raise_after
        return {'ok': True}

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
            row = db.execute('''SELECT u.id, u.email, u.name, r.question FROM users u
                JOIN sessions s ON s.user_id = u.id
                LEFT JOIN account_recovery r ON r.user_id = u.id
                WHERE s.digest = ? AND s.expires > ?''',
                (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            if not row:
                return None
            user = dict(row)
            user['recovery_question'] = user.pop('question')
            return user

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
