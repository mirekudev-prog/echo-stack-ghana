const CACHE_NAME = 'echostack-v2';
const urlsToCache = [
    '/',
    '/index.html',
    '/admin',
    '/user-login',
    '/signup',
    '/app',
    '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Cache opened:', CACHE_NAME);
                // Add each URL individually to avoid failing on missing files
                return Promise.all(
                    urlsToCache.map(url => {
                        return fetch(url)
                            .then(response => {
                                if (response.ok) {
                                    console.log('Caching:', url);
                                    return cache.put(url, response);
                                }
                                console.warn('Skipping (not found):', url);
                                return Promise.resolve();
                            })
                            .catch(error => {
                                console.warn('Failed to cache:', url, error);
                                return Promise.resolve();
                            });
                    })
                );
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Cache hit - return response
                if (response) {
                    return response;
                }
                
                // Clone the request
                const fetchRequest = event.request.clone();
                
                return fetch(fetchRequest).then(response => {
                    // Check if we received a valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // Clone the response
                    const responseToCache = response.clone();
                    
                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    
                    return response;
                }).catch(error => {
                    console.error('Fetch failed:', error);
                    // Return offline page or fallback
                    return caches.match('/index.html');
                });
            })
    );
});
