// EchoStack Service Worker — enhanced for performance and reliability
const CACHE_NAME = 'echostack-v5';
const STATIC_CACHE = 'echostack-static-v5';
const OFFLINE_URL = '/offline.html';   // Create this simple page

const ASSETS_TO_CACHE = [
    '/echostack-logo.png',
    '/manifest.json',
    '/sw.js',
    // Add other static assets
];

const PAGES_TO_CACHE = [
    '/',
    '/index.html',
    '/user-login',
    '/signup',
    '/app',
    '/dashboard',
    '/admin',
    '/subscribers',        // <--- added subscribers route
    OFFLINE_URL,
];

// Install: cache each file individually so one failure doesn't break install
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        Promise.all([
            caches.open(STATIC_CACHE).then(cache =>
                Promise.allSettled(
                    ASSETS_TO_CACHE.map(url =>
                        cache.add(url).catch(err => console.warn(`SW: failed to cache ${url}:`, err))
                    )
                )
            ),
            caches.open(CACHE_NAME).then(cache =>
                Promise.allSettled(
                    PAGES_TO_CACHE.map(url =>
                        cache.add(url).catch(err => console.warn(`SW: failed to cache page ${url}:`, err))
                    )
                )
            )
        ]).then(() => console.log('SW: installation completed (some items may not be cached)'))
    );
});

// Activate: delete old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.map(key => {
                    if (key !== CACHE_NAME && key !== STATIC_CACHE) {
                        console.log('SW: deleting old cache:', key);
                        return caches.delete(key);
                    }
                })
            )
        ).then(() => self.clients.claim())
    );
});

// Helper: static asset detection
function isStaticAsset(url) {
    const extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.css', '.js', '.woff', '.woff2', '.ttf'];
    return extensions.some(ext => url.endsWith(ext));
}

// Fetch strategy
self.addEventListener('fetch', event => {
    const url = event.request.url;
    const request = event.request;

    // 1. API calls (including /api/subscribers if you move it) → network only
    if (url.includes('/api/')) {
        event.respondWith(
            fetch(request).catch(() => 
                new Response(JSON.stringify({ error: 'Offline' }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                })
            )
        );
        return;
    }

    // 2. Static assets → cache-first
    if (isStaticAsset(url)) {
        event.respondWith(
            caches.match(request).then(cached => 
                cached || fetch(request).then(response => {
                    if (response.status === 200) {
                        const clone = response.clone();
                        caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
                    }
                    return response;
                })
            )
        );
        return;
    }

    // 3. All other requests (including /subscribers) → network-first, fallback to cache, then offline page
    event.respondWith(
        fetch(request)
            .then(response => {
                if (request.method === 'GET' && response.status === 200) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
                }
                return response;
            })
            .catch(() => 
                caches.match(request).then(cached => cached || caches.match(OFFLINE_URL))
            )
    );
});
