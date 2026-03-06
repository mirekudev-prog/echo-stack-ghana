// EchoStack Service Worker - Fixed Version
const CACHE_NAME = 'echostack-v3';

// Only cache GET-able static assets - NO index.html (served dynamically by FastAPI)
const STATIC_ASSETS = [
  '/',
  '/signup',
  '/user-login',
  '/app',
  '/manifest.json',
  '/echostack-logo.png'
];

// ── Install: cache static assets ─────────────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      const results = await Promise.allSettled(
        STATIC_ASSETS.map(async (url) => {
          try {
            // Use a plain GET request - never POST
            const response = await fetch(url, { method: 'GET' });
            if (response.ok) {
              await cache.put(url, response);
              console.log(`[SW] Cached: ${url}`);
            } else {
              console.warn(`[SW] Skipping (${response.status}): ${url}`);
            }
          } catch (err) {
            console.warn(`[SW] Skipping (not found): ${url}`);
          }
        })
      );
      return results;
    })
  );
  self.skipWaiting();
});

// ── Activate: delete old caches ───────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log(`[SW] Deleting old cache: ${key}`);
            return caches.delete(key);
          })
      );
    })
  );
  self.clients.claim();
});

// ── Fetch: network-first for API, cache-first for static ─────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // CRITICAL FIX: Never intercept non-GET requests (POST, PUT, DELETE, etc.)
  // Attempting to cache POST requests causes the TypeError you saw in the console
  if (request.method !== 'GET') {
    return; // Let the browser handle it normally
  }

  // Never cache API calls - always go to network
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  // Never cache admin routes
  if (url.pathname.startsWith('/admin')) {
    event.respondWith(fetch(request));
    return;
  }

  // For everything else: network-first, fall back to cache
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Only cache successful GET responses
        if (response.ok && request.method === 'GET') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Network failed - try cache
        return caches.match(request).then((cached) => {
          if (cached) return cached;
          // Return offline fallback for navigation requests
          if (request.mode === 'navigate') {
            return caches.match('/');
          }
          return new Response('Offline', { status: 503 });
        });
      })
  );
});
