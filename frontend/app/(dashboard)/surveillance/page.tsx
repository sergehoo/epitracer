'use client';

import { useEffect, useState } from 'react';
import { api, extractApiError } from '@/lib/api';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { formatDateTime, STATUS_LABELS } from '@/lib/utils';
import type { RiskLevel } from '@/types/ebola';

interface InvRow {
  case_number: string;
  status: string;
  risk_level: RiskLevel;
  risk_score: number;
  entry_point_name: string;
  created_at: string;
  traveler_detail: { public_id: string; full_name?: string; last_name?: string; first_name?: string };
}

export default function SurveillancePage() {
  const [items, setItems] = useState<InvRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/ebola/investigations/?ordering=-created_at')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-widest text-emerald-700 dark:text-emerald-400 font-semibold">Surveillance Ebola</div>
        <h1 className="font-display text-3xl font-bold mt-1">Enquêtes en cours</h1>
        <p className="text-sm text-slate-500 mt-1">Tri par date de création. Filtres avancés à venir.</p>
      </div>

      {loading && <div className="card p-10 animate-pulse h-40" />}
      {err && <div className="card p-6 text-rose-600">{err}</div>}

      {!loading && !err && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 text-left">Cas</th>
                <th className="px-4 py-3 text-left">Voyageur</th>
                <th className="px-4 py-3 text-left">Risque</th>
                <th className="px-4 py-3 text-left">Statut</th>
                <th className="px-4 py-3 text-left">Point d'entrée</th>
                <th className="px-4 py-3 text-left">Créé le</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">Aucune enquête.</td></tr>
              )}
              {items.map((r) => (
                <tr key={r.case_number} className="hover:bg-slate-50 dark:hover:bg-slate-900/60">
                  <td className="px-4 py-3 font-mono">{r.case_number}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{r.traveler_detail?.full_name || `${r.traveler_detail?.last_name || ''} ${r.traveler_detail?.first_name || ''}`.trim()}</div>
                    <div className="text-xs text-slate-500">{r.traveler_detail?.public_id}</div>
                  </td>
                  <td className="px-4 py-3"><RiskBadge level={r.risk_level} score={r.risk_score} /></td>
                  <td className="px-4 py-3">{STATUS_LABELS[r.status] || r.status}</td>
                  <td className="px-4 py-3">{r.entry_point_name || '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDateTime(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
