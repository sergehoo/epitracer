/** Store Zustand pour le formulaire d'enregistrement (multi-step). */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  ConfinementInput, DeclarationInput, ExposureInput,
  IdentiteInput, SymptomsInput, VoyageInput,
} from './schema';
import type { HistoryItem } from '@/types/ebola';

interface RegistrationDraft {
  step: number;
  voyage?: VoyageInput;
  identite?: IdentiteInput;
  historique?: HistoryItem[];
  confinement?: ConfinementInput;
  exposure?: ExposureInput;
  symptoms?: SymptomsInput;
  declaration?: DeclarationInput;
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
      reset: () => set({ step: 0, historique: [], voyage: undefined, identite: undefined, confinement: undefined, exposure: undefined, symptoms: undefined, declaration: undefined }),
      goTo: (s) => set({ step: s }),
    }),
    { name: 'epi.registration.draft' },
  ),
);
