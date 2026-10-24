'use client';

/**
 * Bascule FR/EN du portail public (en-tête, page d'accueil, pied de page).
 *
 * Sans dépendance : dictionnaires statiques + contexte React. Le rendu serveur
 * est en français (SEO, langue par défaut) ; la langue choisie est mémorisée
 * (localStorage + cookie `epi_lang`) et appliquée au premier rendu client.
 * Les formulaires et pages métier restent en français.
 */

import { usePathname } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export type Locale = 'fr' | 'en';
const STORAGE_KEY = 'epi.lang';

const fr = {
  skip: 'Aller au contenu',
  nav: {
    services: 'Services',
    diseases: 'Maladies sous surveillance',
    how: 'Comment ça marche',
    assistance: 'Assistance',
    faq: 'FAQ',
    pass: 'Consulter mon pass',
    register: "M'enregistrer",
    agent: 'Espace agent',
    menuOpen: 'Ouvrir le menu',
    menuClose: 'Fermer le menu',
    main: 'Navigation principale',
    language: 'Langue',
  },
  brand: {
    country: "République de Côte d'Ivoire",
    motto: 'Union · Discipline · Travail',
    tagline: 'Destination Côte d’Ivoire',
    institutions: 'MSHPCMU · INHP',
  },
  hero: {
    eyebrow: 'Akwaba — Bienvenue en Côte d’Ivoire',
    title: 'Voyagez serein, nous veillons sur votre santé.',
    subtitle:
      "Destination Côte d'Ivoire est le dispositif national d'information, de prévention et d'accompagnement sanitaire des voyageurs, porté par le MSHPCMU et l'INHP. Préparez votre arrivée en quelques minutes et recevez votre pass sanitaire numérique.",
    ctaPrimary: 'Préparer mon arrivée',
    ctaSecondary: 'Consulter mon pass',
    reassurance: ['Gratuit', 'Données protégées', 'Accessible sur mobile'],
    photoAlt: "Colonnade de la Basilique Notre-Dame de la Paix à Yamoussoukro, Côte d'Ivoire",
  },
  demo: {
    badge: 'Démonstration',
    title: 'Pass Voyageur CI',
    name: 'Voyageur Exemple',
    passLabel: 'N° de pass',
    statusLabel: 'Statut',
    status: 'Accompagné',
    qr: 'QR signé, vérifiable hors ligne',
    disclaimer: "Exemple fictif : ce n'est pas un pass valide.",
  },
  services: {
    title: 'Vos services en un clic',
    subtitle: 'Tout ce dont vous avez besoin avant, pendant et après votre arrivée.',
    items: [
      { title: 'Enregistrement', desc: 'Remplissez votre fiche voyageur en ligne, en quelques minutes.', cta: 'Commencer' },
      { title: 'Mon pass', desc: 'Retrouvez et téléchargez votre pass sanitaire QR à tout moment.', cta: 'Consulter' },
      { title: 'Suivi sanitaire', desc: 'Déclarez votre état de santé si un suivi a été ouvert pour vous.', cta: 'Accéder' },
      { title: 'Assistance', desc: 'Conseils, conduite à tenir et numéros d’urgence (143, 185).', cta: 'Être aidé' },
    ],
  },
  diseases: {
    eyebrow: 'Information sanitaire officielle',
    title: 'Maladies sous surveillance',
    subtitle:
      "Fiches validées et publiées par le MSHPCMU et l'INHP : symptômes, transmission, prévention et recommandations aux voyageurs.",
    alerts: 'Alertes sanitaires en cours',
    recommendations: 'Recommandations aux voyageurs',
    empty:
      "Les fiches d'information sont publiées par les autorités sanitaires au fil de la situation. En cas de doute ou de symptôme, appelez le",
    all: 'Toutes les fiches maladies',
    followup: 'Suivi des voyageurs',
    days: 'jours',
    notMonitored: 'Non surveillée',
    transmission: 'Transmission',
    open: 'Voir la fiche',
  },
  how: {
    eyebrow: 'Comment ça marche',
    title: 'Votre parcours en 3 étapes',
    steps: [
      { title: 'Je remplis ma fiche', desc: "Avant ou à l'arrivée : voyage, identité, hébergement et quelques questions de santé." },
      { title: 'Je reçois mon pass', desc: 'Un pass QR signé et une fiche officielle PDF, utilisables même hors ligne.' },
      { title: 'Je suis accompagné', desc: "Si votre situation le justifie, l'INHP vous accompagne pendant la durée prévue par le protocole." },
    ],
    cta: 'Commencer ma fiche',
  },
  ci: {
    eyebrow: 'Akwaba',
    title: "La Côte d'Ivoire vous accueille",
    text:
      "Terre d'hospitalité, la Côte d'Ivoire veille sur la santé de celles et ceux qui la visitent. Les équipes sanitaires des points d'entrée sont là pour vous informer, vous orienter et vous accompagner avec respect.",
    photoAlt: "Vue du Plateau d'Abidjan depuis la lagune Ébrié",
  },
  pwa: {
    eyebrow: 'Application mobile',
    title: "Destination Côte d'Ivoire dans votre poche",
    text: 'Installez le portail sur votre téléphone, comme une application : sans magasin d’applications et sans compte.',
    benefits: [
      'Votre pass QR accessible même sans connexion',
      'Rappels de suivi sur votre téléphone, si vous les acceptez',
      'Accès direct aux numéros d’urgence',
    ],
    install: "Installer l'application",
    installed: 'Application déjà installée sur cet appareil.',
    ios: "Sur iPhone : touchez « Partager » puis « Sur l'écran d'accueil ».",
    unsupported: "Sur ce navigateur, utilisez le menu « Installer » ou « Ajouter à l'écran d'accueil ».",
  },
  faq: {
    title: 'Questions fréquentes',
    subtitle: 'Les réponses aux interrogations les plus courantes des voyageurs.',
    items: [
      { q: 'Pourquoi me demande-t-on ces informations ?', a: "Ces informations permettent aux équipes sanitaires de mieux vous orienter, de vous donner des conseils adaptés aux maladies sous surveillance et de faciliter votre passage aux points d'entrée." },
      { q: 'Quelles maladies sont concernées ?', a: 'Uniquement les maladies placées sous surveillance par les autorités sanitaires ivoiriennes. La liste évolue selon la situation épidémiologique et est consultable à tout moment dans la rubrique « Maladies sous surveillance ».' },
      { q: 'Puis-je être suivi pour plusieurs maladies ?', a: 'Oui. Votre fiche est unique : si votre situation le justifie, un accompagnement est ouvert pour chaque maladie concernée, avec la durée prévue par son protocole, sans que vous ayez à vous réenregistrer.' },
      { q: 'Mes données sont-elles confidentielles ?', a: "Oui. Vos informations sont protégées (signature cryptographique Ed25519, accès strict RBAC) et utilisées uniquement dans le cadre de l'accompagnement sanitaire et de la protection de la santé publique." },
      { q: 'Que se passe-t-il si je ne me sens pas bien ?', a: 'Vous pouvez contacter les services sanitaires. Un agent vous orientera calmement vers la conduite à tenir et, si nécessaire, vers le centre de santé approprié.' },
      { q: 'Est-ce que cela va ralentir mon arrivée ?', a: 'Au contraire, le pré-enregistrement permet souvent de gagner du temps, car votre fiche est déjà prête et le QR code facilite votre orientation.' },
    ],
  },
  footer: {
    about: "Dispositif national d'information, de prévention et d'accompagnement sanitaire des voyageurs en Côte d'Ivoire.",
    travelers: 'Voyageurs',
    prepare: 'Préparer mon arrivée',
    pass: 'Consulter mon pass',
    followup: 'Mon suivi sanitaire',
    diseases: 'Maladies sous surveillance',
    help: 'Assistance',
    advice: 'Conseils sanitaires',
    emergency: "Numéros d'urgence",
    samu: 'SAMU national',
    health: 'Allô Santé',
    rescue: 'Police / Secours',
    institutional: 'Institutionnel',
    pro: 'Espace professionnel',
    legal: 'Informations légales',
    privacy: 'Politique de confidentialité',
    myData: 'Mes données personnelles',
    contact: 'Contact',
    rights: 'Tous droits réservés.',
    security: 'Données protégées · Signature cryptographique Ed25519',
    photos: 'Photos',
  },
};

type Dict = typeof fr;

const en: Dict = {
  skip: 'Skip to content',
  nav: {
    services: 'Services',
    diseases: 'Diseases under surveillance',
    how: 'How it works',
    assistance: 'Assistance',
    faq: 'FAQ',
    pass: 'View my pass',
    register: 'Register',
    agent: 'Staff area',
    menuOpen: 'Open menu',
    menuClose: 'Close menu',
    main: 'Main navigation',
    language: 'Language',
  },
  brand: {
    country: 'Republic of Côte d’Ivoire',
    motto: 'Union · Discipline · Work',
    tagline: 'Destination Côte d’Ivoire',
    institutions: 'MSHPCMU · INHP',
  },
  hero: {
    eyebrow: 'Akwaba — Welcome to Côte d’Ivoire',
    title: 'Travel with peace of mind, we look after your health.',
    subtitle:
      "Destination Côte d'Ivoire is the national health information, prevention and support service for travellers, run by the Ministry of Health (MSHPCMU) and the National Institute of Public Hygiene (INHP). Prepare your arrival in a few minutes and get your digital health pass.",
    ctaPrimary: 'Prepare my arrival',
    ctaSecondary: 'View my pass',
    reassurance: ['Free', 'Data protected', 'Mobile friendly'],
    photoAlt: 'Colonnade of the Basilica of Our Lady of Peace in Yamoussoukro, Côte d’Ivoire',
  },
  demo: {
    badge: 'Demonstration',
    title: 'CI Traveller Pass',
    name: 'Sample Traveller',
    passLabel: 'Pass no.',
    statusLabel: 'Status',
    status: 'Supported',
    qr: 'Signed QR, verifiable offline',
    disclaimer: 'Fictitious example: this is not a valid pass.',
  },
  services: {
    title: 'Your services in one click',
    subtitle: 'Everything you need before, during and after your arrival.',
    items: [
      { title: 'Registration', desc: 'Fill in your traveller form online in a few minutes.', cta: 'Start' },
      { title: 'My pass', desc: 'Find and download your QR health pass at any time.', cta: 'Open' },
      { title: 'Health follow-up', desc: 'Report how you feel if a follow-up has been opened for you.', cta: 'Access' },
      { title: 'Assistance', desc: 'Advice, what to do and emergency numbers (143, 185).', cta: 'Get help' },
    ],
  },
  diseases: {
    eyebrow: 'Official health information',
    title: 'Diseases under surveillance',
    subtitle:
      'Fact sheets validated and published by the MSHPCMU and INHP: symptoms, transmission, prevention and advice for travellers.',
    alerts: 'Current health alerts',
    recommendations: 'Advice for travellers',
    empty:
      'Fact sheets are published by the health authorities as the situation evolves. If in doubt or if you have symptoms, call',
    all: 'All disease fact sheets',
    followup: 'Traveller follow-up',
    days: 'days',
    notMonitored: 'Not under surveillance',
    transmission: 'Transmission',
    open: 'Read the fact sheet',
  },
  how: {
    eyebrow: 'How it works',
    title: 'Your journey in 3 steps',
    steps: [
      { title: 'I fill in my form', desc: 'Before or upon arrival: trip, identity, accommodation and a few health questions.' },
      { title: 'I receive my pass', desc: 'A signed QR pass and an official PDF form, usable even offline.' },
      { title: 'I am supported', desc: 'If your situation requires it, INHP supports you for the period set by the protocol.' },
    ],
    cta: 'Start my form',
  },
  ci: {
    eyebrow: 'Akwaba',
    title: 'Côte d’Ivoire welcomes you',
    text:
      'A land of hospitality, Côte d’Ivoire looks after the health of everyone who visits. Health teams at entry points are there to inform, guide and support you with respect.',
    photoAlt: 'View of the Plateau district of Abidjan from the Ébrié lagoon',
  },
  pwa: {
    eyebrow: 'Mobile app',
    title: "Destination Côte d'Ivoire in your pocket",
    text: 'Install the portal on your phone like an app: no app store and no account needed.',
    benefits: [
      'Your QR pass available even offline',
      'Follow-up reminders on your phone, if you accept them',
      'Direct access to emergency numbers',
    ],
    install: 'Install the app',
    installed: 'The app is already installed on this device.',
    ios: 'On iPhone: tap “Share”, then “Add to Home Screen”.',
    unsupported: 'In this browser, use the “Install” or “Add to Home screen” menu.',
  },
  faq: {
    title: 'Frequently asked questions',
    subtitle: 'Answers to the questions travellers ask most often.',
    items: [
      { q: 'Why am I asked for this information?', a: 'It allows health teams to guide you better, give advice suited to the diseases under surveillance and make your passage through entry points easier.' },
      { q: 'Which diseases are concerned?', a: 'Only the diseases placed under surveillance by the Ivorian health authorities. The list changes with the epidemiological situation and can be consulted at any time under “Diseases under surveillance”.' },
      { q: 'Can I be followed up for several diseases?', a: 'Yes. You have a single form: if your situation requires it, a follow-up is opened for each disease concerned, for the period set by its protocol, without registering again.' },
      { q: 'Is my data confidential?', a: 'Yes. Your information is protected (Ed25519 cryptographic signature, strict role-based access) and used only for health support and public health protection.' },
      { q: 'What if I feel unwell?', a: 'Contact the health services. An agent will calmly tell you what to do and, if needed, direct you to the appropriate health centre.' },
      { q: 'Will this slow down my arrival?', a: 'On the contrary, pre-registration often saves time: your form is ready and the QR code makes guidance easier.' },
    ],
  },
  footer: {
    about: 'National health information, prevention and support service for travellers in Côte d’Ivoire.',
    travelers: 'Travellers',
    prepare: 'Prepare my arrival',
    pass: 'View my pass',
    followup: 'My health follow-up',
    diseases: 'Diseases under surveillance',
    help: 'Assistance',
    advice: 'Health advice',
    emergency: 'Emergency numbers',
    samu: 'National SAMU',
    health: 'Allô Santé',
    rescue: 'Police / Rescue',
    institutional: 'Institutions',
    pro: 'Professional area',
    legal: 'Legal information',
    privacy: 'Privacy policy',
    myData: 'My personal data',
    contact: 'Contact',
    rights: 'All rights reserved.',
    security: 'Data protected · Ed25519 cryptographic signature',
    photos: 'Photos',
  },
};

const DICTS: Record<Locale, Dict> = { fr, en };

interface LocaleContextValue {
  locale: Locale;
  t: Dict;
  setLocale: (l: Locale) => void;
}

const LocaleContext = createContext<LocaleContextValue>({ locale: 'fr', t: fr, setLocale: () => undefined });

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('fr');

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === 'en' || saved === 'fr') setLocaleState(saved);
    } catch { /* stockage indisponible : français par défaut */ }
  }, []);

  // Seule l'accueil est entièrement traduite : ailleurs le corps de page reste
  // en français (<html lang="fr">) ; en-tête et pied portent leur propre `lang`.
  const pathname = usePathname();
  useEffect(() => {
    document.documentElement.lang = pathname === '/' ? locale : 'fr';
  }, [locale, pathname]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
      document.cookie = `epi_lang=${l}; path=/; max-age=31536000; samesite=lax`;
    } catch { /* préférence non mémorisée */ }
  }, []);

  const value = useMemo(() => ({ locale, t: DICTS[locale], setLocale }), [locale, setLocale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}
