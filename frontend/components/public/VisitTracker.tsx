'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';

/**
 * VisitTracker — envoie un page-view à l'API à chaque navigation.
 *
 * - Génère un session_id stable côté client (localStorage).
 * - Inclut langue, timezone et referrer.
 * - Détecte le portail public/admin via le hostname.
 * - Best-effort : on swallow toute erreur réseau pour ne pas perturber l'UX.
 */
function getOrCreateSessionId() {
  if (typeof window === 'undefined') return '';
  let sid = localStorage.getItem('epi_sid');
  if (!sid) {
    sid =
      (crypto.randomUUID?.() as string | undefined) ??
      `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem('epi_sid', sid);
  }
  return sid;
}

export function VisitTracker() {
  const pathname = usePathname();

  useEffect(() => {
    if (typeof window === 'undefined' || !pathname) return;
    const host = window.location.host.toLowerCase();
    const portal =
      host.includes('admin.veillesanitaire')
      || host.includes('admin.lvh.me')
      || host.startsWith('admin.')
        ? 'admin'
        : 'public';
    const payload = {
      session_id: getOrCreateSessionId(),
      path: pathname,
      portal,
      referrer: document.referrer || '',
      language: navigator.language || '',
      timezone:
        Intl.DateTimeFormat?.().resolvedOptions?.().timeZone || '',
    };
    api.post('/analytics/visits/track/', payload).catch(() => undefined);
  }, [pathname]);

  return null;
}
