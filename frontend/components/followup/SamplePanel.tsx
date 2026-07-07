'use client';

/**
 * SamplePanel — Workflow visuel des prélèvements biologiques.
 *
 * Étapes : Demandé (REQUESTED) → Programmé (SCHEDULED) → Effectué (COLLECTED)
 *          → Transport (IN_TRANSIT) → Reçu (RECEIVED).
 *
 * Le backend Phase 9B n'expose pas de GET liste pour les samples — on
 * accepte donc la liste en prop (le parent peut la maintenir via le retour
 * de POST /samples/ ou re-fetch d'un endpoint dédié).
 *
 * Le bouton "Demander prélèvement" ouvre RequestSampleModal.
 */

import { useMemo, useState } from 'react';
import {
  FlaskConical, Plus, Check, MapPin, Building2, Calendar, ChevronRight,
} from 'lucide-react';
import { RequestSampleModal } from './modals/RequestSampleModal';

export type SampleTransportStatus =
  | 'requested' | 'scheduled' | 'collected' | 'in_transit'
  | 'received' | 'rejected' | string;

export interface MedicalSample {
  id: number;
  uuid?: string;
  sample_code: string;
  sample_type: string;
  sample_type_label?: string;
  collected_at: string | null;
  collected_by_name?: string;
  collection_location: string;
  transport_conditions: string;
  destination_lab: string;
  transport_status: SampleTransportStatus;
  transport_status_label?: string;
  transport_departed_at?: string | null;
  received_at: string | null;
  notes: string;
  created_at?: string;
}

interface Props {
  travelerId: string;
  samples: MedicalSample[];
  onCreated?: (created: MedicalSample) => void;
}

const STATUS_ORDER: SampleTransportStatus[] = [
  'requested', 'scheduled', 'collected', 'in_transit', 'received',
];

const STATUS_META: Record<string, { label: string; short: string; tone: string }> = {
  requested: { label: 'Demandé', short: 'Demandé', tone: 'bg-sky-100 text-sky-700 border-sky-200' },
  scheduled: { label: 'Programmé', short: 'Prog.', tone: 'bg-amber-100 text-amber-700 border-amber-200' },
  collected: { label: 'Effectué', short: 'Effectué', tone: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  in_transit: { label: 'En transit', short: 'Transit', tone: 'bg-violet-100 text-violet-700 border-violet-200' },
  received: { label: 'Reçu au labo', short: 'Reçu', tone: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  rejected: { label: 'Rejeté', short: 'Rejeté', tone: 'bg-rose-100 text-rose-700 border-rose-200' },
};

function formatDate(d: string | null | undefined): string {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return d;
  }
}

function statusIndex(s: SampleTransportStatus): number {
  const i = STATUS_ORDER.indexOf(s);
  return i === -1 ? 0 : i;
}

function SampleWorkflowSteps({ status }: { status: SampleTransportStatus }) {
  const currentIdx = statusIndex(status);
  return (
    <div className="flex items-center gap-1 overflow-x-auto">
      {STATUS_ORDER.map((s, idx) => {
        const meta = STATUS_META[s];
        const active = idx <= currentIdx;
        const isCurrent = idx === currentIdx;
        return (
          <div key={s} className="flex items-center gap-1 shrink-0">
            <div
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-bold ${
                active ? meta.tone : 'bg-slate-50 text-slate-400 border-slate-200'
              } ${isCurrent ? 'ring-2 ring-offset-1 ring-emerald-300' : ''}`}
            >
              {active && idx < currentIdx && <Check className="h-3 w-3" />}
              {meta.short}
            </div>
            {idx < STATUS_ORDER.length - 1 && (
              <ChevronRight className="h-3 w-3 text-slate-300" />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function SamplePanel({ travelerId, samples, onCreated }: Props) {
  const [modalOpen, setModalOpen] = useState(false);

  const sorted = useMemo(
    () => [...samples].sort((a, b) => {
      const da = new Date(a.created_at || a.collected_at || 0).getTime();
      const db = new Date(b.created_at || b.collected_at || 0).getTime();
      return db - da;
    }),
    [samples],
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-sky-600" />
            <h2 className="font-display text-lg font-black text-ciDark">Prélèvements</h2>
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {samples.length} prélèvement(s) au dossier.
          </div>
        </div>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 text-white px-3 py-1.5 text-xs font-bold hover:bg-emerald-700"
        >
          <Plus className="h-3.5 w-3.5" /> Demander prélèvement
        </button>
      </header>

      {sorted.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-sm">
          Aucun prélèvement biologique pour ce voyageur.
        </div>
      ) : (
        <ul className="space-y-3">
          {sorted.map((s) => {
            const meta = STATUS_META[s.transport_status] ?? STATUS_META.requested;
            return (
              <li key={s.id} className="rounded-xl border border-slate-200 p-3">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-slate-500">{s.sample_code}</span>
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[10px] font-bold border border-slate-200">
                        {s.sample_type_label || s.sample_type}
                      </span>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${meta.tone}`}>
                        {s.transport_status_label || meta.label}
                      </span>
                    </div>
                    <div className="mt-1.5 text-xs text-slate-600 flex flex-wrap gap-x-3 gap-y-1">
                      {s.collection_location && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="h-3 w-3" /> {s.collection_location}
                        </span>
                      )}
                      {s.destination_lab && (
                        <span className="inline-flex items-center gap-1">
                          <Building2 className="h-3 w-3" /> {s.destination_lab}
                        </span>
                      )}
                      {s.collected_at && (
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3 w-3" /> Effectué : {formatDate(s.collected_at)}
                        </span>
                      )}
                      {s.received_at && (
                        <span className="inline-flex items-center gap-1 text-emerald-700">
                          <Check className="h-3 w-3" /> Reçu : {formatDate(s.received_at)}
                        </span>
                      )}
                    </div>
                    {s.notes && (
                      <p className="mt-1.5 text-xs text-slate-500 italic">{s.notes}</p>
                    )}
                  </div>
                </div>
                <div className="mt-3">
                  <SampleWorkflowSteps status={s.transport_status} />
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <RequestSampleModal
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

export default SamplePanel;
