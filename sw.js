const CACHE_NAME = 'echostack-v2';
const urlsToCache = [
    '/',
    '/index.html',
    '/manifest.json',
    '/echostack-logo.png'
    // NOTE: /admin is intentionally excluded — it requires auth and will fail caching
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .catch(err => console.warn('Cache install error (non-fatal):', err))
    );
    // Force the new SW to activate immediately
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    // Take control of all open clients immediately
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});
