'use client';

/**
 * NationalOverview — bandeau premium en haut du /dashboard.
 *
 * Branché sur /api/v1/analytics/national/ qui retourne tout en 1 appel
 * (KPIs + timeline 14j + top points + alertes). Auto-refresh toutes les
 * 60s. Animations Framer Motion sur les KPIs.
 *
 * Pensé pour s'INTÉGRER au-dessus du dashboard existant, pas pour
 * remplacer ses charts. L'idée est d'ajouter de la dynamique et un
 * accès rapide aux chiffres-clés sans casser ce qui marche déjà.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Activity, AlertTriangle, Bell, HeartPulse, RefreshCcw, ShieldCheck,
  TrendingUp, Users,
} from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer, Tooltip } from 'recharts';
import { api } from '@/lib/api';

interface NationalData {
  kpis: {
    travelers_today: number;
    travelers_total: number;
    active_followups: number;
    passes_issued: number;
    passes_active: number;
    alerts_open: number;
    alerts_critical_24h: number;
    high_risk_travelers: number;
    checkins_today: number;
    checkins_with_symptoms_today: number;
    checkins_missed_48h: number;
  };
  timeline: { date: string; travelers: number }[];
  top_entry_points: { entry_point__name: string; entry_point__code: string; count: number }[];
  top_origins: { country__code: string; country__name: string; count: number }[];
  statuses: Record<string, number>;
  risk_levels: Record<string, number>;
  recent_alerts: {
    id: string; code: string; title: string;
    severity: string; status: string; created_at: string;
  }[];
  generated_at: string;
}

const SEV_STYLES: Record<string, string> = {
  CRITICAL: 'bg-rose-100 text-rose-700 border-rose-200',
  HIGH: 'bg-orange-100 text-orange-700 border-orange-200',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
  LOW: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  INFO: 'bg-slate-100 text-slate-700 border-slate-200',
};

export function NationalOverview() {
  const [data, setData] = useState<NationalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<NationalData>('/analytics/national/');
      setData(data);
      setLastFetch(new Date());
    } catch {
      /* silencieux — le dashboard existant continue de marcher */
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-refresh 60s
  useEffect(() => {
    load();
    const id = window.setInterval(load, 60_000);
    return () => window.clearInterval(id);
  }, [load]);

  const k = data?.kpis;

  // Calcul tendance dernière 7 vs précédente
  const trend = useMemo(() => {
    if (!data?.timeline || data.timeline.length < 14) return null;
    const last7 = data.timeline.slice(-7).reduce((s, p) => s + p.travelers, 0);
    const prev7 = data.timeline.slice(0, 7).reduce((s, p) => s + p.travelers, 0);
    if (prev7 === 0) return null;
    return ((last7 - prev7) / prev7) * 100;
  }, [data]);

  return (
    <section className="mb-8">
      {/* En-tête + bouton refresh */}
      <header className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Vue nationale temps réel
          </span>
          <h2 className="font-display text-xl md:text-2xl font-black text-ciDark dark:text-emerald-100 mt-1">
            Tableau de bord opérationnel
          </h2>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {lastFetch && (
            <span>Actualisé à {lastFetch.toLocaleTimeString('fr-FR')}</span>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            aria-label="Actualiser"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
        </div>
      </header>

      {/* Grille KPIs animés */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <KpiCard
          icon={<Users className="h-4 w-4" />}
          label="Arrivées aujourd'hui"
          value={k?.travelers_today}
          tone="orange"
          delay={0}
        />
        <KpiCard
          icon={<HeartPulse className="h-4 w-4" />}
          label="Suivi actif"
          value={k?.active_followups}
          tone="emerald"
          delay={0.05}
        />
        <KpiCard
          icon={<ShieldCheck className="h-4 w-4" />}
          label="Pass délivrés"
          value={k?.passes_issued}
          sub={`${k?.passes_active ?? 0} actifs`}
          tone="emerald"
          delay={0.1}
        />
        <KpiCard
          icon={<Bell className="h-4 w-4" />}
          label="Check-ins du jour"
          value={k?.checkins_today}
          sub={k?.checkins_with_symptoms_today ? `${k.checkins_with_symptoms_today} avec symptôme` : 'aucun symptôme'}
          tone={k && k.checkins_with_symptoms_today > 0 ? 'amber' : 'emerald'}
          delay={0.15}
        />
        <KpiCard
          icon={<AlertTriangle className="h-4 w-4" />}
          label="Alertes ouvertes"
          value={k?.alerts_open}
          sub={k?.alerts_critical_24h ? `${k.alerts_critical_24h} critique(s) 24h` : 'aucune critique 24h'}
          tone={k && k.alerts_open > 0 ? 'rose' : 'slate'}
          delay={0.2}
        />
        <KpiCard
          icon={<Activity className="h-4 w-4" />}
          label="Manqués > 48h"
          value={k?.checkins_missed_48h}
          tone={k && k.checkins_missed_48h > 0 ? 'amber' : 'slate'}
          delay={0.25}
        />
      </div>

      {/* Trend + sparkline */}
      {data?.timeline && data.timeline.length > 0 && (
        <div className="mt-4 grid lg:grid-cols-[2fr,1fr] gap-4">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="card p-4"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">
                Flux 14 derniers jours
              </div>
              {trend != null && (
                <div className={`text-xs font-bold inline-flex items-center gap-1 ${
                  trend >= 0 ? 'text-emerald-700' : 'text-rose-700'
                }`}>
                  <TrendingUp className={`h-3.5 w-3.5 ${trend < 0 ? 'rotate-180' : ''}`} />
                  {trend >= 0 ? '+' : ''}{trend.toFixed(1)} %
                </div>
              )}
            </div>
            <div className="h-24">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.timeline} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="grad-trav" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#F77F00" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#F77F00" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Tooltip
                    contentStyle={{
                      background: 'white', border: '1px solid #e2e8f0',
                      borderRadius: 12, fontSize: 12,
                    }}
                    labelFormatter={(d) => new Date(d).toLocaleDateString('fr-FR')}
                  />
                  <Area
                    type="monotone" dataKey="travelers"
                    stroke="#F77F00" strokeWidth={2}
                    fill="url(#grad-trav)" name="Voyageurs"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Alertes récentes */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="card p-4"
          >
            <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-2">
              Alertes récentes
            </div>
            {!data?.recent_alerts?.length ? (
              <div className="text-sm text-slate-400 py-6 text-center">
                Aucune alerte ouverte
              </div>
            ) : (
              <ul className="space-y-2 max-h-[6.5rem] overflow-y-auto">
                {data.recent_alerts.slice(0, 4).map((a) => (
                  <li key={a.id} className="flex items-center gap-2 text-xs">
                    <span className={`px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase ${SEV_STYLES[a.severity] || SEV_STYLES.INFO}`}>
                      {a.severity}
                    </span>
                    <span className="truncate flex-1" title={a.title}>{a.title}</span>
                  </li>
                ))}
              </ul>
            )}
            <Link
              href="/alertes"
              className="block text-right text-xs text-ciOrange font-semibold mt-2 hover:underline"
            >
              Voir toutes →
            </Link>
          </motion.div>
        </div>
      )}
    </section>
  );
}

// -----------------------------------------------------------------------------
// KpiCard — composant animé
// -----------------------------------------------------------------------------

interface KpiCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | undefined;
  sub?: string;
  tone: 'orange' | 'emerald' | 'rose' | 'amber' | 'slate';
  delay?: number;
}

const TONE_STYLES: Record<KpiCardProps['tone'], { bg: string; text: string; ring: string }> = {
  orange: { bg: 'bg-orange-50 dark:bg-orange-950/30', text: 'text-orange-700 dark:text-orange-300', ring: 'ring-orange-200/60' },
  emerald: { bg: 'bg-emerald-50 dark:bg-emerald-950/30', text: 'text-emerald-700 dark:text-emerald-300', ring: 'ring-emerald-200/60' },
  rose: { bg: 'bg-rose-50 dark:bg-rose-950/30', text: 'text-rose-700 dark:text-rose-300', ring: 'ring-rose-200/60' },
  amber: { bg: 'bg-amber-50 dark:bg-amber-950/30', text: 'text-amber-700 dark:text-amber-300', ring: 'ring-amber-200/60' },
  slate: { bg: 'bg-slate-50 dark:bg-slate-900', text: 'text-slate-700 dark:text-slate-300', ring: 'ring-slate-200/60' },
};

function KpiCard({ icon, label, value, sub, tone, delay = 0 }: KpiCardProps) {
  const t = TONE_STYLES[tone];
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className={`relative overflow-hidden rounded-2xl ring-1 ${t.ring} ${t.bg} p-3`}
    >
      <div className={`inline-flex items-center justify-center h-7 w-7 rounded-lg ${t.text} bg-white/60 dark:bg-slate-950/30 mb-2`}>
        {icon}
      </div>
      <div className="font-display text-xl md:text-2xl font-black text-ciDark dark:text-emerald-100 tabular-nums">
        {value != null ? value.toLocaleString('fr-FR') : '—'}
      </div>
      <div className="text-[10px] uppercase tracking-wide text-slate-500 leading-tight mt-1">
        {label}
      </div>
      {sub && (
        <div className={`text-[10px] mt-1 ${t.text}`}>{sub}</div>
      )}
    </motion.div>
  );
}
