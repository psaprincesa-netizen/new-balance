import {build} from 'esbuild';
// qrcode-generator keeps its notice in // comments, which minification drops; restate it.
const banner='/*! qrcode-generator 2.0.4 | Copyright (c) 2009 Kazuhiko Arase | MIT license: http://www.opensource.org/licenses/mit-license.php */';
await build({entryPoints:['scripts/qr-entry.js'],bundle:true,format:'esm',platform:'browser',target:'es2022',outfile:'web/qr.js',minify:true,legalComments:'inline',banner:{js:banner}});
