import {build} from 'esbuild';
await build({entryPoints:['scripts/document-entry.js'],bundle:true,format:'esm',platform:'browser',target:'es2022',outfile:'web/document.js',minify:true,legalComments:'inline',define:{'process.env.NODE_ENV':'"production"'}});
