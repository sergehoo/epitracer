'use client';

import { useState } from 'react';
import { ShieldAlert } from 'lucide-react';
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

export function Step5Exposure({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { exposure, set, goTo } = useRegistrationStore();
  const [state, setState] = useState<SectionExposure>(exposure ?? {
    visited_ebola_zone: false,
    visited_ebola_zone_details: '',
    contact_with_case: false,
    attended_funeral_or_touched_corpse: false,
    visited_ebola_healthcare_facility: false,
  });
  const [error, setError] = useState<string | null>(null);

  const setKey = <K extends keyof SectionExposure>(k: K, v: SectionExposure[K]) =>
    setState((s) => ({ ...s, [k]: v }));

  const submit = () => {
    const parse = exposureSchema.safeParse(state);
    if (!parse.success) {
      setError(parse.error.errors[0]?.message || 'Vérifiez vos réponses.');
      return;
    }
    setError(null);
    set({ exposure: state });
    goTo(5);
    onNext();
  };

  const positives = QUESTIONS.filter((q) => state[q.key] === true).length;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">5. Évaluation Épidémiologique du Risque</h2>
        <p className="text-sm text-slate-500 mt-1">
          Réponses portant sur les <strong>21 derniers jours</strong>. Répondez avec honnêteté —
          ces réponses sont utilisées pour calculer votre niveau de risque.
        </p>
      </div>

      <div className="space-y-3">
        {QUESTIONS.map((q) => (
          <div key={q.key} className="card p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="text-sm font-medium pr-4">{q.label}</div>
            <YesNo name={q.key} value={state[q.key] as boolean} onChange={(v) => setKey(q.key, v as any)} />
          </div>
        ))}
      </div>

      {state.visited_ebola_zone && (
        <FieldGroup label="Si oui, précisez la ville / région et le pays" required>
          <input
            className="input"
            value={state.visited_ebola_zone_details || ''}
            onChange={(e) => setKey('visited_ebola_zone_details', e.target.value)}
            placeholder="ex : Goma, RDC"
          />
        </FieldGroup>
      )}

      <div className={`rounded-xl p-4 border ${positives >= 2 ? 'bg-rose-50 border-rose-200 dark:bg-rose-950/30 dark:border-rose-900' : 'bg-slate-50 border-slate-200 dark:bg-slate-900 dark:border-slate-800'}`}>
        <div className="text-sm flex items-center gap-2">
          <ShieldAlert className={positives >= 2 ? 'h-4 w-4 text-rose-600' : 'h-4 w-4 text-slate-500'} />
          <strong>{positives}</strong> réponse{positives > 1 ? 's' : ''} positive{positives > 1 ? 's' : ''}
          {positives >= 2 ? ' — niveau de risque potentiellement élevé.' : ' — répondez aussi à la section suivante.'}
        </div>
      </div>

      {error && <p className="field-error">{error}</p>}

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="button" onClick={submit} className="btn-primary">Suivant : Symptômes →</button>
      </div>
    </div>
  );
}
