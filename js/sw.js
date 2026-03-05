const CACHE_NAME = 'echostack-v1';
const urlsToCache = [
    '/',
    '/index.html',
    '/admin',
    '/login',
    '/echostack-logo.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});
