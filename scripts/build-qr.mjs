import {build} from 'esbuild';
await build({entryPoints:['scripts/qr-entry.js'],bundle:true,format:'esm',platform:'browser',target:'es2022',outfile:'web/qr.js',minify:true,legalComments:'inline'});
