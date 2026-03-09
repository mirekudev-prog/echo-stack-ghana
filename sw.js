// EchoStack Service Worker — enhanced for performance and reliability
const CACHE_NAME = 'echostack-v5';
const STATIC_CACHE = 'echostack-static-v5';
const OFFLINE_URL = '/offline.html';   // Create this simple page (see note below)

// Assets that rarely change – cache them aggressively
const ASSETS_TO_CACHE = [
    '/echostack-logo.png',
    '/manifest.json',
    '/sw.js',
    // Add any other static assets (CSS, JS, fonts) if you have them
];

// Pages to cache on install – these will be available offline
const PAGES_TO_CACHE = [
    '/',
    '/index.html',
    '/user-login',
    '/signup',
    '/app',
    '/dashboard',
    '/admin',
    OFFLINE_URL, // ensure offline page is cached
];

// Install: cache all static assets and pages individually,
// so that one failure doesn't break the whole installation
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        Promise.all([
            // Static assets cache: try to cache each asset individually
            caches.open(STATIC_CACHE).then(cache => 
                Promise.allSettled(
                    ASSETS_TO_CACHE.map(url =>
                        cache.add(url).catch(err => {
                            console.warn(`SW: failed to cache static asset ${url}:`, err);
                        })
                    )
                )
            ),
            // Pages cache: try to cache each page individually
            caches.open(CACHE_NAME).then(cache => 
                Promise.allSettled(
                    PAGES_TO_CACHE.map(url =>
                        cache.add(url).catch(err => {
                            console.warn(`SW: failed to cache page ${url}:`, err);
                        })
                    )
                )
            )
        ]).then(() => {
            console.log('SW: installation completed (some items may not be cached)');
        })
    );
});

// Activate: delete old caches and take control immediately
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

// Helper: determine if request is for a static asset (image, font, etc.)
function isStaticAsset(url) {
    const extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.css', '.js', '.woff', '.woff2', '.ttf'];
    return extensions.some(ext => url.endsWith(ext));
}

// Fetch strategy
self.addEventListener('fetch', event => {
    const url = event.request.url;
    const request = event.request;

    // 1. API calls → always network (never cache)
    if (url.includes('/api/')) {
        event.respondWith(
            fetch(request).catch(() => {
                return new Response(JSON.stringify({ error: 'You are offline. Please check your connection.' }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // 2. Static assets (images, fonts, CSS, JS) → cache-first, network fallback
    if (isStaticAsset(url)) {
        event.respondWith(
            caches.match(request).then(cached => {
                if (cached) return cached;
                return fetch(request).then(response => {
                    if (response && response.status === 200) {
                        const clone = response.clone();
                        caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
                    }
                    return response;
                });
            })
        );
        return;
    }

    // 3. All other requests (pages, etc.) → network-first, cache fallback
    event.respondWith(
        fetch(request)
            .then(response => {
                if (request.method === 'GET' && response.status === 200) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
                }
                return response;
            })
            .catch(() => {
                return caches.match(request).then(cached => {
                    if (cached) return cached;
                    // If all else fails, show offline page
                    return caches.match(OFFLINE_URL);
                });
            })
    );
});
