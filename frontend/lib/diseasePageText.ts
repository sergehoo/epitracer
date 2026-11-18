/**
 * Libellés de la fiche maladie publique (/maladies/[slug]) en FR et EN.
 * Module sans 'use client' : utilisable par la page serveur, la page d'erreur et les tests.
 * Les contenus médicaux viennent de l'API (`?lang=en`), jamais de ce fichier.
 */

export type DiseaseLocale = 'fr' | 'en';

/** Cookie posé par le sélecteur FR/EN du portail (lib/i18n.tsx). */
export const LANG_COOKIE = 'epi_lang';

export function diseaseLocale(cookieValue?: string | null): DiseaseLocale {
  return cookieValue === 'en' ? 'en' : 'fr';
}

export const DISEASE_TEXT = {
  fr: {
    home: 'Accueil',
    breadcrumb: "Fil d'Ariane",
    diseases: 'Maladies sous surveillance',
    underSurveillance: 'Sous surveillance',
    generalInfo: 'Information générale',
    incubation: 'Incubation',
    incubationDays: (min: number, max: number) => `${min} à ${max} jours`,
    transmission: 'Transmission',
    followup: 'Suivi des voyageurs',
    followupDays: (days: number) => `${days} jours si nécessaire`,
    noFollowup: 'Pas de suivi en cours',
    notices: 'Alertes et recommandations',
    symptoms: 'Symptômes',
    redFlag: "Signe d'alerte",
    prevention: 'Prévention',
    recommendations: 'Recommandations aux voyageurs',
    help: "Besoin d'aide ?",
    helpText: 'Allô Santé 143 (gratuit) · SAMU 185. Signalez toujours votre voyage au personnel de santé.',
    call: 'Appeler le 143',
    prepare: 'Préparer mon arrivée',
    all: 'Toutes les maladies',
    published: (date: string) => `Fiche validée et publiée par les autorités sanitaires le ${date}`,
    updated: (date: string) => ` · mise à jour le ${date}`,
    untranslated: '',
    metaTitle: (name: string) => `${name} — symptômes, prévention et conseils aux voyageurs`,
    metaFallback: 'Maladies sous surveillance',
    notFound: 'Fiche introuvable',
    dateLocale: 'fr-FR',
    ogLocale: 'fr_FR',
    // Page d'erreur
    errorTitle: 'Fiche momentanément indisponible',
    errorText: "Le service d'information sanitaire ne répond pas pour le moment. Réessayez dans quelques instants.",
    errorHelp: 'En cas de symptômes ou de doute : Allô Santé 143 (gratuit) · SAMU 185.',
    retry: 'Réessayer',
    allSheets: 'Toutes les fiches',
    reference: 'Référence technique',
  },
  en: {
    home: 'Home',
    breadcrumb: 'Breadcrumb',
    diseases: 'Diseases under surveillance',
    underSurveillance: 'Under surveillance',
    generalInfo: 'General information',
    incubation: 'Incubation',
    incubationDays: (min: number, max: number) => `${min} to ${max} days`,
    transmission: 'Transmission',
    followup: 'Traveller follow-up',
    followupDays: (days: number) => `${days} days if needed`,
    noFollowup: 'No follow-up in progress',
    notices: 'Alerts and recommendations',
    symptoms: 'Symptoms',
    redFlag: 'Warning sign',
    prevention: 'Prevention',
    recommendations: 'Advice for travellers',
    help: 'Need help?',
    helpText: 'Allô Santé 143 (toll-free) · SAMU 185. Always tell health workers about your trip.',
    call: 'Call 143',
    prepare: 'Prepare my arrival',
    all: 'All diseases',
    published: (date: string) => `Fact sheet approved and published by the health authorities on ${date}`,
    updated: (date: string) => ` · updated on ${date}`,
    untranslated: 'Some parts of this fact sheet are not yet available in English and are shown in French.',
    metaTitle: (name: string) => `${name} — symptoms, prevention and advice for travellers`,
    metaFallback: 'Diseases under surveillance',
    notFound: 'Fact sheet not found',
    dateLocale: 'en-GB',
    ogLocale: 'en_GB',
    errorTitle: 'Fact sheet temporarily unavailable',
    errorText: 'The health information service is not responding right now. Please try again in a moment.',
    errorHelp: 'If you have symptoms or any doubt: Allô Santé 143 (toll-free) · SAMU 185.',
    retry: 'Try again',
    allSheets: 'All fact sheets',
    reference: 'Technical reference',
  },
} as const;

export function formatDiseaseDate(iso: string | null, locale: DiseaseLocale): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(DISEASE_TEXT[locale].dateLocale, {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Africa/Abidjan',
  });
}
