'use client';

/**
 * AddLabResultModal — Création d'un LabAnalysis pour un MedicalSample existant.
 *
 * POST /api/v1/admin/followups/{travelerId}/lab-results/
 *   { sample_id, lab_name, test_type, status, result, notes }
 *
 * Si un fichier est joint, on bascule en multipart/form-data (l'intercepteur
 * Axios retire automatiquement Content-Type pour laisser le browser fixer la
 * boundary).
 */

import { useEffect, useState } from 'react';
import { X, Loader2, TestTube2, FileUp } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import type { LabAnalysis } from '../LabAnalysisPanel';
import type { MedicalSample } from '../SamplePanel';

const STATUSES: { value: string; label: string }[] = [
  { value: 'pending', label: 'En attente' },
  { value: 'received', label: 'Reçu' },
  { value: 'in_analysis', label: 'En analyse' },
  { value: 'result_available', label: 'Résultat disponible' },
  { value: 'validated', label: 'Validé' },
];

const RESULTS: { value: string; label: string }[] = [
  { value: '', label: '— (aucun)' },
  { value: 'negative', label: 'Négatif' },
  { value: 'positive', label: 'Positif' },
  { value: 'indeterminate', label: 'Indéterminé' },
  { value: 'retest', label: 'À refaire' },
];

interface Props {
  open: boolean;
  travelerId: string;
  samples: MedicalSample[];
  onClose: () => void;
  onSuccess?: (created: LabAnalysis) => void;
}

export function AddLabResultModal({ open, travelerId, samples, onClose, onSuccess }: Props) {
  const [sampleId, setSampleId] = useState<number | ''>('');
  const [labName, setLabName] = useState<string>('');
  const [testType, setTestType] = useState<string>('');
  const [status, setStatus] = useState<string>('result_available');
  const [result, setResult] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      const firstId = samples[0]?.id;
      setSampleId(typeof firstId === 'number' ? firstId : '');
      setLabName('');
      setTestType('');
      setStatus('result_available');
      setResult('');
      setNotes('');
      setFile(null);
      setSubmitting(false);
    }
  }, [open, samples]);

  if (!open) return null;

  const submit = async () => {
    if (!sampleId) {
      toast.error('Prélèvement requis.');
      return;
    }
    if (!labName.trim() || !testType.trim()) {
      toast.error('Laboratoire et type de test requis.');
      return;
    }

    setSubmitting(true);
    try {
      let payload: FormData | Record<string, unknown>;
      if (file) {
        const fd = new FormData();
        fd.append('sample_id', String(sampleId));
        fd.append('lab_name', labName.trim());
        fd.append('test_type', testType.trim());
        fd.append('status', status);
        fd.append('result', result);
        fd.append('notes', notes.trim());
        fd.append('result_file', file);
        payload = fd;
      } else {
        payload = {
          sample_id: sampleId,
          lab_name: labName.trim(),
          test_type: testType.trim(),
          status,
          result,
          notes: notes.trim(),
        };
      }

      const r = await api.post<LabAnalysis>(
        `/admin/followups/${travelerId}/lab-results/`,
        payload,
      );
      toast.success('Résultat enregistré.');
      onSuccess?.(r.data);
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mt-12 mb-8"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-display text-lg font-bold flex items-center gap-2">
            <TestTube2 className="h-5 w-5 text-violet-600" /> Ajouter un résultat d'analyse
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="text-slate-400 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Prélèvement rattaché
            </label>
            <select
              value={sampleId}
              onChange={(e) => setSampleId(Number(e.target.value) || '')}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            >
              {samples.length === 0 ? (
                <option value="">Aucun prélèvement disponible</option>
              ) : (
                samples.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.sample_code} — {s.sample_type_label || s.sample_type}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
                Nom du laboratoire
              </label>
              <input
                type="text"
                value={labName}
                onChange={(e) => setLabName(e.target.value)}
                maxLength={200}
                placeholder="Ex. Institut Pasteur CI"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
                Type de test
              </label>
              <input
                type="text"
                value={testType}
                onChange={(e) => setTestType(e.target.value)}
                maxLength={80}
                placeholder="Ex. PCR Ebola"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
                Statut
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
              >
                {STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
                Résultat
              </label>
              <select
                value={result}
                onChange={(e) => setResult(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
              >
                {RESULTS.map((r) => (
                  <option key={r.value || 'empty'} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Fichier résultat (optionnel — PDF/image)
            </label>
            <label className="flex items-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-500 cursor-pointer hover:bg-slate-50">
              <FileUp className="h-4 w-4" />
              <span className="truncate">
                {file ? file.name : 'Choisir un fichier…'}
              </span>
              <input
                type="file"
                accept="application/pdf,image/png,image/jpeg"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="hidden"
              />
            </label>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Notes (optionnel)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="Observations cliniques, valeurs hors normes…"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm resize-none focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting || samples.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 text-white px-4 py-2 text-sm font-bold hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Enregistrement…</>
            ) : (
              'Enregistrer le résultat'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AddLabResultModal;
