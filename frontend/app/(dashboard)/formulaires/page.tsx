'use client';

import { useEffect, useState } from 'react';
import { FormInput } from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface DForm {
  id: number; uuid: string; code: string; title: string;
  version: number; is_active: boolean; is_default: boolean;
  disease_code: string;
}

export default function FormulairesPage() {
  const [items, setItems] = useState<DForm[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.get('/forms/definitions/?page_size=50')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Formulaires d'enquête</h1>
        <p className="text-sm text-slate-500 mt-1">Versions actives par maladie. Modification visuelle prévue dans une prochaine itération.</p>
      </div>
      {err && <div className="card p-6 text-rose-600">{err}</div>}
      <div className="grid md:grid-cols-2 gap-4">
        {items.map((f) => (
          <article key={f.uuid} className="card p-5 flex items-start gap-4">
            <div className="h-10 w-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 grid place-items-center text-emerald-600"><FormInput className="h-5 w-5" /></div>
            <div className="flex-1">
              <div className="font-display text-base font-bold">{f.title}</div>
              <div className="text-xs text-slate-500 mt-1">
                {f.disease_code} · {f.code} · v{f.version}
              </div>
              <div className="mt-2 flex gap-2">
                <span className={f.is_active ? 'badge-low' : 'badge-high'}>{f.is_active ? 'Actif' : 'Inactif'}</span>
                {f.is_default && <span className="badge-low">Par défaut</span>}
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
