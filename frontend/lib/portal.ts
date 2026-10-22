/**
 * Lecture des contenus publics publiés (fiches maladies, alertes, recommandations).
 *
 * Utilisable côté serveur (pages SEO, rendu ISR) comme côté client. Les
 * listes se dégradent en résultat vide si l'API est indisponible (build,
 * coupure réseau) ; une fiche, elle, ne renvoie « introuvable » que sur un 404.
 */
import type { PublicAlertLevel, PublicDisease, PublicDiseaseDetail, PublicNotice } from '@/types/portal';

const SERVER_API =
  process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Délai de revalidation des pages publiques (secondes). */
export const PORTAL_REVALIDATE = 300;

class PortalUnavailableError extends Error {}

/** null si la ressource n'existe pas (404) ; lève PortalUnavailableError si l'API est injoignable. */
async function getJson<T>(path: string): Promise<T | null> {
  // Navigateur : même base que lib/api.ts ; serveur : URL interne si fournie.
  const base = typeof window === 'undefined'
    ? SERVER_API
    : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  let res: Response;
  try {
    res = await fetch(`${base}/api/v1/public/${path}`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: PORTAL_REVALIDATE },
    } as RequestInit);
  } catch (e) {
    throw new PortalUnavailableError(`API publique injoignable : ${(e as Error).message}`);
  }
  if (res.status === 404) return null;
  if (!res.ok) throw new PortalUnavailableError(`API publique : HTTP ${res.status}`);
  return (await res.json()) as T;
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

export async function fetchPublicNotices(kind?: 'alert' | 'recommendation'): Promise<PublicNotice[]> {
  return getList<PublicNotice>(`notices/${kind ? `?kind=${kind}` : ''}`);
}

/** Niveau d'alerte public → libellé + classes (couleurs nationales). */
export const ALERT_LEVEL_STYLE: Record<PublicAlertLevel, { label: string; className: string }> = {
  normal:   { label: 'Veille',            className: 'bg-emerald-50 text-ciGreen ring-emerald-200' },
  moderate: { label: 'Vigilance',         className: 'bg-amber-50 text-amber-800 ring-amber-200' },
  high:     { label: 'Alerte',            className: 'bg-orange-50 text-ciOrange ring-orange-200' },
  critical: { label: 'Urgence sanitaire', className: 'bg-red-700 text-white ring-red-800' },
};

export const ALERT_LEVEL_ORDER: PublicAlertLevel[] = ['critical', 'high', 'moderate', 'normal'];
