'use client';

import { useState } from 'react';
import { HeartPulse } from 'lucide-react';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, YesNo } from '@/components/form/Field';
import type { SectionSymptoms } from '@/types/ebola';

const SYMPTOMS: { key: keyof SectionSymptoms; label: string }[] = [
  { key: 'fever', label: 'Fièvre (≥ 38°C) ou sensation de forte chaleur' },
  { key: 'intense_fatigue', label: 'Fatigue intense, faiblesse généralisée inexpliquée' },
  { key: 'muscle_joint_pain', label: 'Douleurs musculaires, articulaires ou courbatures' },
  { key: 'severe_headache', label: 'Maux de tête intenses (Céphalées)' },
  { key: 'sore_throat_or_abdominal', label: 'Maux de gorge ou douleurs abdominales (estomac)' },
  { key: 'diarrhea_nausea_vomiting', label: 'Diarrhée, nausées ou vomissements fréquents' },
  { key: 'unexplained_bleeding', label: 'Saignements inexpliqués (nez, gencives, peau, urines, selles)' },
];

export function Step6Symptoms({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { symptoms, set, goTo } = useRegistrationStore();
  const [state, setState] = useState<SectionSymptoms>(symptoms ?? {
    fever: false, intense_fatigue: false, muscle_joint_pain: false, severe_headache: false,
    sore_throat_or_abdominal: false, diarrhea_nausea_vomiting: false, unexplained_bleeding: false,
    other_symptoms: '',
  });

  const setKey = <K extends keyof SectionSymptoms>(k: K, v: SectionSymptoms[K]) =>
    setState((s) => ({ ...s, [k]: v }));

  const submit = () => {
    set({ symptoms: state });
    goTo(6);
    onNext();
  };

  const positives = SYMPTOMS.filter((s) => state[s.key] === true).length;
  const redFlag = state.unexplained_bleeding;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">6. État de santé</h2>
        <p className="text-sm text-slate-500 mt-1">
          Présentez-vous actuellement l'un des signes suivants au cours des <strong>48 dernières heures</strong> ?
        </p>
      </div>

      <div className="space-y-3">
        {SYMPTOMS.map((q) => (
          <div key={q.key} className="card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="text-sm font-medium pr-4">{q.label}</div>
            <YesNo name={q.key} value={state[q.key] as boolean} onChange={(v) => setKey(q.key, v as any)} />
          </div>
        ))}
      </div>

      <FieldGroup label="Température mesurée (°C)" help="Renseignez votre température corporelle si vous l'avez prise récemment.">
        <input
          type="number"
          step={0.1}
          min={30}
          max={45}
          className="input max-w-[140px]"
          value={state.temperature_celsius ?? ''}
          onChange={(e) => setKey('temperature_celsius', e.target.value ? Number(e.target.value) : undefined)}
        />
      </FieldGroup>

      <FieldGroup label="Autres symptômes (optionnel)">
        <textarea
          className="textarea"
          rows={3}
          value={state.other_symptoms || ''}
          onChange={(e) => setKey('other_symptoms', e.target.value)}
        />
      </FieldGroup>

      <div className={`rounded-xl p-4 border ${redFlag ? 'bg-red-900 text-white border-red-700' : positives >= 2 ? 'bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-900' : 'bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-900'}`}>
        <div className="text-sm flex items-center gap-2">
          <HeartPulse className="h-4 w-4" />
          {redFlag ? (
            <span><strong>Symptôme alarmant détecté.</strong> Composez immédiatement le 185 (SAMU) ou 143 (Allô Santé).</span>
          ) : positives >= 2 ? (
            <span><strong>{positives}</strong> symptômes déclarés — vous serez placé sous surveillance.</span>
          ) : (
            <span>{positives === 0 ? 'Aucun symptôme déclaré.' : `${positives} symptôme déclaré.`} — surveillance simple.</span>
          )}
        </div>
      </div>

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="button" onClick={submit} className="btn-primary">Suivant : Déclaration →</button>
      </div>
    </div>
  );
}
