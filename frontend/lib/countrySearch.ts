/**
 * Recherche de pays pour le Combobox, sur le référentiel local ISO 3166-1
 * (lib/datasets.ts COUNTRIES) : aucun appel réseau pendant la saisie.
 * Insensible aux accents, à la casse et à la ponctuation ; noms français et
 * anglais, code ISO alpha-2 et quelques appellations usuelles.
 */

export interface CountryOption {
  code: string;      // ISO 3166-1 alpha-2 (valeur enregistrée)
  name: string;      // nom français du référentiel
  label: string;     // libellé affiché dans la langue courante
  keys: string[];    // textes normalisés sur lesquels porte la recherche
  obsolete: boolean; // code retiré d'ISO : affiché s'il est déjà enregistré, jamais proposé
}

// Codes retirés d'ISO 3166-1, gardés au référentiel pour les données existantes.
const OBSOLETE = new Set(['AN']);

// Appellations courantes absentes des noms officiels FR/EN.
const ALIASES: Record<string, string> = {
  AE: 'EAU UAE Dubai',
  CD: 'RDC Congo Kinshasa Zaire',
  CF: 'RCA Centrafrique',
  CG: 'Congo Brazzaville',
  CI: 'Ivory Coast',
  GB: 'UK Angleterre Grande-Bretagne',
  NL: 'Hollande',
  US: 'USA Amerique',
};

export function normalizeSearch(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function englishNames(): (code: string) => string {
  try {
    const names = new Intl.DisplayNames(['en'], { type: 'region' });
    return (code) => {
      const name = names.of(code);
      return name && name !== code ? name : '';
    };
  } catch {
    return () => '';
  }
}

/** Options triées par libellé dans la langue courante (français par défaut). */
export function buildCountryOptions(
  countries: { code: string; name: string }[],
  locale: 'fr' | 'en' = 'fr',
): CountryOption[] {
  const english = englishNames();
  return countries
    .map(({ code, name }) => {
      const en = english(code);
      return {
        code,
        name,
        label: locale === 'en' && en ? en : name,
        keys: [name, en, ALIASES[code] ?? ''].filter(Boolean).map(normalizeSearch),
        obsolete: OBSOLETE.has(code),
      };
    })
    .sort((a, b) => a.label.localeCompare(b.label, locale));
}

// 0 : code ISO exact · 1 : début du nom · 2 : début d'un mot · 3 : ailleurs dans le nom.
function rank(option: CountryOption, query: string): number {
  if (option.code.toLowerCase() === query) return 0;
  let best = Infinity;
  for (const key of option.keys) {
    if (key.startsWith(query)) return 1;
    if (` ${key}`.includes(` ${query}`)) best = Math.min(best, 2);
    else if (key.includes(query)) best = Math.min(best, 3);
  }
  return best;
}

/** Pays proposés pour la saisie, du plus pertinent au moins pertinent ; tous si la saisie est vide. */
export function searchCountries(options: CountryOption[], query: string): CountryOption[] {
  const pool = options.filter((o) => !o.obsolete);
  const q = normalizeSearch(query);
  if (!q) return pool;
  return pool
    .map((option) => ({ option, score: rank(option, q) }))
    .filter(({ score }) => score !== Infinity)
    .sort((a, b) => a.score - b.score)
    .map(({ option }) => option);
}

/** Pays dont le nom (FR/EN), l'alias ou le code correspond exactement à la saisie. */
export function findExactCountry(options: CountryOption[], query: string): CountryOption | undefined {
  const q = normalizeSearch(query);
  if (!q) return undefined;
  return options.find((o) => !o.obsolete && (o.code.toLowerCase() === q || o.keys.includes(q)));
}
