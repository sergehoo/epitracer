/**
 * Points d'entrée proposés selon le moyen de transport.
 * Copie de la règle serveur (backend/apps/travelers/transport.py), seule juge à l'enregistrement.
 */

export interface EntryPointOption {
  code: string;
  name: string;
  type: string;
  city?: string;
}

// Catégories de points d'entrée admises par moyen de transport ; « Autre » : sans restriction.
export const ENTRY_TYPES_BY_TRANSPORT: Record<string, readonly string[]> = {
  plane: ['airport'],
  boat: ['seaport', 'river'],
  car: ['land'],
  bus: ['land'],
  foot: ['land'],
  train: ['rail'],
};

// Pour le message « aucun point compatible ».
const ENTRY_KIND_BY_TRANSPORT: Record<string, string> = {
  plane: 'aéroport',
  boat: 'port maritime ou fluvial',
  car: 'poste-frontière terrestre',
  bus: 'poste-frontière terrestre',
  foot: 'poste-frontière terrestre',
  train: "point d'entrée ferroviaire",
};

/** Points compatibles avec le transport choisi ; aucun tant que le transport n'est pas choisi. */
export function compatibleEntryPoints<T extends { type: string }>(points: T[], transport: string): T[] {
  if (!transport) return [];
  const allowed = ENTRY_TYPES_BY_TRANSPORT[transport];
  return allowed ? points.filter((p) => allowed.includes(p.type)) : points;
}

/** Point déjà choisi, conservé seulement s'il reste proposé pour ce transport. */
export function keptEntryPoint(code: string, options: { code: string }[]): string {
  return options.some((p) => p.code === code) ? code : '';
}

export function noCompatibleEntryPointMessage(transport: string): string {
  const kind = ENTRY_KIND_BY_TRANSPORT[transport] ?? "point d'entrée";
  return `Aucun ${kind} n'est actuellement ouvert pour ce moyen de transport. `
    + 'Vérifiez le moyen de transport choisi, ou appelez Allô Santé au 143.';
}
