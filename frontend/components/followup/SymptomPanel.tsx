'use client';

/**
 * SymptomPanel — Liste des MedicalSymptomReport déclarés pour un cas.
 *
 * Le backend Phase 9B n'expose pas (encore) de GET liste paginée pour les
 * symptômes ; on s'appuie donc sur un array reçu en props (typiquement
 * pré-chargé par le parent via le détail ou en local state après POST).
 *
 * Quand le parent veut conserver le panel synchronisé, il peut :
 *   - passer la liste initiale via `symptoms`
 *   - utiliser `onCreated` pour ajouter localement le nouveau symptôme
 *     retourné par AddSymptomModal
 *
 * Symptôme `is_critical=true` → bordure rouge + badge "Critique".
 */

import { useMemo, useState } from 'react';
import { Activity, AlertTriangle, Plus, User as UserIcon, Calendar } from 'lucide-react';
import { CaseClassificationBadge } from './CaseClassificationBadge';
import { AddSymptomModal } from './modals/AddSymptomModal';

export interface SymptomReport {
  id: number;
  uuid?: string;
  symptom_code: string;
  symptom_label: string;
  severity: 'mild' | 'moderate' | 'severe' | 'critical' | string;
  severity_label?: string;
  onset_date: string;
  source: string;
  source_label?: string;
  notes: string;
  is_critical: boolean;
  reported_by_name?: string;
  reported_by_traveler?: boolean;
  created_at?: string;
}

interface Props {
  travelerId: string;
  symptoms: SymptomReport[];
  /** Appelé après création réussie d'un symptôme — le parent peut concat. */
  onCreated?: (created: SymptomReport) => void;
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  mild: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Légère' },
  moderate: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'Modérée' },
  severe: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', label: 'Sévère' },
  critical: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-300', label: 'Critique' },
};

function formatDate(d: string | null | undefined): string {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return d;
  }
}

export function SymptomPanel({ travelerId, symptoms, onCreated }: Props) {
  const [modalOpen, setModalOpen] = useState(false);

  const sorted = useMemo(
    () => [...symptoms].sort((a, b) => {
      const da = new Date(a.onset_date).getTime();
      const db = new Date(b.onset_date).getTime();
      return db - da;
    }),
    [symptoms],
  );

  const criticalCount = useMemo(
    () => symptoms.filter((s) => s.is_critical || s.severity === 'critical').length,
    [symptoms],
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-rose-600" />
            <h2 className="font-display text-lg font-black text-ciDark">Symptômes</h2>
            {criticalCount > 0 && (
              <CaseClassificationBadge
                classification="suspect"
                label={`${criticalCount} critique${criticalCount > 1 ? 's' : ''}`}
              />
            )}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {symptoms.length} déclaration(s) totale(s).
          </div>
        </div>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 text-white px-3 py-1.5 text-xs font-bold hover:bg-emerald-700"
        >
          <Plus className="h-3.5 w-3.5" /> Ajouter symptôme
        </button>
      </header>

      {sorted.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-sm">
          Aucun symptôme déclaré pour ce voyageur.
        </div>
      ) : (
        <ul className="space-y-2.5">
          {sorted.map((s) => {
            const sev = SEVERITY_STYLES[s.severity] ?? SEVERITY_STYLES.mild;
            const isCritical = s.is_critical || s.severity === 'critical';
            return (
              <li
                key={s.id}
                className={`rounded-xl border p-3 ${isCritical ? 'border-rose-300 bg-rose-50/40' : 'border-slate-200 bg-white'}`}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-slate-800">
                        {s.symptom_label || s.symptom_code}
                      </span>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${sev.bg} ${sev.text} ${sev.border}`}>
                        {s.severity_label || sev.label}
                      </span>
                      {isCritical && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-100 text-rose-700 border border-rose-300">
                          <AlertTriangle className="h-3 w-3" /> Critique
                        </span>
                      )}
                    </div>
                    {s.notes && (
                      <p className="mt-1 text-xs text-slate-600 whitespace-pre-wrap">
                        {s.notes}
                      </p>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 text-right shrink-0">
                    <div className="inline-flex items-center gap-1">
                      <Calendar className="h-3 w-3" /> {formatDate(s.onset_date)}
                    </div>
                    {(s.reported_by_name || s.reported_by_traveler) && (
                      <div className="inline-flex items-center gap-1 mt-1">
                        <UserIcon className="h-3 w-3" />
                        {s.reported_by_traveler ? 'Voyageur' : s.reported_by_name}
                      </div>
                    )}
                    {s.source_label && (
                      <div className="text-slate-400 mt-1 font-mono">{s.source_label}</div>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <AddSymptomModal
        open={modalOpen}
        travelerId={travelerId}
        onClose={() => setModalOpen(false)}
        onSuccess={(created) => {
          setModalOpen(false);
          onCreated?.(created);
        }}
      />
    </section>
  );
}

export default SymptomPanel;
