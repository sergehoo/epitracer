/**
 * Service Worker minimal — EpiTravel CI
 *
 * Stratégie : Cache First pour les assets statiques + Stale-While-Revalidate
 * pour la consultation publique du pass (permet de consulter son pass
 * sans connexion une fois affiché au moins une fois).
 */
// Bump cette version à chaque redéploiement modifiant des chunks JS ou des
// variables NEXT_PUBLIC_*. L'event "activate" supprime les anciens caches,
// ce qui force tous les navigateurs (déjà installés) à refetch le nouveau
// bundle au prochain chargement. Sans ce bump, les clients avec le SW
// installé continueraient à servir les anciens chunks (et donc les anciennes
// URLs comme http://localhost:8000) depuis le cache "cache first".
const CACHE = 'epitrace-v18-pass-column-fix';

const STATIC_ASSETS = [
  '/',
  '/voyageur',
  '/voyageur/suivi',
  '/voyageur/confidentialite',
  '/pass',
  '/assistance',
  '/manifest.webmanifest',
  '/icons/icon-192.svg',
  '/icons/icon-512.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(STATIC_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // API publique de consultation du pass → stale-while-revalidate
  if (url.pathname.startsWith('/api/v1/ebola/public/pass/')) {
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {
        const cached = await cache.match(req);
        const fetchPromise = fetch(req)
          .then((res) => {
            if (res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  // Assets statiques → cache first
  if (
    url.origin === self.location.origin &&
    (req.destination === 'image' ||
      req.destination === 'style' ||
      req.destination === 'script' ||
      req.destination === 'font' ||
      url.pathname.startsWith('/icons/') ||
      url.pathname === '/manifest.webmanifest')
  ) {
    event.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          })
      )
    );
    return;
  }

  // Reste : réseau, fallback cache (utile pour les pages /pass/[id])
  event.respondWith(
    fetch(req).catch(() => caches.match(req).then((m) => m || caches.match('/')))
  );
});

// =============================================================================
// Web Push handlers — RFC 8030
//
// Payload attendu (envoyé par apps.companion.push.push_notify) :
//   { "title": "...", "body": "...", "url": "/voyageur/suivi", "tag": "..." }
//
// Le clic sur la notification ouvre l'URL fournie dans `data.url` ; si un
// onglet de la PWA est déjà ouvert, on le réutilise et on navigue à l'URL
// au lieu d'en ouvrir un nouveau.
// =============================================================================

self.addEventListener('push', (event) => {
  let payload = { title: 'EpiTrace', body: 'Vous avez une notification.', url: '/' };
  try {
    if (event.data) payload = { ...payload, ...event.data.json() };
  } catch {
    // Payload non-JSON (rare) — on garde les valeurs par défaut.
  }

  const title = payload.title || 'EpiTrace';
  const options = {
    body: payload.body || '',
    icon: '/icons/icon-192.svg',
    badge: '/icons/icon-192.svg',
    tag: payload.tag || 'epitrace',
    renotify: true,
    requireInteraction: payload.type === 'assistance_request',
    data: {
      url: payload.url || '/voyageur/suivi',
      type: payload.type || 'generic',
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || '/voyageur/suivi';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Si la PWA est déjà ouverte, naviguer dans l'onglet existant.
      for (const client of clientList) {
        if ('navigate' in client && 'focus' in client) {
          client.focus();
          return client.navigate(targetUrl);
        }
      }
      // Sinon ouvrir un nouvel onglet.
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
      return undefined;
    })
  );
});

// Optionnel : ré-abonner automatiquement si la subscription expire.
self.addEventListener('pushsubscriptionchange', (event) => {
  // Le client (page) refera un subscribe() au prochain chargement via le hook
  // `usePushSubscription` côté Next.js. On loggue simplement l'événement.
  event.waitUntil(
    self.registration.showNotification('Abonnement à renouveler', {
      body: 'Ouvrez l\'application pour rétablir les notifications.',
      icon: '/icons/icon-192.svg',
      tag: 'sub-change',
    })
  );
});
