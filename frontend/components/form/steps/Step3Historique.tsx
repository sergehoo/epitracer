'use client';

import { useState } from 'react';
import { Plane, Plus, Trash2 } from 'lucide-react';
import { COUNTRIES } from '@/lib/datasets';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, FieldRow } from '@/components/form/Field';
import type { HistoryItem } from '@/types/ebola';

function emptyItem(role: HistoryItem['role']): HistoryItem {
  return {
    role,
    country_code: '',
    city: '',
    province: '',
    residence_address: '',
    hotel: '',
    room_number: '',
    duration_text: '',
  };
}

export function Step3Historique({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { historique = [], set, goTo } = useRegistrationStore();
  const [items, setItems] = useState<HistoryItem[]>(
    historique.length ? historique : [emptyItem('origin')],
  );
  const [errors, setErrors] = useState<Record<number, string>>({});
  const [globalError, setGlobalError] = useState<string | null>(null);

  const update = (i: number, patch: Partial<HistoryItem>) => {
    setItems((arr) => arr.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  };
  const remove = (i: number) => setItems((arr) => arr.filter((_, idx) => idx !== i));
  const add = (role: HistoryItem['role']) => setItems((arr) => [...arr, emptyItem(role)]);

  const submit = () => {
    const next: Record<number, string> = {};
    items.forEach((it, idx) => {
      if (!it.country_code) next[idx] = 'Pays obligatoire.';
      else if (!it.city || !it.city.trim()) next[idx] = 'Ville obligatoire.';
      else if (it.role !== 'transit' && (!it.province || !it.province.trim())) {
        // Province obligatoire SAUF pour un pays de transit (séjour très court).
        next[idx] = 'Province / région obligatoire.';
      }
    });
    setErrors(next);
    const hasOrigin = items.some((it) => it.role === 'origin' && it.country_code);
    if (!hasOrigin) {
      setGlobalError('Le pays de provenance est obligatoire.');
      return;
    }
    if (Object.keys(next).length > 0) {
      setGlobalError('Veuillez compléter les champs obligatoires indiqués.');
      return;
    }
    setGlobalError(null);
    set({ historique: items });
    goTo(3);
    onNext();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">3. Historique des déplacements</h2>
        <p className="text-sm text-slate-500 mt-1">
          3 dernières semaines / 21 derniers jours. Indiquez impérativement les pays visités ou transités.
        </p>
      </div>

      <div className="space-y-4">
        {items.map((item, i) => {
          const isTransit = item.role === 'transit';
          return (
            <article key={i} className="card p-5 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-200">
                  <Plane className="h-3.5 w-3.5" />
                  {item.role === 'origin' && 'Pays de provenance'}
                  {item.role === 'transit' && 'Pays de transit'}
                  {item.role === 'visited' && 'Autre pays visité (3 dernières semaines)'}
                </div>
                {items.length > 1 && (
                  <button type="button" onClick={() => remove(i)} className="btn-ghost text-rose-600 text-xs">
                    <Trash2 className="h-3.5 w-3.5" /> Supprimer
                  </button>
                )}
              </div>

              {isTransit ? (
                // ---- TRANSIT : 3 champs uniquement (Pays, Ville, Durée) ----
                <FieldRow>
                  <FieldGroup label="Pays" required>
                    <select
                      className="select"
                      value={item.country_code}
                      onChange={(e) => update(i, { country_code: e.target.value })}
                    >
                      <option value="">Sélectionner —</option>
                      {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                    </select>
                  </FieldGroup>
                  <FieldGroup label="Ville" required>
                    <input
                      className="input"
                      value={item.city || ''}
                      onChange={(e) => update(i, { city: e.target.value })}
                      placeholder="ex : Casablanca"
                    />
                  </FieldGroup>
                </FieldRow>
              ) : (
                // ---- ORIGIN / VISITED : avec Province + adresse + hôtel ----
                <>
                  <FieldRow>
                    <FieldGroup label="Pays" required>
                      <select
                        className="select"
                        value={item.country_code}
                        onChange={(e) => update(i, { country_code: e.target.value })}
                      >
                        <option value="">Sélectionner —</option>
                        {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                      </select>
                    </FieldGroup>
                    <FieldGroup label="Ville" required>
                      <input
                        className="input"
                        value={item.city || ''}
                        onChange={(e) => update(i, { city: e.target.value })}
                        placeholder="ex : Goma"
                      />
                    </FieldGroup>
                  </FieldRow>

                  <FieldRow>
                    <FieldGroup label="Province / Région" required>
                      <input
                        className="input"
                        value={item.province || ''}
                        onChange={(e) => update(i, { province: e.target.value })}
                        placeholder="ex : Nord-Kivu"
                      />
                    </FieldGroup>
                    <FieldGroup label="Adresse de résidence">
                      <input
                        className="input"
                        value={item.residence_address || ''}
                        onChange={(e) => update(i, { residence_address: e.target.value })}
                      />
                    </FieldGroup>
                  </FieldRow>

                  <FieldRow>
                    <FieldGroup label="Hôtel / N° Chambre">
                      <input
                        className="input"
                        value={`${item.hotel || ''}${item.room_number ? ' / ' + item.room_number : ''}`}
                        onChange={(e) => {
                          const [h, r] = e.target.value.split('/').map((s) => s.trim());
                          update(i, { hotel: h || '', room_number: r || '' });
                        }}
                        placeholder="ex : Hôtel Pullman / 314"
                      />
                    </FieldGroup>
                    <FieldGroup label="Période (optionnel)">
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="date"
                          className="input"
                          value={item.arrival_date || ''}
                          onChange={(e) => update(i, { arrival_date: e.target.value })}
                        />
                        <input
                          type="date"
                          className="input"
                          value={item.departure_date || ''}
                          onChange={(e) => update(i, { departure_date: e.target.value })}
                        />
                      </div>
                    </FieldGroup>
                  </FieldRow>
                </>
              )}

              <FieldRow>
                <FieldGroup label={isTransit ? 'Durée du transit' : 'Durée du séjour'}>
                  <input
                    className="input"
                    value={item.duration_text || ''}
                    onChange={(e) => update(i, { duration_text: e.target.value })}
                    placeholder={isTransit ? 'ex : 4 heures' : 'ex : 12 jours'}
                  />
                </FieldGroup>
                <div />
              </FieldRow>

              {errors[i] && <p className="field-error">{errors[i]}</p>}
            </article>
          );
        })}
      </div>

      {globalError && <p className="field-error">{globalError}</p>}

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => add('transit')} className="btn-outline text-sm">
          <Plus className="h-4 w-4" /> Ajouter un pays de transit
        </button>
        <button type="button" onClick={() => add('visited')} className="btn-outline text-sm">
          <Plus className="h-4 w-4" /> Ajouter un autre pays visité
        </button>
      </div>

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="button" onClick={submit} className="btn-primary">Suivant : Résidence →</button>
      </div>
    </div>
  );
}
