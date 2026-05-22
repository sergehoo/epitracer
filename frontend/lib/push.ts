/**
 * Helpers Web Push côté PWA voyageur.
 *
 * Le flux d'abonnement complet (consentement → permission navigateur →
 * subscription → enregistrement serveur) est encapsulé dans
 * `subscribeUserToPush()`. Tous les cas d'erreur sont gérés et retournés
 * sous forme typée (jamais d'exception qui remonte à l'UI).
 */

import { api } from '@/lib/api';
import { recordConsent } from '@/lib/companion';

/**
 * Décode une string base64url (sans padding) en Uint8Array.
 * Format attendu par `pushManager.subscribe({applicationServerKey})`.
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

export type PushSubscribeResult =
  | { ok: true; subscriptionId: string }
  | { ok: false; reason: 'unsupported' | 'denied' | 'service_worker_missing' | 'no_public_key' | 'consent_required' | 'network_error' };

/**
 * Récupère la clé publique VAPID exposée par le backend.
 * Mis en cache côté module pour éviter un round-trip à chaque souscription.
 */
let _cachedKey: string | null = null;
export async function getVapidPublicKey(): Promise<string | null> {
  if (_cachedKey) return _cachedKey;
  try {
    const { data } = await api.get<{ public_key: string }>('/public/push/public-key/');
    _cachedKey = data.public_key;
    return _cachedKey;
  } catch {
    return null;
  }
}

/**
 * Vérifie si le navigateur supporte Web Push.
 */
export function isPushSupported(): boolean {
  if (typeof window === 'undefined') return false;
  return (
    'serviceWorker' in navigator
    && 'PushManager' in window
    && 'Notification' in window
  );
}

/**
 * Détecte si l'utilisateur a déjà refusé les notifications au niveau OS.
 * (Une fois refusé, on ne peut plus afficher la popup — il faut passer par
 * les réglages du navigateur.)
 */
export function isPermissionDenied(): boolean {
  if (typeof window === 'undefined' || !('Notification' in window)) return false;
  return Notification.permission === 'denied';
}

/**
 * Récupère la subscription Web Push actuelle (s'il y en a une).
 */
export async function getExistingSubscription(): Promise<PushSubscription | null> {
  if (!isPushSupported()) return null;
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return null;
  return (await reg.pushManager.getSubscription()) || null;
}

/**
 * Inscrit le voyageur aux notifications push :
 *  1. Demande la permission navigateur (popup) ;
 *  2. Crée la subscription via le service worker ;
 *  3. Enregistre le consentement explicite scope=push côté serveur ;
 *  4. Envoie la subscription au serveur (qui vérifie le consentement).
 */
export async function subscribeUserToPush(publicId: string): Promise<PushSubscribeResult> {
  if (!isPushSupported()) return { ok: false, reason: 'unsupported' };

  // 1. Permission navigateur
  let perm: NotificationPermission = Notification.permission;
  if (perm === 'default') {
    perm = await Notification.requestPermission();
  }
  if (perm !== 'granted') return { ok: false, reason: 'denied' };

  // 2. Service worker enregistré
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return { ok: false, reason: 'service_worker_missing' };

  // 3. Clé publique VAPID
  const pubKey = await getVapidPublicKey();
  if (!pubKey) return { ok: false, reason: 'no_public_key' };

  // 4. Consentement serveur (idempotent — append-only)
  try {
    await recordConsent(
      publicId,
      'push',
      true,
      'J\'autorise EpiTrace à m\'envoyer des rappels sanitaires.',
    );
  } catch {
    return { ok: false, reason: 'network_error' };
  }

  // 5. Souscription navigateur
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    try {
      // Cast nécessaire : TypeScript lib.dom déclare applicationServerKey
      // comme BufferSource, mais l'API accepte aussi Uint8Array (RFC).
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true, // Obligatoire (Chrome refuse les push silencieux)
        applicationServerKey: urlBase64ToUint8Array(pubKey) as unknown as BufferSource,
      });
    } catch {
      return { ok: false, reason: 'denied' };
    }
  }

  // 6. Envoi au serveur
  try {
    const payload = sub.toJSON();
    const ua = navigator.userAgent || '';
    const isMobile = /Mobi|Android|iPhone|iPad/i.test(ua);
    const { data } = await api.post<{ subscription_id: string }>('/public/push/subscribe/', {
      public_id: publicId,
      subscription: {
        endpoint: payload.endpoint,
        keys: payload.keys,
      },
      user_agent: ua.slice(0, 300),
      device_type: isMobile ? 'mobile' : 'desktop',
      locale: navigator.language || '',
    });
    return { ok: true, subscriptionId: data.subscription_id };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '';
    if (msg.includes('403')) return { ok: false, reason: 'consent_required' };
    return { ok: false, reason: 'network_error' };
  }
}

/**
 * Désabonne le voyageur (navigateur + serveur).
 */
export async function unsubscribeUserFromPush(publicId: string): Promise<boolean> {
  const sub = await getExistingSubscription();
  if (!sub) return true;
  const endpoint = sub.endpoint;
  try {
    await sub.unsubscribe();
  } catch {
    // ignore — on essaie quand même côté serveur
  }
  try {
    await api.post('/public/push/unsubscribe/', { public_id: publicId, endpoint });
    await recordConsent(publicId, 'push', false, '', 'Désabonnement depuis la PWA');
    return true;
  } catch {
    return false;
  }
}
