'use client';

import { useMemo } from 'react';
import { useLocalizedPortal } from '@/lib/usePortalContent';
import type { PublicDisease, PublicDiseaseDetail, PublicNotice } from '@/types/portal';
import { DiseasesSection } from './DiseasesSection';
import { PreventionSection } from './PreventionSection';
import { SymptomsSection } from './SymptomsSection';
import { TravelerMeasures } from './TravelerMeasures';

/**
 * Bloc sanitaire de l'accueil, placé avant les sections touristiques :
 * alertes et surveillance, prévention, mesures voyageurs, symptômes.
 * Un seul chargement des contenus publiés (et de leur traduction anglaise)
 * pour les quatre sections.
 */
export function HealthHub({
  diseases, details, notices,
}: {
  diseases: PublicDisease[];
  details: PublicDiseaseDetail[];
  notices: PublicNotice[];
}) {
  const initial = useMemo(() => ({ diseases, details, notices }), [diseases, details, notices]);
  const content = useLocalizedPortal(initial);
  return (
    <>
      <DiseasesSection diseases={content.diseases} notices={content.notices} />
      <PreventionSection details={content.details} />
      <TravelerMeasures diseases={content.diseases} details={content.details} notices={content.notices} />
      <SymptomsSection details={content.details} />
    </>
  );
}
