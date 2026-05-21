/**
 * Types alignés sur la fiche INHP "FICHE PASSAGER EBOLA RDC 2026".
 */

export type Gender = 'M' | 'F';
export type AgeUnit = 'years' | 'months';
export type TransportMode = 'plane' | 'boat' | 'car' | 'bus' | 'train' | 'foot' | 'other';
export type RiskLevel = 'low' | 'moderate' | 'high' | 'critical';

/** Section 1 — Voyage
 *  Note typage : les champs "non encore sélectionnés" sont rendus optionnels
 *  (`?: T`) plutôt que `T | ''`, pour rester structurellement compatible
 *  avec les types Zod inférés et la signature `DefaultValues<>` de RHF.
 */
export interface SectionVoyage {
  arrival_date: string;           // YYYY-MM-DD
  arrival_time?: string;          // HH:MM
  transport_mode?: TransportMode;
  flight_or_voyage_number: string;
  seat_number?: string;
  entry_point_code: string;       // ex: ABJ-AIRPORT
}

/** Document de voyage (upload local côté front avant envoi) */
export interface PassportFile {
  file: File;
  preview?: string; // base64 ou URL temporaire
}

/** Section 2 — Identité & contacts */
export interface SectionIdentite {
  last_name: string;
  first_name: string;
  middle_name?: string;
  age?: number;
  age_unit: AgeUnit;
  date_of_birth?: string;
  gender?: Gender;
  profession: string;
  id_document_type: 'passport' | 'cni' | 'driver_license' | 'residence' | 'other';
  id_document_number: string;
  id_document_country_code?: string;
  nationality_code?: string;
  phone_mobile: string;
  email?: string;
  postal_address?: string;
}

/** Section 3 — Historique des déplacements (3 dernières semaines) */
export interface HistoryItem {
  role: 'origin' | 'transit' | 'visited';
  country_code: string;
  city?: string;
  residence_address?: string;
  hotel?: string;
  room_number?: string;
  arrival_date?: string | null;
  departure_date?: string | null;
  duration_text?: string;
}

/** Section 4 — Confinement en Côte d'Ivoire */
export interface SectionConfinement {
  city: string;
  commune: string;
  neighborhood: string;
  street_number?: string;
  lot?: string;
  hotel?: string;
  room_number?: string;
  emergency_phone_ci: string;
  latitude?: number;
  longitude?: number;
}

/** Section 5 — Évaluation épidémiologique du risque (21j) */
export interface SectionExposure {
  visited_ebola_zone: boolean;
  visited_ebola_zone_details?: string;
  contact_with_case: boolean;
  attended_funeral_or_touched_corpse: boolean;
  visited_ebola_healthcare_facility: boolean;
}

/** Section 6 — État de santé (48h) */
export interface SectionSymptoms {
  fever: boolean;
  intense_fatigue: boolean;
  muscle_joint_pain: boolean;
  severe_headache: boolean;
  sore_throat_or_abdominal: boolean;
  diarrhea_nausea_vomiting: boolean;
  unexplained_bleeding: boolean;
  temperature_celsius?: number;
  other_symptoms?: string;
}

/** Section 7 — Déclaration & signature */
export interface SectionDeclaration {
  signed_place: string;
  declared_at: string;            // ISO
  declarant_full_name: string;
  truthful_declaration: boolean;
  signature_data_url?: string;    // signature PNG base64
}

/** Soumission complète */
export interface FullSubmission {
  voyage: SectionVoyage;
  identite: SectionIdentite;
  historique: HistoryItem[];
  confinement: SectionConfinement;
  exposure: SectionExposure;
  symptoms: SectionSymptoms;
  declaration: SectionDeclaration;
}

/** Réponse API après enregistrement */
export interface RegistrationResponse {
  traveler: {
    public_id: string;
    uuid: string;
    full_name: string;
    current_health_status: string;
  };
  investigation: {
    case_number: string;
    risk_score: number;
    risk_level: RiskLevel;
    status: string;
  };
  pass: {
    pass_number: string;
    uuid: string;
    status: string;
    expires_at: string;
    qr_url: string | null;
    pdf_url: string | null;
    qr_token: string;
  };
  instructions: {
    surveillance_days: number;
    message: string;
    phones: {
      samu: string;
      allo_sante: string;
      secours: string;
      inhp_lines: string[];
    };
  };
}

export interface EntryPointLite {
  id: number;
  code: string;
  name: string;
  type: string;
  city: string;
  iata_code: string;
}

export interface CountryLite {
  code: string;
  name: string;
  risk_level?: string;
}
