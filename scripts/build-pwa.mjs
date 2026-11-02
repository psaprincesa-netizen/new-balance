import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=new URL('../',import.meta.url);
const template=await readFile(new URL('scripts/service-worker-template.js',root),'utf8');
const offline=await readFile(new URL('web/offline.html',root));
const version=createHash('sha256').update(offline).update(template).digest('hex').slice(0,16);
await writeFile(new URL('web/service-worker.js',root),template.replace('__OFFLINE_VERSION__',version));

await writeFile(new URL('web/sw.js',root),template.replace('__OFFLINE_VERSION__',version));
