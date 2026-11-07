"""Transactional account and session persistence; no external services required."""
from contextlib import contextmanager
import hashlib
import base64
import hmac
import json
import secrets
import struct
import sqlite3
import time
import unicodedata
from pathlib import Path


class InvalidInput(ValueError):
    pass


class MfaRequired(PermissionError):
    """Password accepted; a second factor is still needed."""
    user_id = None


def totp(secret, step):
    key = base64.b32decode(secret + '=' * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    return '%06d' % ((struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000)


EVENT_KINDS = {
    'register': 'Conta criada',
    'login': 'Entrada na conta',
    'login_failed': 'Senha incorreta ao entrar',
    'mfa_failed': 'Código de verificação incorreto',
    'backup_code_used': 'Código de backup usado',
    'mfa_enabled': 'Verificação em duas etapas ativada',
    'mfa_disabled': 'Verificação em duas etapas desativada',
    'password_reset': 'Senha redefinida pela pergunta secreta',
    'recovery_failed': 'Resposta secreta incorreta',
    'recovery_changed': 'Pergunta secreta alterada',
    'share': 'Arquivo compartilhado',
    'logout': 'Saída da conta',
}


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
                CREATE TABLE IF NOT EXISTS account_mfa (
                    user_id TEXT PRIMARY KEY REFERENCES users(id), secret TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0, backup TEXT NOT NULL DEFAULT '[]',
                    last_step INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS account_events (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    at INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
                    ip TEXT NOT NULL DEFAULT '');
                CREATE INDEX IF NOT EXISTS account_events_user ON account_events (user_id, at);
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
                'recovery_question': question if normalized is not None else None, 'mfa_enabled': False}

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
            self.begin_write(db, "account:" + user_id)
            user = db.execute('SELECT salt, password FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user or not isinstance(password, str) or not hmac.compare_digest(
                    self.password_hash(password, user['salt']), user['password']):
                raise PermissionError('Senha atual incorreta.')
            self._store_recovery(db, user_id, question, normalized)
            self._event(db, user_id, 'recovery_changed')
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
            self.begin_write(db, 'account:' + row['id'])
            row = db.execute('SELECT u.id, r.salt, r.answer, r.failures, r.locked_until FROM account_recovery r JOIN users u ON u.id=r.user_id WHERE u.id=?', (row['id'],)).fetchone()
            if row['locked_until'] > now:
                minutes = max(1, (row['locked_until'] - now + 59) // 60)
                raise PermissionError(f'Muitas respostas incorretas. Tente novamente em {minutes} min.')
            if not hmac.compare_digest(self.password_hash(normalized, row['salt']), row['answer']):
                failures = row['failures'] + 1
                locked = now + RECOVERY_LOCK_SECONDS if failures >= RECOVERY_MAX_FAILURES else 0
                db.execute('UPDATE account_recovery SET failures = ?, locked_until = ? WHERE user_id = ?',
                           (0 if locked else failures, locked, row['id']))
                self._event(db, row['id'], 'recovery_failed')
                raise_after = PermissionError(RECOVERY_FAILED)
            else:
                raise_after = None
                salt = secrets.token_hex(16)
                db.execute('UPDATE users SET salt = ?, password = ? WHERE id = ?',
                           (salt, self.password_hash(password, salt), row['id']))
                db.execute('UPDATE account_recovery SET failures = 0, locked_until = 0 WHERE user_id = ?', (row['id'],))
                db.execute('DELETE FROM sessions WHERE user_id = ?', (row['id'],))
                self._event(db, row['id'], 'password_reset')
        if raise_after:
            # Raised outside the transaction so the failure counter is committed.
            raise raise_after
        return {'ok': True}

    def login(self, email, password, code=None):
        """Return a session token, None for wrong credentials, or raise MfaRequired."""
        with self.connect() as db:
            user = db.execute('SELECT * FROM users WHERE email = ?',
                              (email.strip().lower(),)).fetchone()
            if user:
                self.begin_write(db, 'account:' + user['id'])
                user = db.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
            salt = user['salt'] if user else '00' * 16
            hashed = self.password_hash(password, salt)
            if not user or not hmac.compare_digest(hashed, user['password']):
                return None
            mfa = db.execute('SELECT * FROM account_mfa WHERE user_id = ? AND enabled = 1', (user['id'],)).fetchone()
            if mfa:
                if not code:
                    raise MfaRequired('Digite o código do seu app autenticador.')
                used = self._check_mfa(db, mfa, code)
                if not used:
                    failed = MfaRequired('Código de verificação incorreto.')
                    failed.user_id = user['id']
                    raise failed
                if used == 'backup':
                    self._event(db, user['id'], 'backup_code_used')
            token = secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires <= ?', (int(time.time()),))
            db.execute('INSERT INTO sessions VALUES (?, ?, ?)',
                       (hashlib.sha256(token.encode()).hexdigest(), user['id'],
                        int(time.time()) + 86400))
            return token

    def session_user(self, token):
        if not token:
            return None
        with self.connect() as db:
            row = db.execute('''SELECT u.id, u.email, u.name, r.question, m.enabled AS mfa FROM users u
                JOIN sessions s ON s.user_id = u.id
                LEFT JOIN account_recovery r ON r.user_id = u.id
                LEFT JOIN account_mfa m ON m.user_id = u.id
                WHERE s.digest = ? AND s.expires > ?''',
                (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            if not row:
                return None
            user = dict(row)
            user['recovery_question'] = user.pop('question')
            user['mfa_enabled'] = bool(user.pop('mfa'))
            return user

    def logout(self, token):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE digest = ?',
                       (hashlib.sha256(token.encode()).hexdigest(),))

    def begin_write(self, db, item_id):
        # SQLite already serializes every writer in an active transaction.
        if not db.in_transaction:db.execute('BEGIN IMMEDIATE')

    # ----- Two-step verification (TOTP, RFC 6238) -----
    def _check_mfa(self, db, mfa, code):
        code = ''.join(str(code).split()).replace('-', '')
        if len(code) == 6 and code.isdigit():
            now = int(time.time()) // 30
            for step in (now - 1, now, now + 1):
                if step > mfa['last_step'] and hmac.compare_digest(totp(mfa['secret'], step), code):
                    # Remember the step so the same code cannot be replayed.
                    db.execute('UPDATE account_mfa SET last_step = ? WHERE user_id = ?', (step, mfa['user_id']))
                    return 'totp'
            return None
        backup = json.loads(mfa['backup'])
        digest = hashlib.sha256(code.lower().encode()).hexdigest()
        if digest in backup:
            backup.remove(digest)
            db.execute('UPDATE account_mfa SET backup = ? WHERE user_id = ?', (json.dumps(backup), mfa['user_id']))
            return 'backup'
        return None

    def _verify_password(self, db, user_id, password):
        user = db.execute('SELECT salt, password FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user or not isinstance(password, str) or not hmac.compare_digest(
                self.password_hash(password, user['salt']), user['password']):
            raise PermissionError('Senha atual incorreta.')

    def mfa_setup(self, user_id, password, email):
        with self.connect() as db:
            self.begin_write(db, "account:" + user_id)
            self._verify_password(db, user_id, password)
            if db.execute('SELECT 1 FROM account_mfa WHERE user_id = ? AND enabled = 1', (user_id,)).fetchone():
                raise InvalidInput('A verificação em duas etapas já está ativa.')
            secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
            db.execute('DELETE FROM account_mfa WHERE user_id = ?', (user_id,))
            db.execute("INSERT INTO account_mfa (user_id, secret, enabled, backup, last_step) VALUES (?, ?, 0, '[]', 0)",
                       (user_id, secret))
        from urllib.parse import quote
        uri = f'otpauth://totp/{quote("DRAP office:" + email)}?secret={secret}&issuer={quote("DRAP office")}&digits=6&period=30'
        return {'secret': secret, 'uri': uri}

    def mfa_enable(self, user_id, code):
        with self.connect() as db:
            self.begin_write(db, "account:" + user_id)
            mfa = db.execute('SELECT * FROM account_mfa WHERE user_id = ? AND enabled = 0', (user_id,)).fetchone()
            if not mfa:
                raise InvalidInput('Comece a configuração novamente.')
            if self._check_mfa(db, {**dict(mfa), 'backup': '[]'}, code) != 'totp':
                raise InvalidInput('Código incorreto. Confira o horário do celular e tente de novo.')
            codes = ['%s-%s' % (secrets.token_hex(2), secrets.token_hex(2)) for _ in range(8)]
            db.execute('UPDATE account_mfa SET enabled = 1, backup = ? WHERE user_id = ?',
                       (json.dumps([hashlib.sha256(c.replace('-', '').encode()).hexdigest() for c in codes]), user_id))
            self._event(db, user_id, 'mfa_enabled')
        return {'backup_codes': codes}

    def mfa_disable(self, user_id, password, code):
        with self.connect() as db:
            self.begin_write(db, "account:" + user_id)
            self._verify_password(db, user_id, password)
            mfa = db.execute('SELECT * FROM account_mfa WHERE user_id = ? AND enabled = 1', (user_id,)).fetchone()
            if not mfa:
                raise InvalidInput('A verificação em duas etapas não está ativa.')
            if not self._check_mfa(db, mfa, code):
                raise PermissionError('Código de verificação incorreto.')
            db.execute('DELETE FROM account_mfa WHERE user_id = ?', (user_id,))
            self._event(db, user_id, 'mfa_disabled')
        return {'ok': True}

    # ----- Account activity -----
    def _event(self, db, user_id, kind, detail='', ip=''):
        now = time.time_ns() // 1000000
        db.execute('INSERT INTO account_events (id, user_id, at, kind, detail, ip) VALUES (?, ?, ?, ?, ?, ?)',
                   (secrets.token_hex(12), user_id, now, kind, str(detail)[:200], str(ip)[:64]))
        # Keep the most recent 200 events per account.
        db.execute('''DELETE FROM account_events WHERE user_id = ? AND id NOT IN (
            SELECT id FROM account_events WHERE user_id = ? ORDER BY at DESC LIMIT 200)''', (user_id, user_id))

    def log_event(self, kind, user_id=None, email=None, detail='', ip=''):
        with self.connect() as db:
            if user_id is None and email is not None:
                row = db.execute('SELECT id FROM users WHERE email = ?', (str(email).strip().lower(),)).fetchone()
                user_id = row['id'] if row else None
            if user_id:
                self._event(db, user_id, kind, detail, ip)

    def events(self, user_id, limit=100):
        with self.connect() as db:
            rows = db.execute('SELECT at, kind, detail, ip FROM account_events WHERE user_id = ? ORDER BY at DESC LIMIT ?',
                              (user_id, limit)).fetchall()
        return [{**dict(r), 'label': EVENT_KINDS.get(r['kind'], r['kind'])} for r in rows]

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
