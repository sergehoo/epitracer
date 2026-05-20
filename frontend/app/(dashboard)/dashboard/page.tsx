'use client';

import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, ShieldCheck, Users } from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface Overview {
  travelers: { total: number; last_24h: number; by_status: Record<string, number> };
  ebola: { total: number; by_status: Record<string, number>; by_risk: Record<string, number>; last_7d: number };
  quarantines: { active: number; total: number };
  passes: { total: number; active: number; revoked: number };
  alerts: { open: number; critical_24h: number };
  generated_at: string;
}

export default function DashboardPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get<Overview>('/analytics/overview/')
      .then((r) => setData(r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);

  if (err) return <div className="card p-6 text-rose-600">{err}</div>;
  if (!data) return <div className="card p-10 animate-pulse h-40" />;

  const cards = [
    { label: 'Voyageurs enregistrés', value: data.travelers.total, sub: `+${data.travelers.last_24h} sur 24h`, icon: <Users className="h-5 w-5" /> },
    { label: 'Enquêtes Ebola', value: data.ebola.total, sub: `${data.ebola.last_7d} sur 7 jours`, icon: <Activity className="h-5 w-5" /> },
    { label: 'Quarantaines actives', value: data.quarantines.active, sub: `${data.quarantines.total} historiques`, icon: <ShieldCheck className="h-5 w-5" /> },
    { label: 'Alertes ouvertes', value: data.alerts.open, sub: `${data.alerts.critical_24h} critiques (24h)`, icon: <AlertTriangle className="h-5 w-5" /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-widest text-emerald-700 dark:text-emerald-400 font-semibold">Vue d'ensemble nationale</div>
        <h1 className="font-display text-3xl font-bold mt-1">Tableau de bord</h1>
        <p className="text-sm text-slate-500 mt-1">
          Données rafraîchies à {new Date(data.generated_at).toLocaleTimeString('fr-FR')}.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="card p-5">
            <div className="flex items-center justify-between text-slate-500 text-xs uppercase tracking-wide">
              <span>{c.label}</span>
              <span className="text-emerald-600">{c.icon}</span>
            </div>
            <div className="mt-2 font-display text-3xl font-bold">{c.value}</div>
            <div className="text-xs text-slate-500 mt-1">{c.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <article className="card p-6">
          <h3 className="font-display text-lg font-bold">Voyageurs par statut</h3>
          <ul className="mt-3 space-y-1 text-sm">
            {Object.entries(data.travelers.by_status).map(([k, v]) => (
              <li key={k} className="flex justify-between"><span className="capitalize">{k}</span><span className="font-semibold">{v}</span></li>
            ))}
          </ul>
        </article>
        <article className="card p-6">
          <h3 className="font-display text-lg font-bold">Enquêtes Ebola par niveau de risque</h3>
          <ul className="mt-3 space-y-1 text-sm">
            {Object.entries(data.ebola.by_risk).map(([k, v]) => (
              <li key={k} className="flex justify-between"><span className="capitalize">{k}</span><span className="font-semibold">{v}</span></li>
            ))}
          </ul>
        </article>
      </div>
    </div>
  );
}
