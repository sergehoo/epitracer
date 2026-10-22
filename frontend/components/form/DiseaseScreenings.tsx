'use client';

/**
 * Questionnaires des maladies sous surveillance active (hors Ebola, qui garde
 * sa section INHP dédiée). Questions et symptômes viennent du référentiel
 * maladies (/api/v1/public/registration-config/) : rien n'est codé en dur.
 */

import { YesNo } from '@/components/form/Field';
import type { ScreeningAnswer, ScreeningDisease } from '@/types/portal';

/** Réponses en cours : exposition → oui/non/null, symptômes cochés. */
export type ScreeningDraft = Record<string, { exposures: Record<string, boolean | null>; symptoms: string[] }>;

export function initialScreeningDraft(diseases: ScreeningDisease[], saved?: ScreeningAnswer[]): ScreeningDraft {
  const byCode = new Map((saved || []).map((s) => [s.disease, s]));
  return Object.fromEntries(diseases.map((d) => {
    const prev = byCode.get(d.code);
    return [d.code, {
      exposures: Object.fromEntries(d.exposures.map((e) => [e.code, prev ? prev.exposures.includes(e.code) : null])),
      symptoms: prev?.symptoms ?? [],
    }];
  }));
}

export function unansweredExposures(diseases: ScreeningDisease[], draft: ScreeningDraft): string[] {
  return diseases.flatMap((d) => d.exposures
    .filter((e) => draft[d.code]?.exposures[e.code] == null)
    .map((e) => `${d.code}:${e.code}`));
}

export function toScreeningAnswers(draft: ScreeningDraft): ScreeningAnswer[] {
  return Object.entries(draft).map(([disease, a]) => ({
    disease,
    exposures: Object.entries(a.exposures).filter(([, v]) => v === true).map(([k]) => k),
    symptoms: a.symptoms,
  }));
}

export function DiseaseScreenings({
  diseases, draft, onChange, showErrors,
}: {
  diseases: ScreeningDisease[];
  draft: ScreeningDraft;
  onChange: (next: ScreeningDraft) => void;
  showErrors: boolean;
}) {
  if (diseases.length === 0) return null;

  const setExposure = (code: string, exposure: string, value: boolean) =>
    onChange({ ...draft, [code]: { ...draft[code], exposures: { ...draft[code].exposures, [exposure]: value } } });
  const toggleSymptom = (code: string, symptom: string) => {
    const current = draft[code].symptoms;
    const symptoms = current.includes(symptom) ? current.filter((s) => s !== symptom) : [...current, symptom];
    onChange({ ...draft, [code]: { ...draft[code], symptoms } });
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="font-display text-lg font-bold">Autres maladies sous surveillance</h3>
        <p className="text-sm text-slate-500 mt-1">
          Questions définies par les autorités sanitaires pour chaque maladie actuellement surveillée.
        </p>
      </div>
      {diseases.map((d) => (
        <fieldset key={d.code} className="card p-4 sm:p-5 space-y-3">
          <legend className="px-1 font-semibold text-ciDark dark:text-emerald-200">
            {d.name}{' '}
            <span className="ml-1 text-xs font-normal text-slate-500">
              suivi de {d.followup_days} jours si nécessaire
            </span>
          </legend>
          {d.exposures.map((e) => {
            const value = draft[d.code]?.exposures[e.code];
            return (
              <div
                key={e.code}
                className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl p-2 ${
                  showErrors && value == null ? 'ring-2 ring-rose-200' : ''
                }`}
              >
                <div className="text-sm font-medium pr-4">{e.label} <span className="text-rose-600">*</span></div>
                <YesNo
                  name={`${d.code}:${e.code}`}
                  value={value}
                  onChange={(v) => setExposure(d.code, e.code, v)}
                  error={showErrors}
                />
              </div>
            );
          })}
          {d.symptoms.length > 0 && (
            <div>
              <p className="text-sm font-medium">Avez-vous présenté l&apos;un de ces symptômes ces dernières 48 heures ?</p>
              <div className="mt-2 grid sm:grid-cols-2 gap-2">
                {d.symptoms.map((s) => (
                  <label key={s.code} className="inline-flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={draft[d.code]?.symptoms.includes(s.code) ?? false}
                      onChange={() => toggleSymptom(d.code, s.code)}
                    />
                    {s.label}
                  </label>
                ))}
              </div>
            </div>
          )}
        </fieldset>
      ))}
    </div>
  );
}
