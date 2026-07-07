'use client';

/**
 * AddSymptomModal — Saisie d'un MedicalSymptomReport par l'agent.
 *
 * POST /api/v1/admin/followups/{travelerId}/symptoms/
 *   { symptom_code, symptom_label, severity, onset_date, notes, source }
 *
 * Le backend détermine `is_critical` automatiquement via le protocole de la
 * maladie (DiseaseFollowupProtocol.critical_symptoms).
 */

import { useEffect, useState } from 'react';
import { X, Loader2, Activity } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import type { SymptomReport } from '../SymptomPanel';

interface SymptomChoice {
  code: string;
  label: string;
}

const SYMPTOMS: SymptomChoice[] = [
  { code: 'fever', label: 'Fièvre' },
  { code: 'fatigue', label: 'Fatigue intense' },
  { code: 'headache', label: 'Céphalées' },
  { code: 'sore_throat', label: 'Mal de gorge' },
  { code: 'abdominal_pain', label: 'Douleurs abdominales' },
  { code: 'diarrhea', label: 'Diarrhée' },
  { code: 'vomiting', label: 'Vomissements' },
  { code: 'unexplained_bleeding', label: 'Saignements inexpliqués' },
  { code: 'conjunctivitis', label: 'Conjonctivite hémorragique' },
  { code: 'chest_pain', label: 'Douleurs thoraciques' },
];

const SEVERITIES: { value: 'mild' | 'moderate' | 'severe' | 'critical'; label: string; tone: string }[] = [
  { value: 'mild', label: 'Légère', tone: 'border-emerald-300 text-emerald-700' },
  { value: 'moderate', label: 'Modérée', tone: 'border-amber-300 text-amber-700' },
  { value: 'severe', label: 'Sévère', tone: 'border-orange-300 text-orange-700' },
  { value: 'critical', label: 'Critique', tone: 'border-rose-300 text-rose-700' },
];

interface Props {
  open: boolean;
  travelerId: string;
  onClose: () => void;
  onSuccess?: (created: SymptomReport) => void;
}

function todayISO(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export function AddSymptomModal({ open, travelerId, onClose, onSuccess }: Props) {
  const [code, setCode] = useState<string>(SYMPTOMS[0].code);
  const [severity, setSeverity] = useState<'mild' | 'moderate' | 'severe' | 'critical'>('mild');
  const [onsetDate, setOnsetDate] = useState<string>(todayISO());
  const [notes, setNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setCode(SYMPTOMS[0].code);
      setSeverity('mild');
      setOnsetDate(todayISO());
      setNotes('');
      setSubmitting(false);
    }
  }, [open]);

  if (!open) return null;

  const submit = async () => {
    const choice = SYMPTOMS.find((s) => s.code === code);
    if (!choice) {
      toast.error('Symptôme invalide.');
      return;
    }
    if (!onsetDate) {
      toast.error('Date de début requise.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        symptom_code: choice.code,
        symptom_label: choice.label,
        severity,
        onset_date: onsetDate,
        notes: notes.trim(),
        source: 'admin',
      };
      const r = await api.post<SymptomReport>(
        `/admin/followups/${travelerId}/symptoms/`,
        payload,
      );
      toast.success('Symptôme enregistré.');
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
            <Activity className="h-5 w-5 text-rose-600" /> Déclarer un symptôme
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="text-slate-400 hover:text-slate-700 text-xl"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Symptôme
            </label>
            <select
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            >
              {SYMPTOMS.map((s) => (
                <option key={s.code} value={s.code}>{s.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Sévérité
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {SEVERITIES.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => setSeverity(s.value)}
                  className={`rounded-lg border px-3 py-2 text-xs font-bold transition ${
                    severity === s.value
                      ? `${s.tone} bg-white ring-2 ring-offset-1 ring-emerald-400`
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Date de début
            </label>
            <input
              type="date"
              value={onsetDate}
              onChange={(e) => setOnsetDate(e.target.value)}
              max={todayISO()}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            />
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
              placeholder="Contexte, évolution, signes associés…"
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
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 text-white px-4 py-2 text-sm font-bold hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Enregistrement…</>
            ) : (
              'Enregistrer'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AddSymptomModal;
