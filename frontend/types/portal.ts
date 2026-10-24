/** Contenus publics du portail (API /api/v1/public/). */

export type PublicAlertLevel = 'normal' | 'moderate' | 'high' | 'critical';

export interface PublicDisease {
  slug: string;
  code: string;
  name: string;
  short_name: string;
  description: string;
  color: string;
  public_alert_level: PublicAlertLevel;
  alert_level_label: string;
  under_surveillance: boolean;
  transmission: string[];
  incubation_min_days: number;
  incubation_max_days: number;
  followup_days: number;
  published_at: string | null;
  updated_at: string;
}

export interface PublicNotice {
  uuid: string;
  kind: 'alert' | 'recommendation';
  title: string;
  summary: string;
  body: string;
  alert_level: PublicAlertLevel;
  alert_level_label: string;
  disease: { slug: string; name: string } | null;
  countries: { code: string; name: string }[];
  valid_from: string;
  valid_until: string | null;
  published_at: string | null;
}

export interface PublicDiseaseDetail extends PublicDisease {
  icd11_code: string;
  transmission_details: string;
  prevention: string[];
  traveler_recommendations: string[];
  symptoms: { label: string; is_red_flag: boolean }[];
  notices: PublicNotice[];
}

export interface ScreeningDisease {
  code: string;
  name: string;
  slug: string;
  /** Questions « contact avec un malade » : regroupées dans le tronc commun. */
  contact_exposures: { code: string; label: string }[];
  /** Questions propres à la maladie : posées selon l'itinéraire (ou toujours). */
  specific_exposures: { code: string; label: string }[];
  ask_specific_exposures: 'always' | 'if_risk_itinerary';
  /** Pays (ISO-2) où la maladie fait l'objet d'une surveillance renforcée. */
  risk_countries: string[];
  followup_days: number;
  daily_checkin: boolean;
}

export interface RegistrationConfig {
  ebola_questionnaire: boolean;
  /** Section symptômes commune → codes du référentiel (jamais reposés par maladie). */
  common_symptom_fields: Record<string, string[]>;
  /** Autres symptômes des maladies actives, dédoublonnés. */
  extra_symptoms: { code: string; label: string }[];
  diseases: ScreeningDisease[];
}

/** Réponses « oui » d'un voyageur pour une maladie (envoyées à l'enregistrement). */
export interface ScreeningAnswer {
  disease: string;
  exposures: string[];
}
