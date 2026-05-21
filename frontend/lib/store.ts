/**
 * Store Zustand pour le formulaire d'enregistrement (multi-step).
 *
 * Les slots du store utilisent les types `Section*` du fichier `types/ebola.ts`
 * (champs optionnels) — c'est la forme la plus large, manipulée directement
 * par les Steps. Les schémas Zod (`*Input`) servent à la validation locale
 * de chaque step et sont compatibles structurellement.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  HistoryItem,
  SectionConfinement,
  SectionDeclaration,
  SectionExposure,
  SectionIdentite,
  SectionSymptoms,
  SectionVoyage,
} from '@/types/ebola';

interface RegistrationDraft {
  step: number;
  voyage?: SectionVoyage;
  identite?: SectionIdentite;
  historique?: HistoryItem[];
  confinement?: SectionConfinement;
  exposure?: SectionExposure;
  symptoms?: SectionSymptoms;
  declaration?: SectionDeclaration;
  set: (patch: Partial<RegistrationDraft>) => void;
  reset: () => void;
  goTo: (s: number) => void;
}

export const useRegistrationStore = create<RegistrationDraft>()(
  persist(
    (set) => ({
      step: 0,
      historique: [],
      set: (patch) => set((s) => ({ ...s, ...patch })),
      reset: () =>
        set({
          step: 0,
          historique: [],
          voyage: undefined,
          identite: undefined,
          confinement: undefined,
          exposure: undefined,
          symptoms: undefined,
          declaration: undefined,
        }),
      goTo: (s) => set({ step: s }),
    }),
    { name: 'epi.registration.draft' },
  ),
);
