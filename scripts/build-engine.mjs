import { build } from 'esbuild';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
await build({entryPoints:['scripts/formula-engine-entry.js'],bundle:true,format:'esm',platform:'browser',target:'es2022',outfile:'web/formula-engine.js',minify:true,legalComments:'inline'});
const packages=['fast-formula-parser','chevrotain','jstat','bessel','bahttext','regexp-to-ast'];
let licenses='Dependências do motor de fórmulas DRAP office\n\n';
for (const name of packages) {
  for (const file of ['LICENSE','LICENSE.txt','LICENSE.md']) {
    try { licenses+='\n--- '+name+' ---\n'+await readFile('node_modules/'+name+'/'+file,'utf8'); break; } catch {}
  }
}
await mkdir('docs',{recursive:true});
await writeFile('docs/licencas-formulas.txt',licenses);
