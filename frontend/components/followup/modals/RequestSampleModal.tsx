'use client';

/**
 * RequestSampleModal — Demande d'un prélèvement biologique.
 *
 * POST /api/v1/admin/followups/{travelerId}/samples/
 *   { sample_type, collection_location, destination_lab,
 *     transport_conditions, notes }
 *
 * Le sample_code est généré côté serveur (via services_api.generate_sample_code).
 */

import { useEffect, useState } from 'react';
import { X, Loader2, FlaskConical } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import type { MedicalSample } from '../SamplePanel';

const SAMPLE_TYPES: { value: string; label: string }[] = [
  { value: 'blood', label: 'Sang' },
  { value: 'saliva', label: 'Salive' },
  { value: 'nasopharyngeal', label: 'Nasopharyngé' },
  { value: 'urine', label: 'Urine' },
  { value: 'stool', label: 'Selles' },
  { value: 'other', label: 'Autre' },
];

interface Props {
  open: boolean;
  travelerId: string;
  onClose: () => void;
  onSuccess?: (created: MedicalSample) => void;
}

export function RequestSampleModal({ open, travelerId, onClose, onSuccess }: Props) {
  const [sampleType, setSampleType] = useState<string>('blood');
  const [collectionLocation, setCollectionLocation] = useState<string>('');
  const [destinationLab, setDestinationLab] = useState<string>('');
  const [transportConditions, setTransportConditions] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setSampleType('blood');
      setCollectionLocation('');
      setDestinationLab('');
      setTransportConditions('');
      setNotes('');
      setSubmitting(false);
    }
  }, [open]);

  if (!open) return null;

  const submit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        sample_type: sampleType,
        collection_location: collectionLocation.trim(),
        destination_lab: destinationLab.trim(),
        transport_conditions: transportConditions.trim(),
        notes: notes.trim(),
      };
      const r = await api.post<MedicalSample>(
        `/admin/followups/${travelerId}/samples/`,
        payload,
      );
      toast.success(`Prélèvement demandé · ${r.data?.sample_code ?? ''}`);
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
            <FlaskConical className="h-5 w-5 text-sky-600" /> Demander un prélèvement
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
              Type de prélèvement
            </label>
            <select
              value={sampleType}
              onChange={(e) => setSampleType(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            >
              {SAMPLE_TYPES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Lieu de prélèvement
            </label>
            <input
              type="text"
              value={collectionLocation}
              onChange={(e) => setCollectionLocation(e.target.value)}
              maxLength={200}
              placeholder="Ex. CHU Treichville, Bloc B"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Laboratoire de destination
            </label>
            <input
              type="text"
              value={destinationLab}
              onChange={(e) => setDestinationLab(e.target.value)}
              maxLength={200}
              placeholder="Ex. Institut Pasteur de CI"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-emerald-500 outline-none"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1 block">
              Conditions de transport (optionnel)
            </label>
            <input
              type="text"
              value={transportConditions}
              onChange={(e) => setTransportConditions(e.target.value)}
              placeholder="Ex. Chaîne du froid +4°C, triple emballage P650"
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
              placeholder="Contexte clinique, examens à effectuer…"
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
              <><Loader2 className="h-4 w-4 animate-spin" /> Création…</>
            ) : (
              'Demander le prélèvement'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default RequestSampleModal;
