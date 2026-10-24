'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRegistrationStore } from '@/lib/store';
import { useRegistrationConfig } from '@/lib/registrationConfig';
import { FieldGroup, YesNo } from '@/components/form/Field';
import {
  DiseaseScreenings, ScreeningDraft, initialScreeningDraft, toScreeningAnswers, unansweredScreening,
} from '@/components/form/DiseaseScreenings';
import { exposureSchema } from '@/lib/schema';
import type { SectionExposure } from '@/types/ebola';

const NO_EBOLA_EXPOSURE: SectionExposure = {
  visited_ebola_zone: false,
  visited_ebola_zone_details: '',
  contact_with_case: false,
  attended_funeral_or_touched_corpse: false,
  visited_ebola_healthcare_facility: false,
};

const QUESTIONS: { key: keyof SectionExposure; label: string }[] = [
  { key: 'visited_ebola_zone', label: "Avez-vous séjourné ou transité par une zone touchée par l'épidémie d'Ebola ?" },
  { key: 'contact_with_case', label: "Avez-vous été en contact avec une personne malade ou suspectée d'avoir Ebola ?" },
  { key: 'attended_funeral_or_touched_corpse', label: 'Avez-vous assisté à des funérailles ou touché une dépouille humaine ?' },
  { key: 'visited_ebola_healthcare_facility', label: 'Avez-vous fréquenté un établissement de soins traitant des patients Ebola ?' },
];

type ExposureDraft = {
  [K in keyof SectionExposure]: SectionExposure[K] extends boolean
    ? boolean | null
    : SectionExposure[K];
};

export function Step5Exposure({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { exposure, screenings, historique, set, goTo } = useRegistrationStore();
  // Configuration par maladie (repli : questionnaire Ebola historique seul).
  const config = useRegistrationConfig();
  const showEbola = config?.ebola_questionnaire ?? true;
  const otherDiseases = useMemo(() => config?.diseases ?? [], [config]);
  // Pays de provenance / transit / visités déclarés à l'étape « Historique »
  const visited = useMemo(
    () => Array.from(new Set((historique || []).map((h) => h.country_code).filter(Boolean))),
    [historique],
  );
  const [screeningDraft, setScreeningDraft] = useState<ScreeningDraft>(
    { contactAny: null, contactDiseases: [], specific: {} },
  );
  useEffect(() => {
    if (config) setScreeningDraft(initialScreeningDraft(config.diseases, screenings));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config]);
  // Initialise à null pour FORCER l'utilisateur à répondre (au lieu de
  // false par défaut — qui correspondrait à "non" implicite).
  const [state, setState] = useState<ExposureDraft>(
    (exposure as ExposureDraft) ?? {
      visited_ebola_zone: null,
      visited_ebola_zone_details: '',
      contact_with_case: null,
      attended_funeral_or_touched_corpse: null,
      visited_ebola_healthcare_facility: null,
    }
  );
  const [error, setError] = useState<string | null>(null);
  const [showErrors, setShowErrors] = useState(false);

  const setKey = <K extends keyof ExposureDraft>(k: K, v: ExposureDraft[K]) =>
    setState((s) => ({ ...s, [k]: v }));

  const submit = () => {
    // Vérifie que TOUTES les questions oui/non ont reçu une réponse.
    const unanswered = [
      ...(showEbola
        ? QUESTIONS.filter((q) => state[q.key] === null || state[q.key] === undefined).map((q) => q.key)
        : []),
      ...unansweredScreening(otherDiseases, visited, screeningDraft),
    ];
    if (unanswered.length > 0) {
      setShowErrors(true);
      setError(
        `Veuillez répondre à toutes les questions (${unanswered.length} restante${unanswered.length > 1 ? 's' : ''}).`,
      );
      // Scroll vers la 1ère question non répondue
      setTimeout(() => {
        const el = document.querySelector(`[data-name="${unanswered[0]}"]`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
      return;
    }

    // Ebola hors surveillance : section masquée, réponses « non » par défaut.
    const ebolaAnswers = showEbola ? state : NO_EBOLA_EXPOSURE;
    // Cast vers SectionExposure pour le schema (tous les null → boolean garanti)
    const parse = exposureSchema.safeParse(ebolaAnswers);
    if (!parse.success) {
      setError(parse.error.errors[0]?.message || 'Vérifiez vos réponses.');
      return;
    }
    setError(null);
    setShowErrors(false);
    set({
      exposure: ebolaAnswers as SectionExposure,
      screenings: toScreeningAnswers(otherDiseases, visited, screeningDraft),
    });
    goTo(5);
    onNext();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">5. Questionnaire de prévention</h2>
        <p className="text-sm text-slate-500 mt-1">
          Réponses portant sur les <strong>21 derniers jours</strong>. Toutes les questions
          sont <strong className="text-rose-600">obligatoires</strong>. Elles portent sur les
          maladies actuellement sous surveillance et aident l'INHP à mieux vous accompagner.
        </p>
      </div>

      {config === null && <p className="text-sm text-slate-500" role="status">Chargement du questionnaire…</p>}

      {showEbola && (
      <div className="space-y-3">
        {otherDiseases.length > 0 && (
          <h3 className="font-display text-lg font-bold">Maladie à virus Ebola</h3>
        )}
        {QUESTIONS.map((q) => {
          const unanswered = state[q.key] === null || state[q.key] === undefined;
          return (
            <div
              key={q.key}
              className={`card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 ${
                showErrors && unanswered ? 'border-2 border-rose-300 dark:border-rose-800/60' : ''
              }`}
            >
              <div className="text-sm font-medium pr-4">
                {q.label} <span className="text-rose-600">*</span>
              </div>
              <YesNo
                name={q.key}
                value={state[q.key] as boolean | null}
                onChange={(v) => setKey(q.key, v as any)}
                error={showErrors}
              />
            </div>
          );
        })}
      </div>
      )}

      {showEbola && state.visited_ebola_zone === true && (
        <FieldGroup label="Si oui, précisez la ville / région et le pays" required>
          <input
            className="input"
            value={state.visited_ebola_zone_details || ''}
            onChange={(e) => setKey('visited_ebola_zone_details', e.target.value)}
            placeholder="ex : Goma, RDC"
          />
        </FieldGroup>
      )}

      <DiseaseScreenings
        diseases={otherDiseases}
        visited={visited}
        draft={screeningDraft}
        onChange={setScreeningDraft}
        showErrors={showErrors}
      />

      {error && <p className="field-error" role="alert">{error}</p>}

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="button" onClick={submit} className="btn-primary">Suivant : Symptômes →</button>
      </div>
    </div>
  );
}
