'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronRight, Siren } from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface Alert {
  id: number;
  uuid: string;
  code: string;
  title: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  status: string;
  disease_code?: string | null;
  entry_point_name?: string | null;
  created_at: string;
}

const SEV: Record<string, string> = {
  info: 'badge-low',
  low: 'badge-low',
  medium: 'badge-moderate',
  high: 'badge-high',
  critical: 'badge-critical',
};

export default function AlertesPage() {
  const [items, setItems] = useState<Alert[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/surveillance/alerts/?ordering=-created_at')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-widest text-rose-600 font-semibold">Alertes sanitaires</div>
        <h1 className="font-display text-3xl font-bold mt-1">Alertes en cours</h1>
      </div>
      {loading && <div className="card p-10 animate-pulse h-40" />}
      {err && <div className="card p-6 text-rose-600">{err}</div>}
      <div className="space-y-3">
        {items.length === 0 && !loading && (
          <div className="card p-10 text-center text-slate-400">Aucune alerte active.</div>
        )}
        {items.map((a) => (
          <Link
            key={a.uuid}
            href={`/alertes/${a.uuid}`}
            className="card p-5 flex items-start justify-between gap-4 hover:shadow-lg transition group"
          >
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-xl bg-rose-50 dark:bg-rose-950/40 grid place-items-center text-rose-600"><Siren className="h-5 w-5" /></div>
              <div>
                <div className="font-display text-lg font-bold group-hover:text-ciOrange transition">{a.title}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {a.code} · {a.disease_code || '—'} · {a.entry_point_name || '—'}
                </div>
                <div className="text-xs text-slate-400">{formatDateTime(a.created_at)}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={SEV[a.severity] || 'badge-low'}>{a.severity.toUpperCase()}</span>
              <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-ciOrange transition" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
