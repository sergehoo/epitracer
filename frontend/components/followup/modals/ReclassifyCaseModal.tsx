'use client';

/**
 * ReclassifyCaseModal — Reclassification clinique d'un cas (Phase 9F).
 *
 * POST /api/v1/admin/followups/{travelerId}/classify/
 *   { classification, reason }
 *
 * Le backend crée une nouvelle entrée CaseClassification (is_current=true)
 * et marque les précédentes comme historiques. Une FollowUpAction de type
 * "case_reclassified" est aussi créée automatiquement côté service.
 */

import { useEffect, useState } from 'react';
import { X, Loader2, Tag } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

const CLASSIFICATIONS: { value: string; label: string; tone: string }[] = [
  { value: 'not_suspect', label: 'Non suspect', tone: 'text-slate-700' },
  { value: 'under_surveillance', label: 'Sous surveillance', tone: 'text-sky-700' },
  { value: 'suspect', label: 'Suspect', tone: 'text-amber-700' },
  { value: 'probable', label: 'Probable', tone: 'text-orange-700' },
  { value: 'confirmed', label: 'Confirmé', tone: 'text-rose-700' },
  { value: 'excluded', label: 'Exclu', tone: 'text-emerald-700' },
  { value: 'recovered', label: 'Guéri', tone: 'text-emerald-700' },
  { value: 'closed', label: 'Clos', tone: 'text-slate-500' },
];

interface Props {
  open: boolean;
  travelerId: string;
  currentClassification?: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function ReclassifyCaseModal({
  open, travelerId, currentClassification, onClose, onSuccess,
}: Props) {
  const [classification, setClassification] = useState<string>('suspect');
  const [reason, setReason] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setClassification(currentClassification || 'suspect');
      setReason('');
      setSubmitting(false);
    }
  }, [open, currentClassification]);

  if (!open) return null;

  const submit = async () => {
    if (!reason.trim()) {
      toast.error('Un motif de reclassification est requis.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/admin/followups/${travelerId}/classify/`, {
        classification,
        reason: reason.trim(),
      });
      toast.success('Cas reclassifié.');
      onSuccess?.();
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
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md mt-16"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-display text-lg font-bold flex items-center gap-2">
            <Tag className="h-5 w-5 text-amber-600" /> Reclasser le cas
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
              Nouvelle classification
            </label>
            <select
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-amber-500 focus:ring-amber-500 outline-none"
            >
              {CLASSIFICATIONS.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Motif (obligatoire)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="Ex. Résultat PCR positif confirmé, ou symptômes critiques apparus."
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm resize-none focus:border-amber-500 focus:ring-amber-500 outline-none"
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
            disabled={submitting || !reason.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-amber-600 text-white px-4 py-2 text-sm font-bold hover:bg-amber-700 disabled:opacity-50"
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Reclassification…</>
            ) : (
              'Reclasser'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReclassifyCaseModal;
