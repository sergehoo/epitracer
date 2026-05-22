/**
 * Schémas Zod alignés strictement sur la fiche INHP officielle.
 * 7 sections, validations spécifiques par champ.
 */
import { z } from 'zod';

const phoneRegex = /^[+\d][\d\s().-]{6,}$/;

export const voyageSchema = z.object({
  arrival_date: z.string().min(1, 'Date d\'arrivée obligatoire.'),
  arrival_time: z.string().optional(),
  transport_mode: z.enum(['plane', 'boat', 'car', 'bus', 'train', 'foot', 'other'], {
    errorMap: () => ({ message: 'Sélectionnez un moyen de transport.' }),
  }),
  flight_or_voyage_number: z.string().min(1, 'N° de vol / moyen de transport obligatoire.'),
  // Le numéro de siège est OBLIGATOIRE pour permettre la traçabilité des
  // contacts à proximité dans l'avion / bateau / bus.
  seat_number: z.string().min(1, 'N° de siège obligatoire (utilisé pour le contact-tracing).'),
  entry_point_code: z.string().min(1, 'Point d\'entrée obligatoire.'),
});

export const identiteSchema = z.object({
  last_name: z.string().min(2, 'Nom obligatoire.'),
  first_name: z.string().min(2, 'Prénoms obligatoires.'),
  middle_name: z.string().optional().default(''),
  age: z.coerce.number().int().min(0, 'Âge invalide.').max(130, 'Âge invalide.'),
  age_unit: z.enum(['years', 'months']).default('years'),
  date_of_birth: z.string().optional().default(''),
  gender: z.enum(['M', 'F'], { errorMap: () => ({ message: 'Sélectionnez le sexe.' }) }),
  profession: z.string().min(1, 'Profession obligatoire.'),
  id_document_type: z.enum(['passport', 'cni', 'driver_license', 'residence', 'other']).default('passport'),
  id_document_number: z.string().min(3, 'N° passeport obligatoire.'),
  id_document_country_code: z.string().optional().default(''),
  nationality_code: z.string().optional().default(''),
  phone_mobile: z.string().regex(phoneRegex, 'Numéro de téléphone invalide.'),
  email: z.string().email('Email invalide.').optional().or(z.literal('')),
  postal_address: z.string().optional().default(''),
});

export const historyItemSchema = z.object({
  role: z.enum(['origin', 'transit', 'visited']),
  country_code: z.string().min(2, 'Pays obligatoire.'),
  // Ville et province deviennent obligatoires (sauf pour transit, où seule
  // la ville est exigée — voir validation côté composant Step3).
  city: z.string().min(1, 'Ville obligatoire.'),
  province: z.string().optional().default(''),
  residence_address: z.string().optional().default(''),
  hotel: z.string().optional().default(''),
  room_number: z.string().optional().default(''),
  arrival_date: z.string().optional().nullable().default(null),
  departure_date: z.string().optional().nullable().default(null),
  duration_text: z.string().optional().default(''),
});

export const historiqueSchema = z.array(historyItemSchema).default([]);

export const confinementSchema = z.object({
  city: z.string().min(1, 'Ville obligatoire.'),
  commune: z.string().min(1, 'Commune obligatoire.'),
  neighborhood: z.string().min(1, 'Quartier obligatoire.'),
  street_number: z.string().optional().default(''),
  lot: z.string().optional().default(''),
  hotel: z.string().optional().default(''),
  room_number: z.string().optional().default(''),
  // Téléphone d'urgence en Côte d'Ivoire — désormais OPTIONNEL (le contact
  // principal passe par WhatsApp). On accepte une chaîne vide ou un format
  // téléphonique valide ; pas de regex sans permissive si vide.
  emergency_phone_ci: z.string()
    .optional()
    .default('')
    .refine(
      (v) => !v || phoneRegex.test(v),
      { message: 'Numéro de téléphone invalide.' },
    ),
  // Numéro WhatsApp international (format E.164 : +XXXNNNNNNN). Doit
  // commencer par + et contenir au moins 8 chiffres au total. Obligatoire
  // car c'est désormais le canal de contact principal.
  whatsapp_phone: z.string().regex(/^\+\d{8,15}$/, 'Numéro WhatsApp international obligatoire.'),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
});

export const exposureSchema = z.object({
  visited_ebola_zone: z.boolean().default(false),
  visited_ebola_zone_details: z.string().optional().default(''),
  contact_with_case: z.boolean().default(false),
  attended_funeral_or_touched_corpse: z.boolean().default(false),
  visited_ebola_healthcare_facility: z.boolean().default(false),
}).refine(
  (v) => !v.visited_ebola_zone || (v.visited_ebola_zone_details && v.visited_ebola_zone_details.length > 1),
  { path: ['visited_ebola_zone_details'], message: 'Précisez la ville/région et le pays.' },
);

export const symptomsSchema = z.object({
  fever: z.boolean().default(false),
  intense_fatigue: z.boolean().default(false),
  muscle_joint_pain: z.boolean().default(false),
  severe_headache: z.boolean().default(false),
  sore_throat_or_abdominal: z.boolean().default(false),
  diarrhea_nausea_vomiting: z.boolean().default(false),
  unexplained_bleeding: z.boolean().default(false),
  temperature_celsius: z.coerce.number().min(30).max(45).optional(),
  other_symptoms: z.string().optional().default(''),
});

export const declarationSchema = z.object({
  signed_place: z.string().min(1, 'Indiquez la ville où vous remplissez la fiche.'),
  declared_at: z.string().min(1, 'Date obligatoire.'),
  declarant_full_name: z.string().min(2, 'Nom complet obligatoire.'),
  truthful_declaration: z.literal(true, {
    errorMap: () => ({ message: 'Vous devez certifier l\'exactitude des renseignements.' }),
  }),
  signature_data_url: z.string().min(20, 'Signature obligatoire.'),
});

export type VoyageInput = z.infer<typeof voyageSchema>;
export type IdentiteInput = z.infer<typeof identiteSchema>;
export type HistoryItemInput = z.infer<typeof historyItemSchema>;
export type ConfinementInput = z.infer<typeof confinementSchema>;
export type ExposureInput = z.infer<typeof exposureSchema>;
export type SymptomsInput = z.infer<typeof symptomsSchema>;
export type DeclarationInput = z.infer<typeof declarationSchema>;
