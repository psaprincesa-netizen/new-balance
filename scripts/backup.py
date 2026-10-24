"""Online SQLite backup. Restore into a NEW path, then switch DATABASE_PATH."""
import argparse
import sqlite3
from pathlib import Path


def snapshot(source, destination):
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise ValueError('Banco de origem não encontrado.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidentally replacing a user's database.
    destination.touch(mode=0o600, exist_ok=False)
    try:
        with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as origin:
            if origin.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('O banco de origem falhou na verificação de integridade.')
            with sqlite3.connect(destination) as target:
                origin.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('O backup falhou na verificação de integridade.')
    except Exception:
        destination.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    snapshot(args.source, args.destination)
    print('Cópia concluída e integridade verificada.')
