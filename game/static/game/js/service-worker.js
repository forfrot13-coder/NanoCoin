/**
 * NanoCoin Game Service Worker
 * Provides offline support and caching for PWA functionality
 */

const CACHE_VERSION = 'nanocoin-v1';
const CACHE_NAMES = {
    STATIC: 'nanocoin-static-v1',
    API: 'nanocoin-api-v1',
    DATA: 'nanocoin-data-v1',
};

// URLs to cache on install
const STATIC_URLS = [
    '/',
    '/static/game/css/animations.css',
    '/static/game/js/api.js',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    
    event.waitUntil(
        caches.open(CACHE_NAMES.STATIC)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_URLS);
            })
            .then(() => {
                console.log('[SW] Static assets cached');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Install failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => {
                            // Delete caches that are not current version
                            return Object.values(CACHE_NAMES).indexOf(name) === -1;
                        })
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Service worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension and other non-http(s) requests
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    // API requests - Network first, fallback to cache
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request, CACHE_NAMES.API));
        return;
    }
    
    // Static assets - Cache first, fallback to network
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(request, CACHE_NAMES.STATIC));
        return;
    }
    
    // HTML pages - Network first, fallback to cache
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(networkFirst(request, CACHE_NAMES.DATA));
        return;
    }
    
    // Default - Network first
    event.respondWith(networkFirst(request));
});

// Network first strategy
async function networkFirst(request, cacheName = null) {
    try {
        const networkResponse = await fetch(request);
        
        // Clone the response before caching
        const responseClone = networkResponse.clone();
        
        // Cache the response if cacheName provided
        if (cacheName) {
            const cache = await caches.open(cacheName);
            cache.put(request, responseClone);
        }
        
        return networkResponse;
    } catch (error) {
        // Network failed, try cache
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page for navigation requests
        if (request.headers.get('accept')?.includes('text/html')) {
            const offlineResponse = await caches.match('/');
            if (offlineResponse) {
                return offlineResponse;
            }
        }
        
        throw error;
    }
}

// Cache first strategy
async function cacheFirst(request, cacheName) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        // Return cached response and update cache in background
        fetchAndCache(request, cacheName);
        return cachedResponse;
    }
    
    return fetchAndCache(request, cacheName);
}

// Fetch and cache helper
async function fetchAndCache(request, cacheName) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('[SW] Fetch failed:', error);
        throw error;
    }
}

// Handle messages from the main thread
self.addEventListener('message', (event) => {
    const { type, payload } = event.data;
    
    switch (type) {
        case 'CACHE_URLS':
            // Cache additional URLs
            event.waitUntil(
                caches.open(CACHE_NAMES.DATA)
                    .then((cache) => {
                        return cache.addAll(payload.urls);
                    })
            );
            break;
            
        case 'CLEAR_CACHE':
            // Clear all caches
            event.waitUntil(
                caches.keys().then((cacheNames) => {
                    return Promise.all(
                        cacheNames.map((name) => caches.delete(name))
                    );
                })
            );
            break;
            
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
    }
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-pending-actions') {
        event.waitUntil(syncPendingActions());
    }
});

// Sync pending offline actions
async function syncPendingActions() {
    // Get pending actions from IndexedDB and sync them
    console.log('[SW] Syncing pending actions...');
    // Implementation would go here
}

// Push notifications (for future use)
self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.body,
            icon: '/static/game/img/icon-192.png',
            badge: '/static/game/img/badge-72.png',
            vibrate: [100, 50, 100],
            data: {
                url: data.url || '/',
            },
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then((clientList) => {
            const url = event.notification.data.url;
            
            // Focus existing window or open new one
            for (const client of clientList) {
                if (client.url === url && 'focus' in client) {
                    return client.focus();
                }
            }
            
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});

console.log('[SW] Service worker loaded');
