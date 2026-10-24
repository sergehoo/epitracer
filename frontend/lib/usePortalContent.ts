'use client';

import { useEffect, useState } from 'react';
import { useLocale } from '@/lib/i18n';
import { fetchPublicDiseaseDetails, fetchPublicDiseases, fetchPublicNotices } from '@/lib/portal';
import type { PublicDisease, PublicDiseaseDetail, PublicNotice } from '@/types/portal';

export interface PortalContent {
  diseases: PublicDisease[];
  details: PublicDiseaseDetail[];
  notices: PublicNotice[];
}

/**
 * Contenus publiés de l'accueil dans la langue choisie : rendus côté serveur
 * en français ; en anglais, les traductions publiées sont rechargées (l'API
 * retombe sur le français quand une traduction manque).
 */
export function useLocalizedPortal(initial: PortalContent): PortalContent {
  const { locale } = useLocale();
  const [content, setContent] = useState(initial);

  useEffect(() => {
    if (locale === 'fr') {
      setContent(initial);
      return;
    }
    let alive = true;
    Promise.all([
      fetchPublicDiseases('?active=true&lang=en'),
      fetchPublicNotices(undefined, 'en'),
      fetchPublicDiseaseDetails(initial.details.map((d) => d.slug), 'en'),
    ]).then(([diseases, notices, details]) => {
      if (!alive) return;
      // Liste vide = API momentanément injoignable : on garde le contenu déjà affiché.
      setContent({
        diseases: diseases.length ? diseases : initial.diseases,
        notices: notices.length ? notices : initial.notices,
        details: details.length ? details : initial.details,
      });
    });
    return () => { alive = false; };
  }, [locale, initial]);

  return content;
}
