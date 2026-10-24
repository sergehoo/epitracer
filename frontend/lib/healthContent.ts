/**
 * Regroupe les contenus sanitaires PUBLIÉS (fiches maladies, avis) pour les
 * sections de l'accueil.
 *
 * Aucun texte médical n'est produit ici : chaque conseil est repris mot pour
 * mot des fiches validées, avec la ou les maladies qui le portent. Seul son
 * classement par thème est déduit, par mots-clés FR/EN ; un conseil sans thème
 * reconnu va dans « maladies transmissibles », jamais à la corbeille.
 */
import type { PublicDisease, PublicDiseaseDetail, PublicNotice } from '@/types/portal';

export type PreventionTheme = 'hands' | 'contact' | 'mosquitoes' | 'foodWater' | 'vaccination';

export const PREVENTION_THEMES: PreventionTheme[] = ['hands', 'contact', 'mosquitoes', 'foodWater', 'vaccination'];

/** Conseil publié (dédoublonné) et maladies sources. */
export interface SourcedAdvice {
  text: string;
  sources: { slug: string; name: string }[];
}

export interface WatchedSymptom {
  label: string;
  /** Signe d'alerte d'au moins une fiche (is_red_flag). */
  redFlag: boolean;
  sources: string[];
}

const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

// Ordre = priorité : « Lavez-vous les mains à l'eau et au savon » relève des
// mains, pas de l'eau ; « contact » est le thème par défaut.
const THEME_PATTERNS: [PreventionTheme, RegExp][] = [
  ['vaccination', /vaccin|immunis|immuniz/],
  ['mosquitoes', /moustique|repulsif|insecte|piqure|mosquito|repellent|insect|bed ?nets?\b/],
  ['hands', /\bmains?\b|savon|hydroalcool|\bhands?\b|soap|saniti[sz]er/],
  ['foodWater', /\beaux?\b|boisson|aliment|nourriture|viande|cuit|\bcrus?\b|fruit|legume|water|drink|food|meat|cook|\braw\b|vegetable/],
];

// Recommandations voyageurs qui relèvent de la conduite à tenir face aux symptômes.
const SYMPTOM_ADVICE = /symptom|fievre|temperature|saign|malaise|fever|bleed|unwell/;

function collect(details: PublicDiseaseDetail[], pick: (d: PublicDiseaseDetail) => string[]): SourcedAdvice[] {
  const byText = new Map<string, SourcedAdvice>();
  for (const d of details) {
    for (const raw of pick(d)) {
      const text = raw.trim();
      if (!text) continue;
      const key = norm(text);
      const entry = byText.get(key) ?? { text, sources: [] };
      if (!entry.sources.some((s) => s.slug === d.slug)) {
        entry.sources.push({ slug: d.slug, name: d.short_name || d.name });
      }
      byText.set(key, entry);
    }
  }
  return [...byText.values()];
}

export function preventionByTheme(details: PublicDiseaseDetail[]): Record<PreventionTheme, SourcedAdvice[]> {
  const out: Record<PreventionTheme, SourcedAdvice[]> = {
    hands: [], contact: [], mosquitoes: [], foodWater: [], vaccination: [],
  };
  for (const advice of collect(details, (d) => d.prevention)) {
    const text = norm(advice.text);
    const theme = THEME_PATTERNS.find(([, re]) => re.test(text))?.[0] ?? 'contact';
    out[theme].push(advice);
  }
  return out;
}

/** Recommandations voyageurs : conduite face aux symptômes / séjour. */
export function travelerAdvice(details: PublicDiseaseDetail[]) {
  const all = collect(details, (d) => d.traveler_recommendations);
  return {
    symptoms: all.filter((a) => SYMPTOM_ADVICE.test(norm(a.text))),
    stay: all.filter((a) => !SYMPTOM_ADVICE.test(norm(a.text))),
  };
}

/** Signes à surveiller des maladies publiées : signes d'alerte d'abord. */
export function watchedSymptoms(details: PublicDiseaseDetail[]): WatchedSymptom[] {
  const byLabel = new Map<string, WatchedSymptom>();
  for (const d of details) {
    for (const s of d.symptoms) {
      const key = norm(s.label.trim());
      if (!key) continue;
      const entry = byLabel.get(key) ?? { label: s.label.trim(), redFlag: false, sources: [] };
      entry.redFlag ||= s.is_red_flag;
      const name = d.short_name || d.name;
      if (!entry.sources.includes(name)) entry.sources.push(name);
      byLabel.set(key, entry);
    }
  }
  return [...byLabel.values()].sort(
    (a, b) => Number(b.redFlag) - Number(a.redFlag) || b.sources.length - a.sources.length
      || a.label.localeCompare(b.label, 'fr'),
  );
}

/** Durées de suivi prévues par les protocoles des maladies sous surveillance. */
export function followupDurations(diseases: PublicDisease[]) {
  return diseases
    .filter((d) => d.under_surveillance && d.followup_days > 0)
    .map((d) => ({ slug: d.slug, name: d.short_name || d.name, days: d.followup_days }));
}

/** Date de la publication ou mise à jour la plus récente (fiches et avis). */
export function lastUpdate(diseases: PublicDisease[], notices: PublicNotice[]): string | null {
  const dates = [
    ...diseases.flatMap((d) => [d.updated_at, d.published_at]),
    ...notices.map((n) => n.published_at),
  ].filter((d): d is string => !!d && !Number.isNaN(Date.parse(d)));
  if (!dates.length) return null;
  return dates.reduce((a, b) => (Date.parse(a) >= Date.parse(b) ? a : b));
}

/** Date lisible ; fuseau fixe (Abidjan, UTC) pour un rendu serveur/client identique. */
export function formatDate(iso: string, locale: 'fr' | 'en'): string {
  return new Date(iso).toLocaleDateString(locale === 'en' ? 'en-GB' : 'fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Africa/Abidjan',
  });
}
