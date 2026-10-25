import { cp, mkdir, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
const root = new URL('../', import.meta.url);
execFileSync(process.execPath, ['scripts/build-engine.mjs'], {cwd:root,stdio:'inherit'});
execFileSync(process.execPath, ['scripts/build-document.mjs'], {cwd:root,stdio:'inherit'});
execFileSync(process.execPath, ['scripts/build-spreadsheet.mjs'], {cwd:root,stdio:'inherit'});
if (process.env.VERCEL === '1') {
  if (!process.env.DATABASE_URL || process.env.DATABASE_URL === '[SENSITIVE]') {
    throw new Error('Configure DATABASE_URL no ambiente de implantação antes de publicar.');
  }
  // Run additive schema setup where Vercel can inject the protected database binding.
  // No secret is exported, logged, or copied into frontend assets.
  const migrationPackages = '/tmp/nexo-migration-packages';
  execFileSync('python3', ['-m', 'pip', 'install', '--disable-pip-version-check', '--target', migrationPackages, '-r', 'requirements.txt'], { cwd: root, stdio: 'inherit' });
  execFileSync('python3', ['-m', 'scripts.migrate'], { cwd: root, stdio: 'inherit', env: { ...process.env, PYTHONPATH: migrationPackages } });
}

for (const file of ['web/app.js', 'web/formula.js']) execFileSync(process.execPath, ['--check', new URL(file, root).pathname], { stdio: 'inherit' });
await rm(new URL('public/', root), { recursive: true, force: true });
await mkdir(new URL('public/', root), { recursive: true });
await cp(new URL('web/', root), new URL('public/', root), { recursive: true });
await mkdir(new URL('public/downloads/', root), { recursive: true });
execFileSync('python3', ['scripts/package_release.py', '--output', 'public/downloads/drap-office.zip'], { cwd: root, stdio: 'inherit' });
await cp(new URL('public/downloads/drap-office.zip', root), new URL('public/downloads/nexo.zip', root));
// No environment values are copied to application assets. The download is an explicit, credential-free source release.
console.log('Frontend compilado em public/. Backend: api/index.py.');
