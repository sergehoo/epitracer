'use client';

/**
 * Questionnaire multimaladies (hors Ebola, qui garde sa section INHP) :
 *  - tronc commun : UNE question « contact avec un malade », précisée par
 *    maladie seulement si la réponse est oui ;
 *  - questions propres à une maladie : posées uniquement si l'itinéraire
 *    passe par un pays où elle fait l'objet d'une surveillance renforcée
 *    (ou toujours, si son protocole le prévoit).
 * Les symptômes sont demandés une seule fois, à l'étape « Santé ».
 */

import type { Dispatch, SetStateAction } from 'react';
import { YesNo } from '@/components/form/Field';
import { COUNTRIES } from '@/lib/datasets';
import type { ScreeningAnswer, ScreeningDisease } from '@/types/portal';

export interface ScreeningDraft {
  contactAny: boolean | null;
  contactDiseases: string[];
  specific: Record<string, Record<string, boolean | null>>;
}

const COUNTRY_NAME = new Map(COUNTRIES.map((c) => [c.code, c.name]));

/** Maladies dont les questions spécifiques s'appliquent à cet itinéraire. */
export function relevantSpecific(diseases: ScreeningDisease[], visited: string[]) {
  return diseases
    .filter((d) => d.specific_exposures.length > 0)
    .map((d) => ({ disease: d, countries: d.risk_countries.filter((c) => visited.includes(c)) }))
    .filter(({ disease, countries }) => disease.ask_specific_exposures === 'always' || countries.length > 0);
}

export function initialScreeningDraft(diseases: ScreeningDisease[], saved?: ScreeningAnswer[]): ScreeningDraft {
  const byCode = new Map((saved || []).map((s) => [s.disease, s.exposures]));
  const contactDiseases = diseases
    .filter((d) => d.contact_exposures.some((e) => byCode.get(d.code)?.includes(e.code)))
    .map((d) => d.code);
  return {
    contactAny: saved ? contactDiseases.length > 0 : null,
    contactDiseases,
    specific: Object.fromEntries(diseases.map((d) => [
      d.code,
      Object.fromEntries(d.specific_exposures.map((e) => [
        e.code, saved && byCode.has(d.code) ? byCode.get(d.code)!.includes(e.code) : null,
      ])),
    ])),
  };
}

/** Clés des questions sans réponse (pour la validation et le défilement). */
export function unansweredScreening(
  diseases: ScreeningDisease[], visited: string[], draft: ScreeningDraft,
): string[] {
  const missing: string[] = [];
  const hasContact = diseases.some((d) => d.contact_exposures.length > 0);
  if (hasContact && draft.contactAny == null) missing.push('screening:contact');
  if (draft.contactAny === true && draft.contactDiseases.length === 0) missing.push('screening:contact');
  for (const { disease } of relevantSpecific(diseases, visited)) {
    for (const e of disease.specific_exposures) {
      if (draft.specific[disease.code]?.[e.code] == null) missing.push(`${disease.code}:${e.code}`);
    }
  }
  return missing;
}

export function toScreeningAnswers(
  diseases: ScreeningDisease[], visited: string[], draft: ScreeningDraft,
): ScreeningAnswer[] {
  const asked = new Set(relevantSpecific(diseases, visited).map(({ disease }) => disease.code));
  return diseases.map((d) => ({
    disease: d.code,
    exposures: [
      ...(draft.contactAny && draft.contactDiseases.includes(d.code) ? d.contact_exposures.map((e) => e.code) : []),
      ...(asked.has(d.code)
        ? Object.entries(draft.specific[d.code] || {}).filter(([, v]) => v === true).map(([k]) => k)
        : []),
    ],
  }));
}

export function DiseaseScreenings({
  diseases, visited, draft, onChange, showErrors,
}: {
  diseases: ScreeningDisease[];
  visited: string[];
  draft: ScreeningDraft;
  /** Mises à jour fonctionnelles : deux réponses rapprochées ne s'écrasent pas. */
  onChange: Dispatch<SetStateAction<ScreeningDraft>>;
  showErrors: boolean;
}) {
  const contactDiseases = diseases.filter((d) => d.contact_exposures.length > 0);
  const specific = relevantSpecific(diseases, visited);
  if (contactDiseases.length === 0 && specific.length === 0) return null;

  const toggleContact = (code: string) => onChange((d) => ({
    ...d,
    contactDiseases: d.contactDiseases.includes(code)
      ? d.contactDiseases.filter((c) => c !== code)
      : [...d.contactDiseases, code],
  }));
  const setSpecific = (code: string, exposure: string, value: boolean) => onChange((d) => ({
    ...d,
    specific: { ...d.specific, [code]: { ...d.specific[code], [exposure]: value } },
  }));
  const contactMissing = showErrors && (
    draft.contactAny == null || (draft.contactAny && draft.contactDiseases.length === 0)
  );

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display text-lg font-bold">Autres maladies sous surveillance</h3>
        <p className="text-sm text-slate-500 mt-1">
          Questions définies par les autorités sanitaires, adaptées à votre itinéraire.
        </p>
      </div>

      {contactDiseases.length > 0 && (
        <fieldset className={`card p-4 sm:p-5 space-y-3 ${contactMissing ? 'border-2 border-rose-300' : ''}`}>
          <legend className="sr-only">Contact avec une personne malade</legend>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="text-sm font-medium pr-4">
              Au cours des 21 derniers jours, avez-vous été en contact avec une personne atteinte de :{' '}
              {contactDiseases.map((d) => d.name).join(', ')} ? <span className="text-rose-600">*</span>
            </div>
            <YesNo
              name="screening:contact"
              value={draft.contactAny}
              onChange={(v) => onChange((d) => ({ ...d, contactAny: v, contactDiseases: v ? d.contactDiseases : [] }))}
              error={showErrors}
            />
          </div>
          {draft.contactAny === true && (
            <div role="group" aria-label="Maladie de la personne rencontrée">
              <p className="text-sm font-medium">Laquelle ou lesquelles ? <span className="text-rose-600">*</span></p>
              <div className="mt-2 grid sm:grid-cols-2 gap-2">
                {contactDiseases.map((d) => (
                  <label key={d.code} className="inline-flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={draft.contactDiseases.includes(d.code)}
                      onChange={() => toggleContact(d.code)}
                    />
                    {d.name}
                  </label>
                ))}
              </div>
            </div>
          )}
        </fieldset>
      )}

      {specific.map(({ disease, countries }) => (
        <fieldset key={disease.code} className="card p-4 sm:p-5 space-y-3">
          <legend className="px-1 font-semibold text-ciDark dark:text-emerald-200">
            {disease.name}{' '}
            {countries.length > 0 && (
              <span className="ml-1 text-xs font-normal text-slate-500">
                — surveillance renforcée : {countries.map((c) => COUNTRY_NAME.get(c) || c).join(', ')}
              </span>
            )}
          </legend>
          {disease.specific_exposures.map((e) => {
            const value = draft.specific[disease.code]?.[e.code];
            return (
              <div
                key={e.code}
                className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl p-2 ${
                  showErrors && value == null ? 'ring-2 ring-rose-200' : ''
                }`}
              >
                <div className="text-sm font-medium pr-4">{e.label} <span className="text-rose-600">*</span></div>
                <YesNo
                  name={`${disease.code}:${e.code}`}
                  value={value}
                  onChange={(v) => setSpecific(disease.code, e.code, v)}
                  error={showErrors}
                />
              </div>
            );
          })}
        </fieldset>
      ))}
    </div>
  );
}
