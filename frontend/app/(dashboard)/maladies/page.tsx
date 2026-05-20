'use client';

import { useEffect, useState } from 'react';
import { Stethoscope } from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface Disease {
  id: number; uuid: string; code: string; name: string;
  severity: string; color: string;
  surveillance_days: number; quarantine_days: number;
  is_active: boolean; requires_quarantine: boolean; requires_pass: boolean;
}

export default function MaladiesPage() {
  const [items, setItems] = useState<Disease[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.get('/diseases/?page_size=50')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Maladies surveillées</h1>
        <p className="text-sm text-slate-500 mt-1">Configuration centralisée des maladies dans le moteur multi-maladies.</p>
      </div>
      {err && <div className="card p-6 text-rose-600">{err}</div>}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((d) => (
          <article key={d.uuid} className="card p-5 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 opacity-10 rounded-full" style={{ backgroundColor: d.color, filter: 'blur(30px)' }} />
            <div className="flex items-start justify-between">
              <div className="h-10 w-10 rounded-xl grid place-items-center text-white" style={{ backgroundColor: d.color }}>
                <Stethoscope className="h-5 w-5" />
              </div>
              <span className={d.is_active ? 'badge-low' : 'badge-high'}>{d.is_active ? 'Active' : 'Inactive'}</span>
            </div>
            <div className="mt-3 font-display text-lg font-bold">{d.name}</div>
            <div className="text-xs text-slate-500">{d.code} · gravité {d.severity}</div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div><dt className="text-slate-500">Surveillance</dt><dd className="font-semibold">{d.surveillance_days} jours</dd></div>
              <div><dt className="text-slate-500">Quarantaine</dt><dd className="font-semibold">{d.quarantine_days} jours</dd></div>
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}
