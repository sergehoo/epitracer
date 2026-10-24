/**
 * Photographies de la page d'accueil — prises en Côte d'Ivoire, licence Unsplash
 * (usage gratuit, attribution affichée en pied de page par courtoisie).
 * Lieu vérifié dans les métadonnées de chaque photo. Servies via l'optimiseur
 * Next/Image : les visiteurs ne contactent pas Unsplash directement.
 * À remplacer par des photos du MSHPCMU / INHP dès qu'elles sont disponibles.
 */
export const LANDING_PHOTOS = [
  {
    key: 'hero',
    src: 'https://images.unsplash.com/photo-1601221656510-e23d747fec7c?auto=format&fit=crop&w=2000&q=80',
    width: 2000,
    height: 1500,
    credit: 'Abubakar Balogun',
    place: 'Yamoussoukro',
    page: 'https://unsplash.com/photos/inyplWQ_P-8',
  },
  {
    key: 'panorama',
    src: 'https://images.unsplash.com/photo-1785095617583-e408f4b451ca?auto=format&fit=crop&w=2400&q=80',
    width: 2400,
    height: 1600,
    credit: 'Shane Ryan Herilalaina',
    place: 'Abidjan, Plateau',
    page: 'https://unsplash.com/photos/ir5PK5Itae0',
  },
] as const;

export const heroPhoto = LANDING_PHOTOS[0];
export const panoramaPhoto = LANDING_PHOTOS[1];
