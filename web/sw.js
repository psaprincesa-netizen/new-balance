// DRAP office service worker.
// Keeps the application shell available offline. Account data is never cached:
// /api/ and downloads always go to the network, so private files are not
// stored in Cache Storage and logging out leaves nothing readable behind.
const CACHE = 'drap-shell-v1';
const SHELL = [
  '/',
  '/style.css',
  '/app.js',
  '/workflows.js',
  '/slides.js',
  '/pivot-ui.js',
  '/pivot.js',
  '/chart.js',
  '/formula.js',
  '/formula-engine.js',
  '/manifest.webmanifest',
  '/icons/icon.svg',
  '/icons/icon-192.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(SHELL.map((url) => new Request(url, {cache: 'reload'}))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith('drap-') && key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

function cacheable(url, request) {
  if (request.method !== 'GET' || url.origin !== self.location.origin) return false;
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/downloads/')) return false;
  if (url.pathname === '/sw.js') return false;
  // Public form links carry a token in the query string; keep them out of the cache.
  if (url.search) return false;
  return true;
}

// Network first: file names are not content-hashed, so a cache-first strategy
// could mix old and new modules after a deploy. The cache is only a fallback.
async function networkFirst(event) {
  const {request} = event;
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    // Store in the background so large bundles reach the page without waiting for the cache write.
    if (response.ok && response.type === 'basic') event.waitUntil(cache.put(request, response.clone()));
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    if (request.mode === 'navigate') {
      const shell = await cache.match('/');
      if (shell) return shell;
    }
    throw error;
  }
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.mode === 'navigate' && url.origin === self.location.origin && !url.pathname.startsWith('/api/') && !cacheable(url, event.request)) {
    // Navigations with a query string (for example ?form= links) are not stored,
    // but still fall back to the cached shell when offline.
    event.respondWith(fetch(event.request).catch(async () => (await caches.match('/')) || Response.error()));
    return;
  }
  if (!cacheable(url, event.request)) return;
  event.respondWith(networkFirst(event));
});
