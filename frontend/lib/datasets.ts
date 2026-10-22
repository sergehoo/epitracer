/** Datasets utilisés par les sélecteurs publics. */
import type { CountryLite, EntryPointLite } from '@/types/ebola';

export const ENTRY_POINTS: EntryPointLite[] = [
  { id: 1, code: 'ABJ-AIRPORT', name: 'Aéroport International Félix-Houphouët-Boigny', type: 'airport', city: 'Abidjan', iata_code: 'ABJ' },
  { id: 2, code: 'ABJ-PORT', name: "Port Autonome d'Abidjan", type: 'seaport', city: 'Abidjan', iata_code: '' },
  { id: 3, code: 'SAN-PORT', name: 'Port de San-Pédro', type: 'seaport', city: 'San-Pédro', iata_code: '' },
  { id: 4, code: 'PGA-LAND', name: 'Frontière de Pôgô (CI/Mali)', type: 'land', city: 'Pôgô', iata_code: '' },
  { id: 5, code: 'NDA-LAND', name: 'Frontière de Niablé (CI/Ghana)', type: 'land', city: 'Niablé', iata_code: '' },
  { id: 6, code: 'AKJ-AIRPORT', name: 'Aéroport de Yamoussoukro', type: 'airport', city: 'Yamoussoukro', iata_code: 'ASK' },
];

// Codes ISO 3166-1 alpha-2, alignés sur le référentiel backend (apps/geo/referential.py).
// Aucun niveau de risque ici : il est défini côté serveur à partir des alertes validées.
export const COUNTRIES: CountryLite[] = [
  // Sous-région ouest-africaine
  { code: 'CI', name: "Côte d'Ivoire" },
  { code: 'GH', name: 'Ghana' },
  { code: 'TG', name: 'Togo' },
  { code: 'BJ', name: 'Bénin' },
  { code: 'BF', name: 'Burkina Faso' },
  { code: 'ML', name: 'Mali' },
  { code: 'NE', name: 'Niger' },
  { code: 'NG', name: 'Nigeria' },
  { code: 'GN', name: 'Guinée' },
  { code: 'GW', name: 'Guinée-Bissau' },
  { code: 'LR', name: 'Liberia' },
  { code: 'SL', name: 'Sierra Leone' },
  { code: 'SN', name: 'Sénégal' },
  { code: 'GM', name: 'Gambie' },
  { code: 'CV', name: 'Cap-Vert' },
  { code: 'MR', name: 'Mauritanie' },
  // Autres pays
  { code: 'CD', name: 'République démocratique du Congo' },
  { code: 'CG', name: 'République du Congo' },
  { code: 'UG', name: 'Ouganda' },
  { code: 'CM', name: 'Cameroun' },
  { code: 'GA', name: 'Gabon' },
  { code: 'CF', name: 'République centrafricaine' },
  { code: 'KE', name: 'Kenya' },
  { code: 'ZA', name: 'Afrique du Sud' },
  { code: 'EG', name: 'Égypte' },
  { code: 'MA', name: 'Maroc' },
  { code: 'TN', name: 'Tunisie' },
  { code: 'FR', name: 'France' },
  { code: 'BE', name: 'Belgique' },
  { code: 'DE', name: 'Allemagne' },
  { code: 'CH', name: 'Suisse' },
  { code: 'GB', name: 'Royaume-Uni' },
  { code: 'ES', name: 'Espagne' },
  { code: 'IT', name: 'Italie' },
  { code: 'PT', name: 'Portugal' },
  { code: 'US', name: 'États-Unis' },
  { code: 'CA', name: 'Canada' },
  { code: 'BR', name: 'Brésil' },
  { code: 'CN', name: 'Chine' },
  { code: 'IN', name: 'Inde' },
  { code: 'TR', name: 'Turquie' },
  { code: 'AE', name: 'Émirats arabes unis' },
  { code: 'SA', name: 'Arabie saoudite' },
  { code: 'LB', name: 'Liban' },
];
