/**
 * Photographies de la page d'accueil — prises en Côte d'Ivoire, licence Unsplash
 * (usage gratuit, attribution affichée en pied de page par courtoisie).
 * Lieu vérifié dans les métadonnées de chaque photo.
 *
 * Fichiers LOCAUX (public/images/landing) importés statiquement : optimisés au
 * build (formats modernes, flou de chargement) et servis par le site lui-même,
 * sans dépendre d'un domaine distant autorisé ni d'un accès réseau sortant du
 * serveur. À remplacer par des photos du MSHPCMU / INHP dès qu'elles existent.
 */
import abidjanPlateau from '@/public/images/landing/abidjan-plateau.jpg';
import yamoussoukroBasilique from '@/public/images/landing/yamoussoukro-basilique.jpg';

export const LANDING_PHOTOS = [
  {
    key: 'hero',
    src: yamoussoukroBasilique,
    credit: 'Abubakar Balogun',
    place: 'Yamoussoukro',
    page: 'https://unsplash.com/photos/inyplWQ_P-8',
  },
  {
    key: 'panorama',
    src: abidjanPlateau,
    credit: 'Shane Ryan Herilalaina',
    place: 'Abidjan, Plateau',
    page: 'https://unsplash.com/photos/ir5PK5Itae0',
  },
] as const;

export const heroPhoto = LANDING_PHOTOS[0];
export const panoramaPhoto = LANDING_PHOTOS[1];
