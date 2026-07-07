'use client';

/**
 * LabAnalysisPanel — Liste des résultats d'analyses LabAnalysis.
 *
 * Comme les autres panels, on accepte la liste en prop puisque le backend
 * Phase 9B n'expose pas de GET liste paginée.
 *
 * Résultat positif → bordure rouge + bandeau d'alerte sticky.
 * Bouton "Ajouter résultat" → ouvre AddLabResultModal (le parent fournit la
 * liste des prélèvements disponibles, car le résultat doit être attaché à un
 * MedicalSample existant).
 */

import { useMemo, useState } from 'react';
import {
  TestTube2, Plus, AlertTriangle, FileText, Calendar, Building2, Loader2,
  CheckCircle2,
} from 'lucide-react';
import { AddLabResultModal } from './modals/AddLabResultModal';
import type { MedicalSample } from './SamplePanel';

export type LabAnalysisResult =
  | '' | 'negative' | 'positive' | 'indeterminate' | 'retest' | string;

export interface LabAnalysis {
  id: number;
  uuid?: string;
  sample: number;
  lab_name: string;
  test_type: string;
  status: string;
  status_label?: string;
  result: LabAnalysisResult;
  result_label?: string;
  received_at?: string | null;
  analyzed_at?: string | null;
  validated_at?: string | null;
  validated_by_name?: string;
  result_file?: string | null;
  notes: string;
  created_at?: string;
  updated_at?: string;
}

interface Props {
  travelerId: string;
  analyses: LabAnalysis[];
  /** Liste des prélèvements disponibles — utilisée par la modale d'ajout. */
  samples: MedicalSample[];
  onCreated?: (created: LabAnalysis) => void;
}

const RESULT_STYLES: Record<string, { bg: string; text: string; border: string; label: string; danger: boolean }> = {
  negative: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Négatif', danger: false },
  positive: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-300', label: 'Positif', danger: true },
  indeterminate: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'Indéterminé', danger: false },
  retest: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200', label: 'À refaire', danger: false },
};

const STATUS_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  pending: { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', label: 'En attente' },
  received: { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200', label: 'Reçu' },
  in_analysis: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200', label: 'En analyse' },
  result_available: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Résultat dispo' },
  validated: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300', label: 'Validé' },
  rejected: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'Rejeté' },
};

function formatDate(d: string | null | undefined): string {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return d;
  }
}

export function LabAnalysisPanel({ travelerId, analyses, samples, onCreated }: Props) {
  const [modalOpen, setModalOpen] = useState(false);

  const sorted = useMemo(
    () => [...analyses].sort((a, b) => {
      const da = new Date(a.created_at || a.received_at || 0).getTime();
      const db = new Date(b.created_at || b.received_at || 0).getTime();
      return db - da;
    }),
    [analyses],
  );

  const positiveCount = useMemo(
    () => analyses.filter((a) => a.result === 'positive').length,
    [analyses],
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2">
            <TestTube2 className="h-4 w-4 text-violet-600" />
            <h2 className="font-display text-lg font-black text-ciDark">Analyses laboratoire</h2>
            {positiveCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-100 text-rose-700 border border-rose-300">
                <AlertTriangle className="h-3 w-3" /> {positiveCount} positif{positiveCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {analyses.length} analyse(s) au dossier.
          </div>
        </div>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          disabled={samples.length === 0}
          title={samples.length === 0 ? 'Aucun prélèvement disponible — créer un prélèvement d\'abord.' : ''}
          className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 text-white px-3 py-1.5 text-xs font-bold hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="h-3.5 w-3.5" /> Ajouter résultat
        </button>
      </header>

      {positiveCount > 0 && (
        <div className="mb-3 rounded-xl border border-rose-300 bg-rose-50 p-3 text-xs text-rose-700">
          <div className="flex items-center gap-2 font-bold">
            <AlertTriangle className="h-4 w-4" /> Alerte clinique — résultat(s) positif(s)
          </div>
          <p className="mt-0.5 text-rose-600">
            Vérifier la classification du cas et déclencher le protocole de prise en charge.
          </p>
        </div>
      )}

      {sorted.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-sm">
          Aucun résultat d'analyse enregistré.
        </div>
      ) : (
        <ul className="space-y-2.5">
          {sorted.map((a) => {
            const res = a.result ? (RESULT_STYLES[a.result] ?? null) : null;
            const stat = STATUS_STYLES[a.status] ?? STATUS_STYLES.pending;
            const danger = res?.danger;
            return (
              <li
                key={a.id}
                className={`rounded-xl border p-3 ${danger ? 'border-rose-300 bg-rose-50/30' : 'border-slate-200'}`}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-slate-800">{a.test_type || 'Analyse'}</span>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${stat.bg} ${stat.text} ${stat.border}`}>
                        {a.status_label || stat.label}
                      </span>
                      {res && (
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${res.bg} ${res.text} ${res.border}`}>
                          {a.result_label || res.label}
                        </span>
                      )}
                      {a.validated_at && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="h-3 w-3" /> Validé
                        </span>
                      )}
                    </div>
                    <div className="mt-1.5 text-xs text-slate-600 flex flex-wrap gap-x-3 gap-y-1">
                      {a.lab_name && (
                        <span className="inline-flex items-center gap-1">
                          <Building2 className="h-3 w-3" /> {a.lab_name}
                        </span>
                      )}
                      {a.received_at && (
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3 w-3" /> Reçu : {formatDate(a.received_at)}
                        </span>
                      )}
                      {a.validated_at && (
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3 w-3" /> Validé : {formatDate(a.validated_at)}
                          {a.validated_by_name && <> · {a.validated_by_name}</>}
                        </span>
                      )}
                    </div>
                    {a.notes && (
                      <p className="mt-1 text-xs text-slate-500 italic whitespace-pre-wrap">{a.notes}</p>
                    )}
                    {a.result_file && (
                      <a
                        href={a.result_file}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-sky-700 hover:underline"
                      >
                        <FileText className="h-3.5 w-3.5" /> Voir le fichier résultat
                      </a>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <AddLabResultModal
        open={modalOpen}
        travelerId={travelerId}
        samples={samples}
        onClose={() => setModalOpen(false)}
        onSuccess={(created) => {
          setModalOpen(false);
          onCreated?.(created);
        }}
      />
    </section>
  );
}

export default LabAnalysisPanel;
