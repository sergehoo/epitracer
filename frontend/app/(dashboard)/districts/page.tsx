'use client';

import { useEffect, useState } from 'react';
import { api, extractApiError } from '@/lib/api';

interface Zone { id: number; code: string; name: string; level: string; risk_level: string; population?: number | null }

export default function DistrictsPage() {
  const [items, setItems] = useState<Zone[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.get('/geo/zones/?level=district&page_size=200')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Districts sanitaires</h1>
        <p className="text-sm text-slate-500 mt-1">Zones administratives sous la responsabilité des districts.</p>
      </div>
      {err && <div className="card p-6 text-rose-600">{err}</div>}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
            <tr><th className="px-4 py-3 text-left">Code</th><th className="text-left">Nom</th><th className="text-left">Niveau</th><th className="text-left">Risque</th><th className="text-left">Population</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.length === 0 && <tr><td colSpan={5} className="px-4 py-10 text-center text-slate-400">Aucun district.</td></tr>}
            {items.map((z) => (
              <tr key={z.id}><td className="px-4 py-3 font-mono">{z.code}</td><td className="px-4 py-3">{z.name}</td><td className="px-4 py-3">{z.level}</td><td className="px-4 py-3 capitalize">{z.risk_level}</td><td className="px-4 py-3">{z.population ?? '—'}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
