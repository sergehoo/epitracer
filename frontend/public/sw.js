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
const CACHE = 'epitrace-v2-api-veillesanitaire';

const STATIC_ASSETS = [
  '/',
  '/voyageur',
  '/pass',
  '/verifier',
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
