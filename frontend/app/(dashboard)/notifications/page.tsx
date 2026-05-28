'use client';

/**
 * /dashboard/notifications — Historique global des notifications envoyées.
 *
 * KPIs en haut + filtres canal/statut/provider + liste paginée.
 */

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Bell, CheckCircle2, Send, Smartphone, XCircle, Clock,
  MessageCircle, Filter, Search, RefreshCcw,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { NotificationHistory } from '@/components/notifications/NotificationHistory';

interface NotifSummary {
  count: number;
  results: any[];
}

const STATUS_OPTS = [
  { value: '', label: 'Tous' },
  { value: 'sent', label: 'Envoyés' },
  { value: 'delivered', label: 'Délivrés' },
  { value: 'pending', label: 'En attente' },
  { value: 'queued', label: 'En file' },
  { value: 'failed', label: 'Échec' },
  { value: 'cancelled', label: 'Annulés' },
];

const CHANNEL_OPTS = [
  { value: '', label: 'Tous canaux' },
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'email', label: 'Email' },
  { value: 'push', label: 'Push' },
];

export default function NotificationsPage() {
  const [channel, setChannel] = useState<'sms' | 'whatsapp' | 'email' | 'push' | ''>('');
  const [kpis, setKpis] = useState<Record<string, number>>({});

  const loadKpis = () => {
    Promise.all(
      STATUS_OPTS.filter((s) => s.value).map((s) =>
        api.get(`/notifications/?status=${s.value}&page_size=1`)
          .then((r) => [s.value, r.data.count ?? (r.data.results || r.data).length] as const)
          .catch(() => [s.value, 0] as const)
      )
    ).then((entries) => setKpis(Object.fromEntries(entries)));
  };
  useEffect(() => { loadKpis(); }, []);

  return (
    <div className="space-y-6">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Communication voyageurs
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Notifications & messages
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Historique complet des SMS / WhatsApp / emails envoyés aux voyageurs.
          Numéros ivoiriens → Orange CI, autres → Twilio (règle automatique).
        </p>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Kpi label="Délivrés" value={kpis.delivered ?? 0} icon={<CheckCircle2 className="h-4 w-4" />} tone="emerald" />
        <Kpi label="Envoyés" value={kpis.sent ?? 0} icon={<Send className="h-4 w-4" />} tone="sky" />
        <Kpi label="En file" value={kpis.queued ?? 0} icon={<Clock className="h-4 w-4" />} tone="amber" />
        <Kpi label="En attente" value={kpis.pending ?? 0} icon={<Clock className="h-4 w-4" />} tone="slate" />
        <Kpi label="Échec" value={kpis.failed ?? 0} icon={<XCircle className="h-4 w-4" />} tone="rose" />
        <Kpi label="Annulés" value={kpis.cancelled ?? 0} icon={<XCircle className="h-4 w-4" />} tone="slate" />
      </div>

      {/* Filtres canal */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Canal</label>
          <div className="flex flex-wrap gap-1.5">
            {CHANNEL_OPTS.map((c) => (
              <button
                key={c.value}
                onClick={() => setChannel(c.value as any)}
                className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold border transition ${
                  channel === c.value
                    ? 'bg-ciOrange text-white border-ciOrange'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={loadKpis}
          className="ml-auto inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          <RefreshCcw className="h-3 w-3" /> Actualiser
        </button>
      </div>

      {/* Liste */}
      <NotificationHistory channel={channel || undefined} pageSize={50} />
    </div>
  );
}

function Kpi({
  label, value, icon, tone,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: 'emerald' | 'sky' | 'amber' | 'rose' | 'slate';
}) {
  const tones = {
    emerald: 'from-emerald-50 to-teal-50 text-emerald-700 border-emerald-200/60',
    sky: 'from-sky-50 to-blue-50 text-sky-700 border-sky-200/60',
    amber: 'from-amber-50 to-yellow-50 text-amber-700 border-amber-200/60',
    rose: 'from-rose-50 to-pink-50 text-rose-700 border-rose-200/60',
    slate: 'from-slate-50 to-gray-50 text-slate-700 border-slate-200/60',
  };
  return (
    <div className={`p-3 rounded-2xl border bg-gradient-to-br ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide font-bold opacity-80">{label}</span>
        <span className="opacity-50">{icon}</span>
      </div>
      <div className="mt-1 font-display text-2xl font-black">{value}</div>
    </div>
  );
}
