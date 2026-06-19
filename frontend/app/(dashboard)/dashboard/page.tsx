'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity, AlertTriangle, ArrowDown, ArrowRight, ArrowUp, BarChart3,
  Building2, CheckCircle2, Clock, Eye, Globe2, MapPin, RefreshCcw,
  ShieldCheck, Siren, Sparkles, Stethoscope, Users,
} from 'lucide-react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  RadialBar, RadialBarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { api, extractApiError } from '@/lib/api';
import { NationalOverview } from '@/components/dashboard/NationalOverview';
import { DashboardFilters, DashboardFilterState } from '@/components/dashboard/DashboardFilters';
import {
  FunnelChart, HourlyHeatmap, ComplianceGauge, ComparisonCard,
} from '@/components/dashboard/AdvancedStats';
import { Users as UsersIcon, Siren as SirenIcon, ShieldAlert as ShieldAlertIcon } from 'lucide-react';

/* ============================================================
   Types
   ============================================================ */
interface Overview {
  travelers: { total: number; last_24h: number; by_status: Record<string, number> };
  ebola: { total: number; by_status: Record<string, number>; by_risk: Record<string, number>; last_7d: number };
  quarantines: { active: number; total: number };
  passes: { total: number; active: number; revoked: number };
  alerts: { open: number; critical_24h: number };
  visits: { today: number; last_7d: number };
  generated_at: string;
}
interface VisitsResp {
  kpi: { period: number; previous_period: number; trend_pct: number; today: number };
  by_day: { date: string; count: number }[];
  top_countries: { country_code: string; country_name: string; count: number }[];
}
interface EntryFlow { entry_point__name: string | null; count: number }

/* ============================================================
   Palette officielle CI (alignée tailwind.config.ts)
   ============================================================ */
const CI = {
  orange: '#F77F00',
  green:  '#009B5A',
  dark:   '#064E3B',
  gold:   '#D4A017',
};
const RISK_COLORS: Record<string, string> = {
  low:      '#10B981',
  moderate: '#F59E0B',
  high:     '#EF4444',
  critical: '#7F1D1D',
  unknown:  '#94A3B8',
};
const STATUS_COLORS: Record<string, string> = {
  healthy:    '#10B981',
  observation:'#F59E0B',
  symptomatic:'#EF4444',
  confirmed:  '#7F1D1D',
  recovered:  '#06B6D4',
  deceased:   '#475569',
  unknown:    '#94A3B8',
};

const STATUS_LABEL: Record<string, string> = {
  healthy: 'En bonne santé',
  observation: 'Sous observation',
  symptomatic: 'Symptomatique',
  confirmed: 'Cas confirmé',
  recovered: 'Rétabli',
  deceased: 'Décédé',
  unknown: 'Indéterminé',
};
const RISK_LABEL: Record<string, string> = {
  low: 'Faible',
  moderate: 'Modéré',
  high: 'Élevé',
  critical: 'Critique',
  unknown: 'Indéterminé',
};

/* ============================================================
   Utilitaires
   ============================================================ */
function flag(code: string) {
  if (!code || code.length !== 2) return '🏳️';
  const A = 0x1f1e6;
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => A + c.charCodeAt(0) - 65));
}
function fmt(n: number | undefined) {
  return (n ?? 0).toLocaleString('fr-FR');
}
function greeting() {
  const h = new Date().getHours();
  if (h < 6) return 'Bonne nuit';
  if (h < 12) return 'Bonjour';
  if (h < 18) return 'Bon après-midi';
  return 'Bonsoir';
}

/* ============================================================
   PAGE
   ============================================================ */
export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [visits, setVisits] = useState<VisitsResp | null>(null);
  const [flows, setFlows] = useState<EntryFlow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filtres pilotant le bandeau national + les stats avancées
  const [filters, setFilters] = useState<DashboardFilterState>({
    period: 30, risk: '', followup: '', country: '', entryPoint: '',
  });
  // Données du payload /analytics/national/ remontées par NationalOverview
  const [nationalData, setNationalData] = useState<any>(null);

  const load = (silent = false) => {
    if (silent) setRefreshing(true); else setLoading(true);
    setErr(null);
    Promise.allSettled([
      api.get<Overview>('/analytics/overview/'),
      api.get<VisitsResp>('/analytics/visits/overview/?days=14'),
      api.get<EntryFlow[]>('/analytics/entry-point-flows/'),
    ])
      .then(([o, v, f]) => {
        if (o.status === 'fulfilled') setOverview(o.value.data);
        else setErr(extractApiError(o.reason));
        if (v.status === 'fulfilled') setVisits(v.value.data);
        if (f.status === 'fulfilled') setFlows(f.value.data || []);
      })
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    const id = setInterval(() => { load(true); }, 60_000);
    return () => clearInterval(id);
  }, []);

  /* ----- Dérivés ----- */
  const statusData = useMemo(() => {
    if (!overview) return [];
    return Object.entries(overview.travelers.by_status || {})
      .filter(([, v]) => (v as number) > 0)
      .map(([k, v]) => ({
        name: STATUS_LABEL[k] || k,
        key: k,
        value: v as number,
      }));
  }, [overview]);

  const riskData = useMemo(() => {
    if (!overview) return [];
    return Object.entries(overview.ebola.by_risk || {})
      .filter(([, v]) => (v as number) > 0)
      .map(([k, v]) => ({
        name: RISK_LABEL[k] || k,
        key: k,
        value: v as number,
      }));
  }, [overview]);

  const passActiveRatio = useMemo(() => {
    if (!overview || !overview.passes.total) return 0;
    return Math.round((overview.passes.active / overview.passes.total) * 100);
  }, [overview]);

  const flowsTop = useMemo(
    () =>
      flows
        .filter((f) => f.entry_point__name)
        .slice(0, 7)
        .map((f) => ({ name: f.entry_point__name as string, count: f.count })),
    [flows],
  );

  const trendUp = (visits?.kpi.trend_pct ?? 0) >= 0;

  if (loading && !overview) {
    return (
      <div className="space-y-6">
        <div className="card p-10 animate-pulse h-40" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => <div key={i} className="card p-6 h-28 animate-pulse" />)}
        </div>
        <div className="card p-10 animate-pulse h-72" />
      </div>
    );
  }
  if (err && !overview) {
    return (
      <div className="card p-6 text-rose-600 flex items-center justify-between">
        <span>{err}</span>
        <button onClick={() => load()} className="btn-outline text-sm">Réessayer</button>
      </div>
    );
  }
  if (!overview) return null;

  /* ============================================================
     RENDER
     ============================================================ */
  return (
    <div className="space-y-6 animate-fade-up">
      {/* ============ Barre de filtres globale ============ */}
      <DashboardFilters value={filters} onChange={setFilters} />

      {/* ============ Cards de comparaison période vs précédente ============ */}
      {nationalData?.kpis?.comparison && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ComparisonCard
            label="Voyageurs (période)"
            current={nationalData.kpis.comparison.travelers.current}
            previous={nationalData.kpis.comparison.travelers.previous}
            trendPct={nationalData.kpis.comparison.travelers.trend_pct}
            icon={<UsersIcon className="h-4 w-4" />}
          />
          <ComparisonCard
            label="Cas critiques"
            current={nationalData.kpis.comparison.cases_critical.current}
            previous={nationalData.kpis.comparison.cases_critical.previous}
            trendPct={nationalData.kpis.comparison.cases_critical.trend_pct}
            icon={<SirenIcon className="h-4 w-4 text-rose-500" />}
          />
          <ComparisonCard
            label="Cas à risque élevé"
            current={nationalData.kpis.comparison.cases_high.current}
            previous={nationalData.kpis.comparison.cases_high.previous}
            trendPct={nationalData.kpis.comparison.cases_high.trend_pct}
            icon={<ShieldAlertIcon className="h-4 w-4 text-orange-500" />}
          />
        </div>
      )}

      {/* ============ Bandeau premium temps réel (Phase 4) ============ */}
      {/* Branché sur /api/v1/analytics/national/ — filtres pris en compte */}
      <NationalOverview filters={filters} onData={setNationalData} />

      {/* ============ Stats avancées (funnel + heatmap + compliance) ============ */}
      {nationalData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {nationalData.funnel && (
            <FunnelChart data={nationalData.funnel} />
          )}
          {nationalData.arrivals_by_hour && (
            <HourlyHeatmap data={nationalData.arrivals_by_hour} />
          )}
          {nationalData.checkin_compliance && (
            <ComplianceGauge
              pct={nationalData.checkin_compliance.pct}
              withRecent={nationalData.checkin_compliance.with_recent}
              totalActive={nationalData.checkin_compliance.total_active}
            />
          )}
        </div>
      )}

      {/* ============ Top nationalités (sur la période filtrée) ============ */}
      {nationalData?.top_nationalities && nationalData.top_nationalities.length > 0 && (
        <article className="card p-6">
          <h3 className="font-display text-lg font-black flex items-center gap-2">
            <Globe2 className="h-5 w-5 text-ciOrange" /> Top nationalités · {filters.period}j
          </h3>
          <ul className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3">
            {nationalData.top_nationalities.slice(0, 10).map((n: any, i: number) => (
              <li
                key={i}
                className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 hover:bg-slate-50 dark:hover:bg-slate-900/50 transition"
              >
                <div className="text-xs text-slate-500 truncate">{n.nationality || '—'}</div>
                <div className="font-display text-xl font-black text-ciDark dark:text-emerald-200 mt-1">
                  {n.count.toLocaleString('fr-FR')}
                </div>
              </li>
            ))}
          </ul>
        </article>
      )}

      {/* ============ HERO BANNER ============ */}
      <section className="relative overflow-hidden rounded-3xl border border-emerald-900/20 bg-gradient-to-br from-ciDark via-emerald-900 to-emerald-950 text-white shadow-card">
        {/* bande tricolore CI */}
        <div className="absolute inset-x-0 top-0 h-1.5 flex">
          <div className="flex-1 bg-ciOrange" />
          <div className="flex-1 bg-white" />
          <div className="flex-1 bg-ciGreen" />
        </div>
        {/* motif dots */}
        <div className="absolute inset-0 opacity-[0.07] pattern-dots" aria-hidden />

        <div className="relative p-6 md:p-8 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 backdrop-blur px-3 py-1 text-[11px] uppercase tracking-widest font-bold">
              <span className="h-2 w-2 rounded-full bg-emerald-300 animate-pulse-dot" />
              Surveillance active · temps réel
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-black mt-3 leading-tight">
              {greeting()}, voici l'état national.
            </h1>
            <p className="mt-2 text-emerald-100/85 text-sm md:text-base max-w-xl">
              Vue consolidée MSHPCMU · INHP — voyageurs entrants, enquêtes Ebola,
              quarantaines, passes sanitaires et alertes sur l'ensemble du territoire.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full bg-emerald-500/15 ring-1 ring-emerald-300/30 px-3 py-1 font-semibold">
                <Clock className="inline h-3 w-3 mr-1 -mt-0.5" />
                Actualisé {new Date(overview.generated_at).toLocaleTimeString('fr-FR')}
              </span>
              <span className="rounded-full bg-white/10 ring-1 ring-white/20 px-3 py-1 font-semibold">
                <CheckCircle2 className="inline h-3 w-3 mr-1 -mt-0.5 text-emerald-300" />
                Backend opérationnel
              </span>
              {overview.alerts.critical_24h > 0 ? (
                <span className="rounded-full bg-rose-500/20 ring-1 ring-rose-300/40 px-3 py-1 font-semibold">
                  <Siren className="inline h-3 w-3 mr-1 -mt-0.5 text-rose-200" />
                  {overview.alerts.critical_24h} alerte(s) critique(s) 24h
                </span>
              ) : (
                <span className="rounded-full bg-emerald-500/20 ring-1 ring-emerald-300/40 px-3 py-1 font-semibold">
                  <ShieldCheck className="inline h-3 w-3 mr-1 -mt-0.5 text-emerald-200" />
                  Aucune alerte critique 24h
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row lg:flex-col gap-3 lg:items-end">
            <button
              onClick={() => load(true)}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-xl bg-white/15 hover:bg-white/25 backdrop-blur px-4 py-2.5 text-sm font-bold transition disabled:opacity-60"
            >
              <RefreshCcw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Mise à jour…' : 'Rafraîchir'}
            </button>
            <Link
              href="/alertes"
              className="inline-flex items-center gap-2 rounded-xl bg-ciOrange hover:bg-orange-600 px-4 py-2.5 text-sm font-bold shadow-lg shadow-orange-500/30 transition"
            >
              <Siren className="h-4 w-4" /> Centre d'alertes
            </Link>
          </div>
        </div>
      </section>

      {/* ============ KPI CARDS PREMIUM ============ */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <KpiCard
          label="Voyageurs"
          value={overview.travelers.total}
          delta={overview.travelers.last_24h}
          deltaLabel="+24h"
          icon={<Users className="h-5 w-5" />}
          accent="green"
          href="/surveillance"
        />
        <KpiCard
          label="Enquêtes Ebola"
          value={overview.ebola.total}
          delta={overview.ebola.last_7d}
          deltaLabel="+7j"
          icon={<Activity className="h-5 w-5" />}
          accent="orange"
          href="/surveillance"
        />
        <KpiCard
          label="Quarantaines actives"
          value={overview.quarantines.active}
          delta={overview.quarantines.total}
          deltaLabel="total"
          icon={<ShieldCheck className="h-5 w-5" />}
          accent="dark"
          href="/surveillance"
        />
        <KpiCard
          label="Alertes ouvertes"
          value={overview.alerts.open}
          delta={overview.alerts.critical_24h}
          deltaLabel="crit. 24h"
          icon={<AlertTriangle className="h-5 w-5" />}
          accent={overview.alerts.critical_24h > 0 ? 'red' : 'gold'}
          href="/alertes"
        />
      </section>

      {/* ============ KPI SECONDAIRES (PASS + VISITES) ============ */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Pass sanitaires (radial chart) */}
        <article className="card p-5 flex items-center gap-4">
          <div className="relative h-24 w-24 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                innerRadius="65%"
                outerRadius="100%"
                data={[{ value: passActiveRatio, fill: CI.green }]}
                startAngle={90}
                endAngle={-270}
              >
                <RadialBar background={{ fill: '#E2E8F0' }} dataKey="value" cornerRadius={20} />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 grid place-items-center">
              <span className="font-display text-lg font-black text-ciDark dark:text-emerald-200">
                {passActiveRatio}%
              </span>
            </div>
          </div>
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-widest font-bold text-ciGreen">
              Passes sanitaires
            </div>
            <div className="font-display text-2xl font-black mt-0.5">
              {fmt(overview.passes.active)}
              <span className="text-sm font-bold text-slate-400"> / {fmt(overview.passes.total)}</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {fmt(overview.passes.revoked)} révoqué(s)
            </div>
          </div>
        </article>

        {/* Visites aujourd'hui */}
        <article className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-widest font-bold text-ciOrange">
                Visites · aujourd'hui
              </div>
              <div className="font-display text-3xl font-black mt-0.5">{fmt(overview.visits.today)}</div>
              <div className="text-xs text-slate-500 mt-1">
                {fmt(overview.visits.last_7d)} sur 7 jours
              </div>
            </div>
            <div className="h-12 w-12 rounded-2xl bg-orange-50 dark:bg-orange-950/40 grid place-items-center text-ciOrange">
              <Eye className="h-5 w-5" />
            </div>
          </div>
          {/* Mini sparkline (14j) */}
          <div className="h-14 -mx-2 mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={visits?.by_day || []} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                <defs>
                  <linearGradient id="sparkVisits" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CI.orange} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={CI.orange} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area dataKey="count" stroke={CI.orange} strokeWidth={2} fill="url(#sparkVisits)" />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                  labelFormatter={(v) => new Date(v as string).toLocaleDateString('fr-FR')}
                  formatter={(v: any) => [v, 'Visites']}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        {/* Tendance vs période */}
        <article className="card p-5">
          <div className="text-[11px] uppercase tracking-widest font-bold text-slate-500">
            Tendance · 14 jours
          </div>
          <div className="font-display text-3xl font-black mt-0.5">
            {fmt(visits?.kpi.period)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            vs {fmt(visits?.kpi.previous_period)} période précédente
          </div>
          <div className={`mt-3 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
            trendUp ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
                    : 'bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300'
          }`}>
            {trendUp ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
            {Math.abs(visits?.kpi.trend_pct ?? 0)}%
          </div>
        </article>
      </section>

      {/* ============ COURBE + FLUX POINTS D'ENTRÉE ============ */}
      <section className="grid lg:grid-cols-3 gap-4">
        {/* Courbe trafic */}
        <article className="card p-6 lg:col-span-2">
          <header className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-ciOrange" /> Trafic de la plateforme
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Visites quotidiennes · {visits?.by_day.length || 0} jours
              </p>
            </div>
            <Link href="/visites" className="text-xs font-bold text-ciOrange hover:underline inline-flex items-center gap-1">
              Tout voir <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </header>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={visits?.by_day || []} margin={{ top: 10, right: 8, bottom: 0, left: -16 }}>
                <defs>
                  <linearGradient id="trafficGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CI.orange} stopOpacity={0.45} />
                    <stop offset="100%" stopColor={CI.orange} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#64748B' }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => new Date(v).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })}
                />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0' }}
                  labelFormatter={(v) => new Date(v as string).toLocaleDateString('fr-FR')}
                  formatter={(v: any) => [v, 'Visites']}
                />
                <Area type="monotone" dataKey="count" stroke={CI.orange} strokeWidth={2.5} fill="url(#trafficGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        {/* Flux points d'entrée */}
        <article className="card p-6">
          <header className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <MapPin className="h-5 w-5 text-ciGreen" /> Flux points d'entrée
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">7 derniers jours</p>
            </div>
            <Link href="/points-entree" className="text-xs font-bold text-ciGreen hover:underline inline-flex items-center gap-1">
              Détails <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </header>
          {flowsTop.length === 0 ? (
            <EmptyState icon={<MapPin className="h-6 w-6" />} label="Aucun flux enregistré sur les 7 derniers jours." />
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={flowsTop} layout="vertical" margin={{ top: 4, right: 12, bottom: 0, left: 8 }}>
                  <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={110}
                    tick={{ fontSize: 11, fill: '#334155' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0' }}
                    formatter={(v: any) => [v, 'Voyageurs']}
                  />
                  <Bar dataKey="count" radius={[6, 6, 6, 6]} fill={CI.green} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </article>
      </section>

      {/* ============ RÉPARTITIONS STATUTS / RISQUE ============ */}
      <section className="grid lg:grid-cols-2 gap-4">
        <article className="card p-6">
          <header className="flex items-center justify-between mb-2">
            <h3 className="font-display text-lg font-black flex items-center gap-2">
              <Stethoscope className="h-5 w-5 text-ciGreen" /> Voyageurs · état de santé
            </h3>
            <span className="text-xs text-slate-500">{fmt(overview.travelers.total)} total</span>
          </header>
          {statusData.length === 0 ? (
            <EmptyState icon={<Stethoscope className="h-6 w-6" />} label="Aucun voyageur encore enregistré." />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      dataKey="value"
                      innerRadius={48}
                      outerRadius={78}
                      paddingAngle={2}
                      strokeWidth={0}
                    >
                      {statusData.map((d) => (
                        <Cell key={d.key} fill={STATUS_COLORS[d.key] || CI.green} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="space-y-2 text-sm">
                {statusData.map((d) => (
                  <li key={d.key} className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: STATUS_COLORS[d.key] || CI.green }} />
                      <span className="font-medium">{d.name}</span>
                    </span>
                    <span className="font-black text-ciDark dark:text-emerald-200">{fmt(d.value)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </article>

        <article className="card p-6">
          <header className="flex items-center justify-between mb-2">
            <h3 className="font-display text-lg font-black flex items-center gap-2">
              <Activity className="h-5 w-5 text-ciOrange" /> Ebola · niveau de risque
            </h3>
            <span className="text-xs text-slate-500">{fmt(overview.ebola.total)} enquête(s)</span>
          </header>
          {riskData.length === 0 ? (
            <EmptyState icon={<Activity className="h-6 w-6" />} label="Aucune enquête Ebola enregistrée." />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskData}
                      dataKey="value"
                      innerRadius={48}
                      outerRadius={78}
                      paddingAngle={2}
                      strokeWidth={0}
                    >
                      {riskData.map((d) => (
                        <Cell key={d.key} fill={RISK_COLORS[d.key] || CI.orange} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="space-y-2 text-sm">
                {riskData.map((d) => (
                  <li key={d.key} className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLORS[d.key] || CI.orange }} />
                      <span className="font-medium">{d.name}</span>
                    </span>
                    <span className="font-black text-ciDark dark:text-emerald-200">{fmt(d.value)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </article>
      </section>

      {/* ============ TOP PAYS + ACCÈS RAPIDES + SYSTEM ============ */}
      <section className="grid lg:grid-cols-3 gap-4">
        {/* Top pays */}
        <article className="card p-6 lg:col-span-2">
          <header className="flex items-center justify-between mb-4">
            <h3 className="font-display text-lg font-black flex items-center gap-2">
              <Globe2 className="h-5 w-5 text-ciOrange" /> Origines · top pays (14j)
            </h3>
            <Link href="/visites" className="text-xs font-bold text-ciOrange hover:underline inline-flex items-center gap-1">
              Voir tout <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </header>
          {(visits?.top_countries.length ?? 0) === 0 ? (
            <EmptyState icon={<Globe2 className="h-6 w-6" />} label="Pas encore de données géographiques." />
          ) : (
            <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-2.5">
              {visits!.top_countries.slice(0, 8).map((c) => {
                const max = Math.max(1, ...visits!.top_countries.map((x) => x.count));
                return (
                  <li key={c.country_code}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="flex items-center gap-2 min-w-0">
                        <span className="text-lg leading-none">{flag(c.country_code)}</span>
                        <span className="font-semibold truncate">{c.country_name || c.country_code}</span>
                      </span>
                      <span className="font-bold text-ciDark dark:text-emerald-200">{fmt(c.count)}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-ciOrange to-ciGreen"
                        style={{ width: `${(c.count / max) * 100}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </article>

        {/* Accès rapides */}
        <article className="card p-6">
          <h3 className="font-display text-lg font-black flex items-center gap-2 mb-4">
            <BarChart3 className="h-5 w-5 text-ciGreen" /> Accès rapides
          </h3>
          <div className="space-y-2">
            <QuickLink href="/surveillance" icon={<Activity className="h-4 w-4" />} label="Surveillance" desc="Voyageurs, enquêtes, suivi 21j" />
            <QuickLink href="/alertes" icon={<Siren className="h-4 w-4" />} label="Alertes" desc={`${overview.alerts.open} ouverte(s)`} highlight={overview.alerts.open > 0} />
            <QuickLink href="/cartographie" icon={<MapPin className="h-4 w-4" />} label="Cartographie" desc="Vue géospatiale" />
            <QuickLink href="/districts" icon={<Building2 className="h-4 w-4" />} label="Districts sanitaires" desc="Annuaire et flux" />
            <QuickLink href="/visites" icon={<Eye className="h-4 w-4" />} label="Visites" desc={`${fmt(overview.visits.today)} aujourd'hui`} />
          </div>
        </article>
      </section>

      {/* ============ FOOTER STATUT SYSTÈME ============ */}
      <section className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur px-5 py-4 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse-dot" />
          <span className="font-semibold">Plateforme opérationnelle</span>
          <span className="text-slate-400">·</span>
          <span>EpiTrace v0.1.0</span>
          <span className="text-slate-400">·</span>
          <span>MSHPCMU · INHP</span>
        </div>
        <div className="flex items-center gap-3 text-slate-500">
          <span>Auto-refresh 60 s</span>
          <span>·</span>
          <span>
            Dernière synchro : {new Date(overview.generated_at).toLocaleString('fr-FR')}
          </span>
        </div>
      </section>
    </div>
  );
}

/* ============================================================
   SUB COMPONENTS
   ============================================================ */
function KpiCard({
  label, value, delta, deltaLabel, icon, accent, href,
}: {
  label: string;
  value: number;
  delta?: number;
  deltaLabel?: string;
  icon: React.ReactNode;
  accent: 'green' | 'orange' | 'dark' | 'gold' | 'red';
  href?: string;
}) {
  const accentMap: Record<typeof accent, { bg: string; ring: string; text: string; bar: string }> = {
    green:  { bg: 'bg-emerald-50 dark:bg-emerald-950/40', ring: 'ring-emerald-200/60 dark:ring-emerald-900/40', text: 'text-ciGreen',  bar: 'bg-ciGreen' },
    orange: { bg: 'bg-orange-50 dark:bg-orange-950/40',   ring: 'ring-orange-200/60 dark:ring-orange-900/40',   text: 'text-ciOrange', bar: 'bg-ciOrange' },
    dark:   { bg: 'bg-emerald-50 dark:bg-emerald-950/40', ring: 'ring-emerald-300/40 dark:ring-emerald-900/40', text: 'text-ciDark dark:text-emerald-200', bar: 'bg-ciDark dark:bg-emerald-400' },
    gold:   { bg: 'bg-amber-50 dark:bg-amber-950/40',     ring: 'ring-amber-200/60 dark:ring-amber-900/40',     text: 'text-ciGold',   bar: 'bg-ciGold' },
    red:    { bg: 'bg-rose-50 dark:bg-rose-950/40',       ring: 'ring-rose-200/60 dark:ring-rose-900/40',       text: 'text-rose-600 dark:text-rose-300', bar: 'bg-rose-500' },
  };
  const a = accentMap[accent];
  const card = (
    <div className={`relative card p-5 overflow-hidden group transition hover:-translate-y-0.5 hover:shadow-xl ring-1 ${a.ring}`}>
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${a.bar}`} aria-hidden />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-widest font-bold text-slate-500">
            {label}
          </div>
          <div className={`mt-1 font-display text-3xl md:text-[2rem] leading-tight font-black ${a.text}`}>
            {fmt(value)}
          </div>
          {delta !== undefined && (
            <div className="mt-1 text-xs text-slate-500">
              <span className={`font-bold ${a.text}`}>{fmt(delta)}</span> {deltaLabel}
            </div>
          )}
        </div>
        <div className={`h-10 w-10 rounded-xl grid place-items-center ${a.bg} ${a.text} shrink-0`}>
          {icon}
        </div>
      </div>
      {href && (
        <div className="mt-4 text-[11px] font-bold text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 inline-flex items-center gap-1">
          Ouvrir <ArrowRight className="h-3 w-3 transition group-hover:translate-x-0.5" />
        </div>
      )}
    </div>
  );
  return href ? <Link href={href}>{card}</Link> : card;
}

function QuickLink({
  href, icon, label, desc, highlight,
}: { href: string; icon: React.ReactNode; label: string; desc: string; highlight?: boolean }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition group ${
        highlight
          ? 'bg-rose-50 dark:bg-rose-950/30 hover:bg-rose-100 dark:hover:bg-rose-950/50'
          : 'hover:bg-slate-50 dark:hover:bg-slate-800/60'
      }`}
    >
      <span className={`h-9 w-9 rounded-xl grid place-items-center ${
        highlight ? 'bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-300'
                  : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 group-hover:bg-ciGreen/10 group-hover:text-ciGreen'
      }`}>
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-bold leading-tight">{label}</div>
        <div className="text-xs text-slate-500 truncate">{desc}</div>
      </div>
      <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-slate-600 transition group-hover:translate-x-0.5" />
    </Link>
  );
}

function EmptyState({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="h-48 grid place-items-center text-center px-4">
      <div>
        <div className="mx-auto h-12 w-12 rounded-2xl bg-slate-100 dark:bg-slate-800 grid place-items-center text-slate-400 mb-3">
          {icon}
        </div>
        <p className="text-sm text-slate-500">{label}</p>
      </div>
    </div>
  );
}
