import {build} from 'esbuild';
import {readFile,writeFile,readdir} from 'node:fs/promises';
await build({entryPoints:['scripts/spreadsheet-entry.js'],bundle:true,format:'esm',platform:'browser',target:'es2022',outfile:'web/spreadsheet.js',minify:true,legalComments:'inline',define:{'process.env.NODE_ENV':'"production"'},loader:{'.woff2':'dataurl','.woff':'dataurl','.ttf':'dataurl','.svg':'dataurl','.png':'dataurl'}});
let notices='DRAP office — bibliotecas do editor de planilhas\n\n';
const entries=await readdir('node_modules',{withFileTypes:true});
const names=[];
for(const e of entries){if(e.name.startsWith('@')){for(const n of await readdir('node_modules/'+e.name))names.push(e.name+'/'+n);}else if(e.isDirectory())names.push(e.name);}
for(const name of names){for(const file of ['LICENSE','LICENSE.txt','LICENSE.md','license','LICENSE.MIT']){try{notices+='\n--- '+name+' ---\n'+await readFile('node_modules/'+name+'/'+file,'utf8');break;}catch{}}}
await writeFile('docs/licencas-planilha.txt',notices);
