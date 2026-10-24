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
import santeAeroport from '@/public/images/landing/sante/aeroport.jpg';
import santeAlimentation from '@/public/images/landing/sante/alimentation.jpg';
import santeMains from '@/public/images/landing/sante/mains.jpg';
import santeMoustiques from '@/public/images/landing/sante/moustiques.jpg';
import santeThermometre from '@/public/images/landing/sante/thermometre.jpg';
import santeTransmissibles from '@/public/images/landing/sante/transmissibles.jpg';
import santeVaccination from '@/public/images/landing/sante/vaccination.jpg';

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

/**
 * Photographies des sections sanitaires — Wikimedia Commons, licences libres
 * vérifiées (API Commons) le 24/10/2026. Recadrées pour qu'aucun visage
 * n'apparaisse, redimensionnées et débarrassées de leurs métadonnées EXIF.
 * Crédit et licence affichés en pied de page (obligatoires pour CC BY / BY-SA).
 */
const CC_BY_SA_4 = { license: 'CC BY-SA 4.0', licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0/' };
const CC_BY_2 = { license: 'CC BY 2.0', licenseUrl: 'https://creativecommons.org/licenses/by/2.0/' };
const COMMONS = 'https://commons.wikimedia.org/wiki/File:';

export const HEALTH_PHOTOS = {
  hands: {
    src: santeMains, credit: 'Wabyona Bingi', ...CC_BY_SA_4,
    page: `${COMMONS}Use_of_a_touchless_hand_washing_tap_and_solid_bar_soap_dispenser.jpg`,
  },
  contact: {
    src: santeTransmissibles, credit: 'Rc1959', license: 'CC0',
    licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
    page: `${COMMONS}Alcohol-based_hand_sanitizer_in_a_French_train.jpg`,
  },
  mosquitoes: {
    src: santeMoustiques, credit: 'Tjeerd Wiersma', ...CC_BY_2,
    page: `${COMMONS}Mosquito_Netting.jpg`,
  },
  foodWater: {
    src: santeAlimentation, credit: 'Palmolley', ...CC_BY_SA_4,
    page: `${COMMONS}Fruits_et_l%C3%A9gumes_sur_un_%C3%A9tal_02.jpg`,
  },
  vaccination: {
    src: santeVaccination, credit: 'Ümit Kartoğlu / VOA', license: '', licenseUrl: '', // domaine public
    page: `${COMMONS}BioFarma_vaccine_vials_Bandung.jpg`,
  },
  airport: {
    src: santeAeroport, credit: 'Fawaz.tairou', ...CC_BY_SA_4,
    page: `${COMMONS}A%C3%A9roport_International_F%C3%A9lix_HOUPHOUET-BOIGNY.jpg`,
  },
  thermometer: {
    src: santeThermometre, credit: 'ajay_suresh', ...CC_BY_2,
    page: `${COMMONS}Digital_Thermometer_(51825721879).jpg`,
  },
} as const;
