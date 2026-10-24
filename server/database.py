"""Persistent PostgreSQL for serverless; SQLite remains available for local use."""
from contextlib import contextmanager
import os
import sqlite3
import threading
from urllib.parse import parse_qsl, urlsplit
from server.store import Store


class ConfigurationError(RuntimeError):
    pass


class PostgresConnection:
    """Translate the application's fixed, parameterized SQL to PostgreSQL."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        import psycopg
        try:
            return self.connection.execute(sql.replace('?', '%s'), params)
        except psycopg.IntegrityError as exc:
            # Retain the account layer's generic duplicate-account response.
            raise sqlite3.IntegrityError('Constraint violation') from exc

    def executescript(self, sql):
        for statement in sql.split(';'):
            if statement.strip():
                # Millisecond timestamps exceed PostgreSQL's 32-bit INTEGER.
                self.execute(statement.replace('INTEGER', 'BIGINT'))


class PostgresStore(Store):
    def __init__(self, url, initialize=True):
        try:
            import psycopg  # noqa: F401
            import certifi
        except ImportError:
            raise ConfigurationError('Instale as dependências de requirements.txt.') from None
        parsed = urlsplit(url)
        if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname:
            raise ConfigurationError('DATABASE_URL deve ser uma conexão PostgreSQL válida.')
        settings = dict(parse_qsl(parsed.query))
        # Provider URLs using require/verify-ca are upgraded to verify-full below.
        # Explicit TLS-disabling modes remain forbidden.
        if settings.get('sslmode') not in (None, 'require', 'verify-ca', 'verify-full'):
            raise ConfigurationError('Use sslmode=verify-full na conexão PostgreSQL.')
        self.url = url
        self.sslrootcert = settings.get('sslrootcert', certifi.where())
        self.schema_managed = True
        if initialize:
            with self.connect() as db:
                db.execute('CREATE SCHEMA IF NOT EXISTS nexo')
            self.initialize()
            from server.workspace import Workspace
            Workspace(self, initialize=True)

    @contextmanager
    def connect(self):
        import psycopg
        from psycopg.rows import dict_row
        try:
            with psycopg.connect(self.url, row_factory=dict_row, connect_timeout=10,
                                 sslmode='verify-full', sslrootcert=self.sslrootcert,
                                 prepare_threshold=None) as db:
                db.execute("SET LOCAL statement_timeout = '15s'")
                db.execute('SET LOCAL search_path TO nexo')
                yield PostgresConnection(db)
        except sqlite3.IntegrityError:
            raise
        except psycopg.Error as exc:
            # Never send a DSN or provider diagnostic containing credentials to the browser.
            error = ConfigurationError('Banco de dados indisponível. Verifique a conexão e tente novamente.')
            reasons = ('certificate verify failed', 'password authentication failed',
                       'permission denied', 'does not exist', 'connection refused',
                       'timeout expired', 'could not translate host name',
                       'no schema has been selected', 'channel binding')
            error.diagnostic = {
                'type': type(exc).__name__, 'sqlstate': exc.sqlstate,
                'reason': next((reason for reason in reasons if reason in str(exc)), 'unclassified'),
            }
            raise error from None

    def begin_write(self, db, item_id):
        # Coordinate the same item across separate serverless instances.
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?, 0))', (item_id,))


def store_from_environment():
    url = os.environ.get('DATABASE_URL')
    if url:
        return PostgresStore(url, initialize=False)
    if os.environ.get('VERCEL'):
        raise ConfigurationError('Configure DATABASE_URL no projeto Vercel para ativar o backend.')
    return Store(os.environ.get('DATABASE_PATH', '.data/platform.sqlite'))


class LazyStore:
    """Do not connect or create schema during a Vercel build or static request."""
    def __init__(self):
        self._store = None
        self._lock = threading.Lock()

    def __getattr__(self, name):
        with self._lock:
            if self._store is None:
                self._store = store_from_environment()
        return getattr(self._store, name)
