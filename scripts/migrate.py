"""Apply additive PostgreSQL schema changes before routing production traffic."""
import os
from server.database import ConfigurationError, PostgresStore


def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise SystemExit('Configure DATABASE_URL de forma segura antes de migrar.')
    try:
        PostgresStore(url, initialize=True)
    except ConfigurationError as exc:
        if hasattr(exc, 'diagnostic'):
            print('Diagnóstico sem credenciais:', exc.diagnostic)
        raise SystemExit(str(exc)) from None
    print('Schema PostgreSQL inicializado; nenhuma conta ou dado de exemplo foi criado.')


if __name__ == '__main__':
    main()
