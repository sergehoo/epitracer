'use client';

import { useEffect, useState } from 'react';
import { api, extractApiError } from '@/lib/api';

interface EP { id: number; code: string; name: string; type: string; iata_code: string; city: string; country_name?: string; is_active: boolean }

export default function PointsEntreePage() {
  const [items, setItems] = useState<EP[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get('/geo/entry-points/?ordering=name&page_size=100')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Points d'entrée</h1>
        <p className="text-sm text-slate-500 mt-1">Aéroports, ports maritimes et frontières terrestres sous surveillance.</p>
      </div>
      {loading && <div className="card p-10 animate-pulse h-40" />}
      {err && <div className="card p-6 text-rose-600">{err}</div>}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((ep) => (
          <article key={ep.id} className="card p-5">
            <div className="text-xs uppercase tracking-wide text-emerald-700 font-semibold">{ep.type}</div>
            <div className="font-display text-lg font-bold mt-1">{ep.name}</div>
            <div className="text-sm text-slate-500 mt-1">{ep.city} · {ep.country_name || '—'} {ep.iata_code && <span>· {ep.iata_code}</span>}</div>
            <span className={`mt-3 inline-flex ${ep.is_active ? 'badge-low' : 'badge-high'}`}>
              {ep.is_active ? 'Actif' : 'Inactif'}
            </span>
          </article>
        ))}
      </div>
    </div>
  );
}
