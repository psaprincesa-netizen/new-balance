"""Create a source release using an explicit allowlist; never package runtime data."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
FILES = ['README.md', 'package.json', 'package-lock.json', 'requirements.txt', 'vercel.json', '.python-version',
         '.env.example', '.gitignore', '.vercelignore']
DIRECTORIES = ['api', 'server', 'web', 'scripts', 'tests', 'docs', '.github']
# Vercel omits its upload-control files from the remote build workspace.
IGNORE_DEFAULT = '.env\n.env.*\n!.env.example\n.data/\n.venv/\n.vercel/\nnode_modules/\n__pycache__/\npublic/\ndist/\n'


def package(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    selected = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        for path in sorted((ROOT / directory).rglob('*')):
            blocked = {'.git', '.data', '.venv', 'node_modules', '__pycache__', 'public', 'dist'}
            if (path.is_file() and not path.is_symlink() and not blocked.intersection(path.relative_to(ROOT).parts)
                    and path.suffix in {'.py', '.js', '.mjs', '.css', '.html', '.json', '.md', '.txt', '.yml'}
                    and not path.name.startswith('.env')):
                selected.append(path)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in selected:
            if path.name in ('.gitignore', '.vercelignore') and not path.exists():
                archive.writestr('drap-office/' + path.name, IGNORE_DEFAULT)
                continue
            if path.is_symlink():
                raise ValueError('Links simbólicos não são permitidos no pacote.')
            archive.write(path, 'drap-office/' + path.relative_to(ROOT).as_posix())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest + '  ' + output.name + '\n')
    print(f'Pacote: {output.name} ({output.stat().st_size} bytes); SHA-256: {digest}')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'dist/drap-office.zip'))
    args = parser.parse_args()
    package(args.output)
