// EchoStack Service Worker — works for BOTH the public site AND admin dashboard
const CACHE_NAME = 'echostack-v4';

// Pages to cache so both site and admin work offline/as PWA
const STATIC_CACHE = [
    '/',
    '/index.html',
    '/user-login',
    '/signup',
    '/app',
    '/dashboard',
    '/admin',
    '/echostack-logo.png',
    '/manifest.json'
];

// Install: cache all static pages immediately
self.addEventListener('install', event => {
    self.skipWaiting(); // don't wait — activate right away
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(STATIC_CACHE).catch(err => {
                console.warn('SW: some pages failed to cache:', err);
            });
        })
    );
});

// Activate: delete old caches, take control immediately
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.map(key => {
                    if (key !== CACHE_NAME) {
                        console.log('SW: deleting old cache:', key);
                        return caches.delete(key);
                    }
                })
            )
        ).then(() => self.clients.claim())
    );
});

// Fetch strategy:
// - API calls → always network (never cache — data must be fresh)
// - Everything else → network first, cache as fallback
self.addEventListener('fetch', event => {
    var url = event.request.url;

    // Always go to network for API calls — never serve stale data
    if (url.includes('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(JSON.stringify({ error: 'Offline' }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // For all pages (including /admin) — network first, cache fallback
    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Only cache successful GET responses
                if (event.request.method === 'GET' && response.status === 200) {
                    var clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            })
            .catch(() => {
                // Offline: serve from cache
                return caches.match(event.request).then(cached => {
                    if (cached) return cached;
                    // If nothing cached, serve homepage as fallback
                    return caches.match('/');
                });
            })
    );
});
