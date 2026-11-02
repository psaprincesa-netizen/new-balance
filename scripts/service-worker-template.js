// Only the public offline notice is cached. Accounts, API responses, files and
// editor bundles always use the network. Activation never reloads open editors.
const CACHE='drap-offline-__OFFLINE_VERSION__';
const OFFLINE='/offline.html';
self.addEventListener('install',event=>{
  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    const response=await fetch(OFFLINE,{cache:'reload',credentials:'omit'});
    if(!response.ok)throw Error('Offline page unavailable');
    await cache.put(OFFLINE,response);
    await self.skipWaiting();
  })());
});
self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    for(const key of await caches.keys())if(key.startsWith('drap-offline-')&&key!==CACHE)await caches.delete(key);
    await self.clients.claim();
  })());
});
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.origin!==self.location.origin||event.request.mode!=='navigate'||!['/','/install','/install/','/install.html'].includes(url.pathname))return;
  event.respondWith(fetch(event.request).catch(async()=>{
    const cache=await caches.open(CACHE);
    return await cache.match(OFFLINE)||new Response('Sem conexão. Reconecte-se e tente novamente.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});
  }));
});
