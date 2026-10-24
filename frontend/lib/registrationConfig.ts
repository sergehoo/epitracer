/**
 * Configuration du questionnaire voyageur (maladies actives, questions,
 * symptômes) — chargée une fois et partagée entre les étapes 5 et 6.
 */
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { RegistrationConfig } from '@/types/portal';

// Repli si l'API est injoignable : questionnaire Ebola historique seul.
export const FALLBACK_CONFIG: RegistrationConfig = {
  ebola_questionnaire: true,
  common_symptom_fields: {},
  extra_symptoms: [],
  diseases: [],
};

let pending: Promise<RegistrationConfig> | null = null;

function loadConfig(): Promise<RegistrationConfig> {
  pending ??= api
    .get<RegistrationConfig>('/public/registration-config/')
    .then((r) => r.data)
    .catch(() => {
      pending = null; // nouvel essai au prochain affichage
      return FALLBACK_CONFIG;
    });
  return pending;
}

/** null tant que la configuration n'est pas chargée. */
export function useRegistrationConfig(): RegistrationConfig | null {
  const [config, setConfig] = useState<RegistrationConfig | null>(null);
  useEffect(() => {
    let alive = true;
    loadConfig().then((c) => { if (alive) setConfig(c); });
    return () => { alive = false; };
  }, []);
  return config;
}
