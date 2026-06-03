'use client';

import { useState } from 'react';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, YesNo } from '@/components/form/Field';
import { exposureSchema } from '@/lib/schema';
import type { SectionExposure } from '@/types/ebola';

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
  const { exposure, set, goTo } = useRegistrationStore();
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
    const unanswered = QUESTIONS.filter((q) => state[q.key] === null || state[q.key] === undefined);
    if (unanswered.length > 0) {
      setShowErrors(true);
      setError(
        `Veuillez répondre à toutes les questions (${unanswered.length} restante${unanswered.length > 1 ? 's' : ''}).`,
      );
      // Scroll vers la 1ère question non répondue
      setTimeout(() => {
        const el = document.querySelector(`[data-name="${unanswered[0].key}"]`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
      return;
    }

    // Cast vers SectionExposure pour le schema (tous les null → boolean garanti)
    const parse = exposureSchema.safeParse(state);
    if (!parse.success) {
      setError(parse.error.errors[0]?.message || 'Vérifiez vos réponses.');
      return;
    }
    setError(null);
    setShowErrors(false);
    set({ exposure: state as SectionExposure });
    goTo(5);
    onNext();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">5. Questionnaire de prévention</h2>
        <p className="text-sm text-slate-500 mt-1">
          Réponses portant sur les <strong>21 derniers jours</strong>. Toutes les questions
          sont <strong className="text-rose-600">obligatoires</strong>. Vos réponses aident
          l'INHP à mieux vous accompagner.
        </p>
      </div>

      <div className="space-y-3">
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

      {state.visited_ebola_zone === true && (
        <FieldGroup label="Si oui, précisez la ville / région et le pays" required>
          <input
            className="input"
            value={state.visited_ebola_zone_details || ''}
            onChange={(e) => setKey('visited_ebola_zone_details', e.target.value)}
            placeholder="ex : Goma, RDC"
          />
        </FieldGroup>
      )}

      {error && <p className="field-error">{error}</p>}

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="button" onClick={submit} className="btn-primary">Suivant : Symptômes →</button>
      </div>
    </div>
  );
}
