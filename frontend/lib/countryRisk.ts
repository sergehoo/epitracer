/** Niveaux de risque sanitaire des pays (référentiel geo, API /geo/country-risks/). */

export type CountryRiskLevel = 'normal' | 'moderate' | 'high' | 'critical';

export const COUNTRY_RISK_OPTIONS: { value: CountryRiskLevel; label: string }[] = [
  { value: 'normal',   label: 'Normal' },
  { value: 'moderate', label: 'Modéré' },
  { value: 'high',     label: 'Élevé' },
  { value: 'critical', label: 'Critique' },
];

export const COUNTRY_RISK_LABEL: Record<string, string> = Object.fromEntries(
  COUNTRY_RISK_OPTIONS.map((o) => [o.value, o.label]),
);

export const COUNTRY_RISK_BADGE: Record<string, string> = {
  normal: 'badge-low',
  moderate: 'badge-moderate',
  high: 'badge-high',
  critical: 'badge-critical',
};
