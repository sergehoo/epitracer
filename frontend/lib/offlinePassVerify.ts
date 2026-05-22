'use client';

/**
 * offlinePassVerify — Vérification cryptographique des pass sanitaires
 * EpiTrace côté client, sans aller-retour serveur.
 *
 * Format du token : `EPMS1.<payload_b64u>.<signature_b64u>`
 *   - payload : JSON contenant tid, pid, name, dis, iss, iat, exp, ...
 *   - signature : Ed25519 sur le JSON brut (UTF-8)
 *
 * La clé publique Ed25519 est récupérée une seule fois depuis le backend
 * (`/api/v1/passes/public-key.pem`) puis cachée dans `localStorage`. Le
 * Service Worker la met aussi en cache HTTP pour le mode hors-ligne strict.
 *
 * Sécurité : on ne peut PAS révoquer un pass hors-ligne (la liste de
 * révocation requiert le backend). Le résultat `offline_only=true` doit
 * être affiché clairement à l'agent.
 */

import * as ed from '@noble/ed25519';
import { sha512 } from '@noble/hashes/sha2';

// ed25519@2.x nécessite que sha512 soit fourni manuellement (sync)
ed.hashes.sha512 = sha512;

const TOKEN_PREFIX = 'EPMS1';
const STORAGE_KEY = 'epitrace:pubkey:ed25519';
const STORAGE_KEY_DATE = 'epitrace:pubkey:fetched_at';
// Re-fetch la clé publique au-delà de 7 jours, pour permettre une éventuelle
// rotation côté serveur sans bloquer les agents qui sont hors-ligne longtemps.
const STALE_AFTER_MS = 7 * 24 * 3600 * 1000;

// ---------------------------------------------------------------------------
// Décodage base64url
// ---------------------------------------------------------------------------
function b64uToBytes(s: string): Uint8Array {
  // Convertit base64url → base64 standard puis utilise atob
  const b64 = s.replace(/-/g, '+').replace(/_/g, '/').padEnd(s.length + ((4 - (s.length % 4)) % 4), '=');
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// ---------------------------------------------------------------------------
// Extraction de la clé Ed25519 depuis un PEM SubjectPublicKeyInfo
// ---------------------------------------------------------------------------
function extractEd25519FromPem(pem: string): Uint8Array {
  const b64 = pem
    .replace(/-----BEGIN [A-Z ]+-----/g, '')
    .replace(/-----END [A-Z ]+-----/g, '')
    .replace(/\s+/g, '');
  const der = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  // Une SubjectPublicKeyInfo Ed25519 fait toujours 44 octets, avec la clé
  // brute (32 octets) en queue. On prend les 32 derniers octets.
  if (der.length < 32) throw new Error('Clé publique trop courte');
  return der.slice(der.length - 32);
}

// ---------------------------------------------------------------------------
// Récupération + cache de la clé publique
// ---------------------------------------------------------------------------
let _cachedKey: Uint8Array | null = null;

export async function loadPublicKey(apiBaseUrl: string, forceRefresh = false): Promise<Uint8Array> {
  if (_cachedKey && !forceRefresh) return _cachedKey;

  // 1) Tentative depuis localStorage
  if (!forceRefresh && typeof localStorage !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    const fetchedAt = parseInt(localStorage.getItem(STORAGE_KEY_DATE) || '0', 10);
    const isStale = Date.now() - fetchedAt > STALE_AFTER_MS;
    if (stored && !isStale) {
      try {
        _cachedKey = b64uToBytes(stored);
        return _cachedKey;
      } catch {
        // corrompu → on tombe sur le fetch
      }
    }
  }

  // 2) Fetch depuis le serveur
  const url = `${apiBaseUrl.replace(/\/$/, '')}/passes/public-key.pem`;
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`Téléchargement clé publique HTTP ${r.status}`);
  const pem = await r.text();
  const key = extractEd25519FromPem(pem);

  // 3) Cache mémoire + localStorage
  _cachedKey = key;
  if (typeof localStorage !== 'undefined') {
    const b64 = btoa(String.fromCharCode(...key))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    localStorage.setItem(STORAGE_KEY, b64);
    localStorage.setItem(STORAGE_KEY_DATE, String(Date.now()));
  }
  return key;
}

export function hasPublicKeyCached(): boolean {
  if (typeof localStorage === 'undefined') return false;
  return !!localStorage.getItem(STORAGE_KEY);
}

// ---------------------------------------------------------------------------
// Vérification d'un token
// ---------------------------------------------------------------------------
export interface OfflineVerifyResult {
  is_valid: boolean;
  reason?: string;
  /** True si le pass a expiré (mais signature OK) */
  is_expired?: boolean;
  /** Payload décodé (uniquement si signature valide) */
  payload?: Record<string, unknown>;
  /** True dans tous les cas où on n'a pas pu interroger le serveur */
  offline_only: true;
}

export async function verifyTokenOffline(
  token: string,
  apiBaseUrl: string,
): Promise<OfflineVerifyResult> {
  // Format
  const parts = token.trim().split('.');
  if (parts.length !== 3 || parts[0] !== TOKEN_PREFIX) {
    return { is_valid: false, reason: "Format de token invalide (attendu : EPMS1.<payload>.<signature>).", offline_only: true };
  }
  const [, payloadB64, sigB64] = parts;

  let payloadBytes: Uint8Array;
  let sigBytes: Uint8Array;
  let payload: Record<string, unknown>;
  try {
    payloadBytes = b64uToBytes(payloadB64);
    sigBytes = b64uToBytes(sigB64);
    payload = JSON.parse(new TextDecoder().decode(payloadBytes));
  } catch (e) {
    return { is_valid: false, reason: `Token mal formé : ${(e as Error).message}`, offline_only: true };
  }

  // Vérif signature
  let pubKey: Uint8Array;
  try {
    pubKey = await loadPublicKey(apiBaseUrl);
  } catch (e) {
    return {
      is_valid: false,
      reason: `Clé publique indisponible (${(e as Error).message}). Première vérification : connectez-vous à internet une fois.`,
      offline_only: true,
    };
  }

  let sigValid = false;
  try {
    sigValid = await ed.verifyAsync(sigBytes, payloadBytes, pubKey);
  } catch (e) {
    return { is_valid: false, reason: `Erreur cryptographique : ${(e as Error).message}`, offline_only: true };
  }

  if (!sigValid) {
    return { is_valid: false, reason: "Signature invalide — le pass a peut-être été altéré.", offline_only: true };
  }

  // Vérif expiration
  let expired = false;
  const exp = payload.exp;
  if (typeof exp === 'number') {
    expired = Date.now() / 1000 > exp;
  } else if (typeof exp === 'string') {
    const t = Date.parse(exp);
    if (!Number.isNaN(t)) expired = Date.now() > t;
  }

  if (expired) {
    return {
      is_valid: false,
      is_expired: true,
      reason: `Pass expiré le ${exp}.`,
      payload,
      offline_only: true,
    };
  }

  return {
    is_valid: true,
    reason: "Signature Ed25519 valide (vérification hors-ligne).",
    payload,
    offline_only: true,
  };
}
