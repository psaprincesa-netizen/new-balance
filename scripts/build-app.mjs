import {build} from 'esbuild';
await build({entryPoints:['web/app.js'],bundle:true,format:'esm',platform:'browser',
  target:'es2022',outfile:'web/app.bundle.js',minify:true,legalComments:'inline',
  external:['/document.js','/spreadsheet.js','/google.js']});
