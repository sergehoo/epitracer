'use client';

/**
 * CloseFollowupModal — Clôture du suivi médical.
 *
 * POST /api/v1/admin/followups/{travelerId}/close/
 *   { closure_reason, final_status, notes }
 *
 * Action irréversible côté UX — confirme avant POST.
 */

import { useEffect, useState } from 'react';
import { X, Loader2, ShieldOff, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

interface CloseResponse {
  ok: boolean;
  status: string;
  closure_reason: string;
  actual_end_on: string | null;
}

const CLOSURE_REASONS: { value: string; label: string }[] = [
  { value: 'auto_completed', label: 'Suivi terminé automatiquement' },
  { value: 'manual_close', label: 'Clôture manuelle' },
  { value: 'escalated', label: 'Escaladé (orienté hospitalisation)' },
  { value: 'lost_to_followup', label: 'Perdu de vue' },
];

const FINAL_STATUSES: { value: string; label: string }[] = [
  { value: 'completed', label: 'Terminé' },
  { value: 'cancelled', label: 'Annulé' },
];

interface Props {
  open: boolean;
  travelerId: string;
  travelerName?: string;
  onClose: () => void;
  onSuccess?: (response: CloseResponse) => void;
}

export function CloseFollowupModal({
  open,
  travelerId,
  travelerName,
  onClose,
  onSuccess,
}: Props) {
  const [closureReason, setClosureReason] = useState<string>('manual_close');
  const [finalStatus, setFinalStatus] = useState<string>('completed');
  const [notes, setNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setClosureReason('manual_close');
      setFinalStatus('completed');
      setNotes('');
      setSubmitting(false);
    }
  }, [open]);

  if (!open) return null;

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post<CloseResponse>(
        `/admin/followups/${travelerId}/close/`,
        {
          closure_reason: closureReason,
          final_status: finalStatus,
          notes: notes.trim(),
        },
      );
      toast.success('Suivi clôturé.');
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
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md mt-12 mb-8"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-display text-lg font-bold flex items-center gap-2">
            <ShieldOff className="h-5 w-5 text-rose-600" /> Clôturer le suivi
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
          <div className="rounded-xl bg-amber-50 border border-amber-200 px-3 py-2.5 text-xs text-amber-800 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Action sensible</p>
              <p className="mt-0.5 text-amber-700">
                La clôture arrête définitivement le suivi quotidien
                {travelerName && <> du voyageur <strong>{travelerName}</strong></>}.
                Les données restent consultables pour audit.
              </p>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Motif de clôture
            </label>
            <select
              value={closureReason}
              onChange={(e) => setClosureReason(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            >
              {CLOSURE_REASONS.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Statut final
            </label>
            <select
              value={finalStatus}
              onChange={(e) => setFinalStatus(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            >
              {FINAL_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Notes (recommandé)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="Conclusion, orientations données au voyageur, suite à donner…"
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
            className="inline-flex items-center gap-2 rounded-lg bg-rose-600 text-white px-4 py-2 text-sm font-bold hover:bg-rose-700 disabled:opacity-50"
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Clôture en cours…</>
            ) : (
              'Clôturer le suivi'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CloseFollowupModal;
