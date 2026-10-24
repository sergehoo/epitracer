'use client';

/**
 * Revues sanitaires — qualifications à l'arrivée qui demandent l'avis d'un
 * agent (symptômes sans exposition, symptôme critique, exposition sans
 * ouverture automatique). Confirmer ouvre le suivi ; écarter exige un motif.
 */

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, ClipboardCheck, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

interface Screening {
  uuid: string; traveler_public_id: string; traveler_name: string;
  disease_code: string; disease_name: string; decision: string; reasons: string[];
  review_status: 'pending' | 'confirmed' | 'dismissed' | 'not_required';
  reviewed_by_email: string | null; reviewed_at: string | null; review_note: string;
  created_at: string;
}

const FILTERS = [
  { value: 'pending', label: 'À revoir' },
  { value: 'confirmed', label: 'Confirmées' },
  { value: 'dismissed', label: 'Écartées' },
];
const fmt = (d: string | null) => (d ? new Date(d).toLocaleString('fr-FR') : '—');

export default function RevuesSanitairesPage() {
  const [status, setStatus] = useState('pending');
  const [items, setItems] = useState<Screening[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    api.get(`/admin/screenings/?review_status=${status}&page_size=100`)
      .then((r) => { setItems(r.data.results || r.data); setErr(null); })
      .catch((e) => setErr(extractApiError(e)));
  }, [status]);
  useEffect(load, [load]);

  const review = async (s: Screening, verb: 'confirm' | 'dismiss') => {
    const note = window.prompt(
      verb === 'confirm'
        ? 'Note de revue (optionnelle) — un suivi va être ouvert :'
        : 'Motif pour écarter cette qualification (obligatoire) :',
    );
    if (note === null) return;
    setBusy(s.uuid);
    try {
      await api.post(`/admin/screenings/${s.uuid}/${verb}/`, { note });
      toast.success(verb === 'confirm' ? 'Suivi ouvert.' : 'Qualification écartée.');
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold inline-flex items-center gap-2">
          <ClipboardCheck className="h-7 w-7" /> Revues sanitaires
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Réponses au questionnaire d&apos;arrivée qui nécessitent l&apos;avis d&apos;un agent avant
          tout suivi. Un symptôme isolé n&apos;ouvre jamais de suivi automatiquement.
        </p>
      </div>

      <div className="inline-flex rounded-xl border border-slate-200 dark:border-slate-700 p-1" role="tablist">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            role="tab"
            aria-selected={status === f.value}
            onClick={() => setStatus(f.value)}
            className={`px-3 py-1.5 text-xs rounded-lg font-bold ${
              status === f.value ? 'bg-ciDark text-white' : 'text-slate-600 dark:text-slate-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {err && <div className="card p-4 text-rose-600 text-sm">{err}</div>}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-4 py-3">Voyageur</th>
              <th className="px-4 py-3">Maladie</th>
              <th className="px-4 py-3">Motifs</th>
              <th className="px-4 py-3">Reçue le</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-400">Aucune qualification.</td></tr>
            )}
            {items.map((s) => (
              <tr key={s.uuid} className="border-b border-slate-100 dark:border-slate-800 align-top">
                <td className="px-4 py-3">
                  <Link href={`/voyageurs/${s.traveler_public_id}`} className="font-semibold hover:text-ciOrange">
                    {s.traveler_name || s.traveler_public_id}
                  </Link>
                  <div className="text-xs text-slate-500">{s.traveler_public_id}</div>
                </td>
                <td className="px-4 py-3">{s.disease_name}</td>
                <td className="px-4 py-3 text-xs">
                  <ul className="list-disc pl-4 space-y-0.5">{s.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
                  {s.review_note && <p className="mt-1 text-slate-500">Note : {s.review_note}</p>}
                  {s.reviewed_by_email && (
                    <p className="mt-1 text-[10px] text-slate-400">Revue par {s.reviewed_by_email} le {fmt(s.reviewed_at)}</p>
                  )}
                </td>
                <td className="px-4 py-3 text-xs">{fmt(s.created_at)}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  {s.review_status === 'pending' && (
                    <>
                      <button className="btn-primary text-xs" disabled={busy === s.uuid} onClick={() => review(s, 'confirm')}>
                        <CheckCircle2 className="h-3.5 w-3.5" /> Ouvrir le suivi
                      </button>
                      <button className="btn-outline text-xs ml-1" disabled={busy === s.uuid} onClick={() => review(s, 'dismiss')}>
                        <XCircle className="h-3.5 w-3.5" /> Écarter
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
