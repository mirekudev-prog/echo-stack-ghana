const CACHE_NAME = 'echostack-v2';
const urlsToCache = [
    '/',
    '/index.html',
    '/manifest.json',
    '/echostack-logo.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .catch(err => console.warn('Cache install error (non-fatal):', err))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(name => {
                    if (name !== CACHE_NAME) return caches.delete(name);
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});
```

---

### 📄 File 3: `admin_dashboard.html`
Find the line near the top that says:
```
<!-- ✅ FIX: Google Fonts loaded as <link> tags...
