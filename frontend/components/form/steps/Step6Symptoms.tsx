'use client';

import { useState } from 'react';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, YesNo } from '@/components/form/Field';
import type { SectionSymptoms } from '@/types/ebola';

const SYMPTOMS: { key: keyof SectionSymptoms; label: string }[] = [
  { key: 'fever', label: 'Fièvre (≥ 38°C) ou corps chaud' },
  { key: 'intense_fatigue', label: 'Fatigue intense, faiblesse généralisée' },
  { key: 'muscle_joint_pain', label: 'Douleurs musculaires, articulaires ou courbatures' },
  { key: 'severe_headache', label: 'Maux de tête intenses (Céphalées)' },
  { key: 'sore_throat_or_abdominal', label: 'Maux de gorge (estomac)' },
  { key: 'diarrhea_nausea_vomiting', label: 'Diarrhée, nausées ou vomissements ou abdominales' },
  { key: 'unexplained_bleeding', label: 'Saignements (nez, gencives, peau, urines, selles)' },
];

type SymptomsDraft = {
  [K in keyof SectionSymptoms]: SectionSymptoms[K] extends boolean
    ? boolean | null
    : SectionSymptoms[K];
};

export function Step6Symptoms({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { symptoms, set, goTo } = useRegistrationStore();
  // Initialise à null pour FORCER l'utilisateur à répondre à chaque symptôme
  const [state, setState] = useState<SymptomsDraft>(
    (symptoms as SymptomsDraft) ?? {
      fever: null, intense_fatigue: null, muscle_joint_pain: null, severe_headache: null,
      sore_throat_or_abdominal: null, diarrhea_nausea_vomiting: null, unexplained_bleeding: null,
      other_symptoms: '',
    }
  );
  const [error, setError] = useState<string | null>(null);
  const [showErrors, setShowErrors] = useState(false);

  const setKey = <K extends keyof SymptomsDraft>(k: K, v: SymptomsDraft[K]) =>
    setState((s) => ({ ...s, [k]: v }));

  const submit = () => {
    const unanswered = SYMPTOMS.filter((q) => state[q.key] === null || state[q.key] === undefined);
    if (unanswered.length > 0) {
      setShowErrors(true);
      setError(
        `Veuillez répondre à toutes les questions (${unanswered.length} restante${unanswered.length > 1 ? 's' : ''}).`,
      );
      setTimeout(() => {
        const el = document.querySelector(`[data-name="${unanswered[0].key}"]`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
      return;
    }
    // Température OBLIGATOIRE si fièvre déclarée
    if (state.fever === true && !state.temperature_celsius) {
      setShowErrors(true);
      setError('Vous avez déclaré une fièvre — la température mesurée est obligatoire.');
      return;
    }
    setError(null);
    setShowErrors(false);
    set({ symptoms: state as SectionSymptoms });
    goTo(6);
    onNext();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">6. Comment vous sentez-vous ?</h2>
        <p className="text-sm text-slate-500 mt-1">
          Avez-vous ressenti l'un des signes suivants au cours des <strong>48 dernières heures</strong> ?
          Toutes les questions sont <strong className="text-rose-600">obligatoires</strong>.
          Vos réponses restent confidentielles.
        </p>
      </div>

      <div className="space-y-3">
        {SYMPTOMS.map((q) => {
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

      <FieldGroup
        label="Température mesurée (°C)"
        required={state.fever === true}
        help={
          state.fever === true
            ? 'Vous avez déclaré une fièvre — renseignez votre température corporelle.'
            : "Renseignez votre température corporelle si vous l'avez prise récemment."
        }
      >
        <input
          type="number"
          step={0.1}
          min={30}
          max={45}
          className={`input max-w-[140px] ${
            showErrors && state.fever === true && !state.temperature_celsius
              ? 'border-rose-400 ring-2 ring-rose-200'
              : ''
          }`}
          value={state.temperature_celsius ?? ''}
          onChange={(e) =>
            setKey('temperature_celsius', e.target.value ? Number(e.target.value) : undefined)
          }
          placeholder="37.0"
        />
      </FieldGroup>

      <FieldGroup label="Autres symptômes (optionnel)">
        <textarea
          className="textarea"
          rows={3}
          value={state.other_symptoms || ''}
          onChange={(e) => setKey('other_symptoms', e.target.value)}
          placeholder="Précisez d'autres symptômes ressentis..."
        />
      </FieldGroup>

      {error && <p className="field-error">{error}</p>}

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="button" onClick={submit} className="btn-primary">Suivant : Déclaration →</button>
      </div>
    </div>
  );
}
