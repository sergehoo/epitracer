/**
 * Lecture des contenus publics publiés (fiches maladies, alertes, recommandations).
 *
 * Utilisable côté serveur (pages SEO, rendu ISR) comme côté client. Les
 * listes se dégradent en résultat vide si l'API est indisponible (build,
 * coupure réseau) ; une fiche, elle, ne renvoie « introuvable » que sur un 404.
 */
import type { PublicAlertLevel, PublicDisease, PublicDiseaseDetail, PublicNotice } from '@/types/portal';

const PUBLIC_API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Serveur : URL interne d'abord (réseau Docker, ex. http://web:8000), puis
 * l'URL publique en secours — un conteneur ne joint pas toujours l'URL
 * publique de son propre hôte. Navigateur : même base que lib/api.ts.
 */
const SERVER_BASES = [process.env.INTERNAL_API_URL, PUBLIC_API].filter(
  (base, i, all): base is string => !!base && all.indexOf(base) === i,
);

/** Délai de revalidation des pages publiques (secondes). */
export const PORTAL_REVALIDATE = 300;

class PortalUnavailableError extends Error {}

/** null si la ressource n'existe pas (404) ; lève PortalUnavailableError si l'API est injoignable. */
async function getJson<T>(path: string): Promise<T | null> {
  const onServer = typeof window === 'undefined';
  const headers: Record<string, string> = { Accept: 'application/json' };
  // Le saut interne est en HTTP : sans cet en-tête, SECURE_SSL_REDIRECT de
  // Django redirigerait vers https://web:8000 (injoignable).
  if (onServer) headers['X-Forwarded-Proto'] = 'https';
  const failures: string[] = [];
  for (const base of onServer ? SERVER_BASES : [PUBLIC_API]) {
    let res: Response;
    try {
      res = await fetch(`${base}/api/v1/public/${path}`, {
        headers,
        next: { revalidate: PORTAL_REVALIDATE },
      } as RequestInit);
    } catch (e) {
      const err = e as Error & { cause?: { code?: string; message?: string } };
      failures.push(`${base} : ${err.cause?.code || err.cause?.message || err.message}`);
      continue;
    }
    if (res.status === 404) return null;
    if (res.ok) return (await res.json()) as T;
    failures.push(`${base} : HTTP ${res.status}`);
  }
  throw new PortalUnavailableError(`API publique injoignable — ${failures.join(' ; ')}`);
}

/** Listes : contenu vide si l'API est indisponible (build, coupure) — le portail reste utilisable. */
async function getList<T>(path: string): Promise<T[]> {
  try {
    return (await getJson<T[]>(path)) ?? [];
  } catch {
    return [];
  }
}

export async function fetchPublicDiseases(query = ''): Promise<PublicDisease[]> {
  return getList<PublicDisease>(`diseases/${query}`);
}

/**
 * Fiche : null uniquement si elle n'est pas publiée (vrai 404). Une API
 * indisponible lève une erreur : Next conserve alors la page déjà en cache
 * au lieu de servir un faux « introuvable ».
 */
export async function fetchPublicDisease(slug: string): Promise<PublicDiseaseDetail | null> {
  if (!/^[a-z0-9-]+$/.test(slug)) return null;
  return getJson<PublicDiseaseDetail>(`diseases/${slug}/`);
}

export async function fetchPublicNotices(
  kind?: 'alert' | 'recommendation', lang?: string,
): Promise<PublicNotice[]> {
  const params = new URLSearchParams();
  if (kind) params.set('kind', kind);
  if (lang) params.set('lang', lang);
  const qs = params.toString();
  return getList<PublicNotice>(`notices/${qs ? `?${qs}` : ''}`);
}

/** Niveau d'alerte public → libellé + classes (couleurs nationales). */
export const ALERT_LEVEL_STYLE: Record<PublicAlertLevel, { label: string; className: string }> = {
  normal:   { label: 'Veille',            className: 'bg-emerald-50 text-emerald-800 ring-emerald-200' },
  moderate: { label: 'Vigilance',         className: 'bg-amber-50 text-amber-800 ring-amber-200' },
  high:     { label: 'Alerte',            className: 'bg-orange-50 text-orange-800 ring-orange-200' },
  critical: { label: 'Urgence sanitaire', className: 'bg-red-700 text-white ring-red-800' },
};

export const ALERT_LEVEL_ORDER: PublicAlertLevel[] = ['critical', 'high', 'moderate', 'normal'];
