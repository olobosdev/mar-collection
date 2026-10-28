// Service worker: permite usar la web sin conexión (iPhone incluido).
const VERSION = 'mar-v1';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icon.svg', 'apple-touch-icon.png', 'icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== 'mar-img').map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Nunca cachear la API de GitHub (sincronización)
  if (url.hostname === 'api.github.com' || url.hostname.endsWith('githubusercontent.com')) return;

  // Imágenes de cartas: primero caché, luego red
  if (url.hostname === 'cards.scryfall.io') {
    e.respondWith(
      caches.open('mar-img').then(async (c) => {
        const hit = await c.match(req);
        if (hit) return hit;
        const res = await fetch(req);
        if (res.ok || res.type === 'opaque') c.put(req, res.clone());
        return res;
      })
    );
    return;
  }

  // Mismo origen (página y data/cards.json): primero red, si falla, caché
  if (url.origin === location.origin) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) caches.open(VERSION).then((c) => c.put(req, res.clone()));
          return res;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match('index.html')))
    );
  }
});
