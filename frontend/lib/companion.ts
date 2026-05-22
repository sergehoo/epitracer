/**
 * Client API du module Companion (PWA voyageur).
 *
 * Conventions :
 * - Tous les endpoints sont sous /public/ (préfixe API, sans auth JWT).
 * - On envoie systématiquement le `public_id` du voyageur dans le body.
 * - Les pings de localisation ne sont jamais envoyés sans consentement
 *   préalable côté serveur (qui re-vérifie).
 */

import { api } from '@/lib/api';

export type ConsentScope =
  | 'geolocation'
  | 'push'
  | 'health_followup'
  | 'data_processing';

export const CONSENT_VERSION = 'v1.0-2026-05';

export interface CheckEntry {
  check_date: string;
  day_index: number;
  has_symptoms: boolean;
  temperature_celsius: number | null;
  feeling: 'ok' | 'symptom' | 'assistance' | null;
  needs_contact?: boolean;
  positive_symptoms?: string[];
  notes?: string;
  alert_raised?: boolean;
}

export interface FollowUpStatus {
  traveler: { public_id: string; full_name: string };
  quarantine: {
    active: boolean;
    started_on: string | null;
    expected_end_on: string | null;
    day_index: number | null;
    total_days: number | null;
  };
  last_check: CheckEntry | null;
  checks?: CheckEntry[];
  consents: Record<ConsentScope, boolean>;
  assistance: { samu: string; allo_sante: string; secours: string };
}

export interface CheckinPayload {
  public_id: string;
  feeling: 'ok' | 'symptom' | 'assistance';
  symptoms?: Record<string, boolean>;
  temperature_celsius?: number | null;
  notes?: string;
  needs_contact?: boolean;
  latitude?: number | null;
  longitude?: number | null;
  accuracy_m?: number | null;
}

export interface CheckinResponse {
  ok: boolean;
  message: string;
  alert_created: boolean;
  alert_severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null;
  location_recorded: boolean;
}

export async function fetchFollowUpStatus(publicId: string) {
  const { data } = await api.get<FollowUpStatus>('/public/follow-up/status/', {
    params: { public_id: publicId },
  });
  return data;
}

export async function recordConsent(
  publicId: string,
  scope: ConsentScope,
  granted: boolean,
  textExcerpt = '',
  revocationReason = '',
) {
  const { data } = await api.post('/public/consent/', {
    public_id: publicId,
    scope,
    granted,
    consent_version: CONSENT_VERSION,
    text_excerpt: textExcerpt,
    revocation_reason: revocationReason,
  });
  return data;
}

export async function submitCheckin(payload: CheckinPayload) {
  const { data } = await api.post<CheckinResponse>('/public/checkin/', payload);
  return data;
}

export async function shareLocation(
  publicId: string,
  position: GeolocationPosition,
  eventType:
    | 'daily_checkin'
    | 'manual_share'
    | 'assistance_request'
    | 'symptom_report'
    | 'agent_visit' = 'manual_share',
) {
  const { data } = await api.post('/public/location/ping/', {
    public_id: publicId,
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy_m: position.coords.accuracy ?? undefined,
    altitude_m: position.coords.altitude ?? undefined,
    speed_mps: position.coords.speed ?? undefined,
    heading_deg: position.coords.heading ?? undefined,
    event_type: eventType,
    device_info: navigator.userAgent.slice(0, 200),
  });
  return data;
}

/**
 * Wrapper navigator.geolocation.getCurrentPosition qui retourne une
 * Promise et gère proprement tous les cas d'erreur (refus, GPS off,
 * timeout, navigateur non compatible). Ne demande la permission que si
 * elle n'a pas déjà été refusée.
 */
export function getCurrentPosition(
  options: PositionOptions = { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      reject(new Error('GEOLOCATION_UNSUPPORTED'));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, (err) => {
      if (err.code === err.PERMISSION_DENIED) reject(new Error('GEOLOCATION_DENIED'));
      else if (err.code === err.POSITION_UNAVAILABLE) reject(new Error('GEOLOCATION_UNAVAILABLE'));
      else if (err.code === err.TIMEOUT) reject(new Error('GEOLOCATION_TIMEOUT'));
      else reject(err);
    }, options);
  });
}

/**
 * Helper : essaie de récupérer la position si l'utilisateur a déjà
 * consenti (côté state local). Best-effort, ne lève jamais d'exception.
 * Retourne null si refusé ou indisponible.
 */
export async function tryGetPosition(): Promise<GeolocationPosition | null> {
  try {
    return await getCurrentPosition();
  } catch {
    return null;
  }
}
