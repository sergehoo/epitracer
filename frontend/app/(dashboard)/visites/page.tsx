'use client';

/**
 * /dashboard/visites — Analytique de fréquentation.
 *
 * Fusionne 3 dimensions :
 *  - Tendance temporelle (par jour + heatmap jour × heure)
 *  - Géographie (pays, villes)
 *  - Contenu (pages, référents, langues, portails)
 *
 * Bot toggle, portail, période — tout est piloté par les query params
 * du backend `/analytics/visits/overview/`.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import {
  ArrowDown, ArrowUp, Bot, Building2, Clock3, Eye, ExternalLink, Globe2,
  Info, Languages, Laptop2, MousePointerClick, RefreshCw, Server, Smartphone, Users,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface HourDow { dow: number; hour: number; count: number; }
interface OverviewResp {
  days: number;
  exclude_bots: boolean;
  portal_filter: string | null;
  kpi: {
    total: number;
    today: number;
    this_week: number;
    this_month: number;
    period: number;
    previous_period: number;
    unique_sessions_period: number;
    trend_pct: number;
    bots_count?: number;
    active_now?: number;
  };
  by_day: { date: string; count: number }[];
  by_hour?: { hour: number; count: number }[];
  by_hour_dow?: HourDow[];
  top_countries: { country_code: string; country_name: string; count: number }[];
  top_cities: { city: string; country_code: string; country_name: string; count: number }[];
  top_paths: { path: string; count: number }[];
  top_referrers?: { referrer: string; count: number }[];
  by_portal: { portal: string; count: number }[];
  top_languages: { language: string; count: number }[];
  devices?: { device: string; count: number }[];
  generated_at: string;
}

const PORTAL_LABEL: Record<string, string> = {
  public: 'Portail public',
  admin: 'Portail admin',
  api: 'API',
};

const PATH_LABEL: Record<string, string> = {
  '/': 'Accueil',
  '/inscription': 'Formulaire voyageur',
  '/verifier-pass': 'Vérification pass',
  '/assistance': 'Assistance',
  '/voyageur/suivi': 'Suivi voyageur (PWA)',
  '/voyageur/mes-donnees': 'Mes données (RGPD)',
  '/login': 'Connexion',
  '/dashboard': 'Dashboard admin',
  '/voyageurs': 'Liste voyageurs',
  '/alertes': 'Alertes',
  '/audit-logs': 'Journaux d\'audit',
  '/notifications': 'Notifications',
  '/visites': 'Analytique visites',
};

const DOW_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

const FLAG_FALLBACK = '🏳️';
function flag(code: string) {
  if (!code || code.length !== 2) return FLAG_FALLBACK;
  const A = 0x1f1e6;
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => A + c.charCodeAt(0) - 65));
}

function humanPath(p: string): string {
  if (!p) return '(inconnu)';
  return PATH_LABEL[p] || p;
}

function heatColor(intensity: number): string {
  // intensity ∈ [0, 1]
  if (intensity <= 0) return 'bg-slate-100 dark:bg-slate-800';
  if (intensity < 0.15) return 'bg-emerald-100 dark:bg-emerald-900/40';
  if (intensity < 0.35) return 'bg-emerald-200 dark:bg-emerald-800/60';
  if (intensity < 0.55) return 'bg-emerald-400 dark:bg-emerald-700';
  if (intensity < 0.75) return 'bg-ciOrange dark:bg-ciOrange/90';
  return 'bg-rose-500 dark:bg-rose-600';
}

export default function VisitsPage() {
  const [days, setDays] = useState(30);
  const [portal, setPortal] = useState<'' | 'public' | 'admin' | 'api'>('');
  const [includeBots, setIncludeBots] = useState(false);
  const [data, setData] = useState<OverviewResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams({ days: String(days) });
    if (portal) params.set('portal', portal);
    if (includeBots) params.set('include_bots', '1');
    api
      .get<OverviewResp>(`/analytics/visits/overview/?${params.toString()}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [days, portal, includeBots]);

  const trendUp = (data?.kpi.trend_pct ?? 0) >= 0;
  const trendNeutral = (data?.kpi.trend_pct ?? 0) === 0;

  const topPathMax = useMemo(
    () => Math.max(1, ...(data?.top_paths ?? []).map((p) => p.count)),
    [data],
  );
  const topCountryMax = useMemo(
    () => Math.max(1, ...(data?.top_countries ?? []).map((p) => p.count)),
    [data],
  );
  const topCityMax = useMemo(
    () => Math.max(1, ...(data?.top_cities ?? []).map((p) => p.count)),
    [data],
  );
  const topRefMax = useMemo(
    () => Math.max(1, ...(data?.top_referrers ?? []).map((p) => p.count)),
    [data],
  );

  // Construit matrice 7 x 24 pour la heatmap
  const heatmap = useMemo(() => {
    const grid: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
    if (!data?.by_hour_dow) return { grid, max: 0 };
    let max = 0;
    for (const cell of data.by_hour_dow) {
      // Postgres ISO DOW : 1=lundi..7=dimanche → index 0..6
      const dowIdx = Math.max(0, Math.min(6, (cell.dow || 1) - 1));
      const h = Math.max(0, Math.min(23, cell.hour || 0));
      grid[dowIdx][h] = cell.count;
      if (cell.count > max) max = cell.count;
    }
    return { grid, max };
  }, [data]);

  const busiestHour = useMemo(() => {
    if (!data?.by_hour || data.by_hour.length === 0) return null;
    return data.by_hour.reduce((acc, cur) => (cur.count > acc.count ? cur : acc), data.by_hour[0]);
  }, [data]);

  const avgPerDay = useMemo(() => {
    if (!data?.by_day || data.by_day.length === 0) return 0;
    return Math.round(data.by_day.reduce((s, d) => s + d.count, 0) / data.by_day.length);
  }, [data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Analytique · Fréquentation
          </div>
          <h1 className="font-display text-3xl font-black">Compteur de visites</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-3xl">
            Trafic public et administratif de la plateforme veillesanitaire.com. Chaque
            page vue est comptée côté serveur (RGPD-friendly, sans cookie tiers).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={load}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            title="Rafraîchir"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Actualiser
          </button>
          <label className="inline-flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={includeBots}
              onChange={(e) => setIncludeBots(e.target.checked)}
              className="accent-ciOrange"
            />
            <Bot className="h-3.5 w-3.5" />
            Inclure bots
          </label>
          <select
            className="select max-w-[180px]"
            value={portal}
            onChange={(e) => setPortal(e.target.value as 'public' | 'admin' | 'api' | '')}
          >
            <option value="">Tous les portails</option>
            <option value="public">Portail public</option>
            <option value="admin">Portail admin</option>
            <option value="api">API</option>
          </select>
          <div className="inline-flex rounded-xl border border-slate-300 dark:border-slate-700 p-1">
            {[7, 14, 30, 90, 365].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 text-xs rounded-lg font-bold transition ${days === d ? 'bg-ciDark text-white' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
              >
                {d === 365 ? '1 an' : `${d} j`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {err && <div className="card p-6 text-rose-600">{err}</div>}
      {loading && <div className="card p-10 animate-pulse h-40" />}

      {data && !loading && (
        <>
          {/* KPIs principaux */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Kpi
              label="Actifs à l'instant"
              value={data.kpi.active_now ?? 0}
              icon={<Users className="h-5 w-5" />}
              accent="ciOrange"
              hint="Sessions actives — 5 dernières minutes"
              pulse
            />
            <Kpi
              label="Aujourd'hui"
              value={data.kpi.today}
              icon={<Eye className="h-5 w-5" />}
              accent="ciGreen"
              hint="Pages vues depuis minuit"
            />
            <Kpi
              label="Cette semaine"
              value={data.kpi.this_week}
              icon={<MousePointerClick className="h-5 w-5" />}
              accent="ciDark"
              hint="Depuis lundi"
            />
            <Kpi
              label="Ce mois-ci"
              value={data.kpi.this_month}
              icon={<Globe2 className="h-5 w-5" />}
              accent="ciGold"
              hint="Depuis le 1er du mois"
            />
          </div>

          {/* KPIs secondaires période */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MiniStat
              label="Total cumulé"
              value={data.kpi.total.toLocaleString('fr-FR')}
              hint="Depuis mise en service"
            />
            <MiniStat
              label="Sessions uniques"
              value={data.kpi.unique_sessions_period.toLocaleString('fr-FR')}
              hint={`Sur ${data.days} j`}
            />
            <MiniStat
              label="Moyenne / jour"
              value={avgPerDay.toLocaleString('fr-FR')}
              hint="Pages / jour"
            />
            <MiniStat
              label="Bots détectés"
              value={(data.kpi.bots_count ?? 0).toLocaleString('fr-FR')}
              hint={data.exclude_bots ? 'Exclus des stats' : 'Inclus dans les stats'}
            />
          </div>

          {/* Tendance période */}
          <article className="card p-6">
            <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-4">
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">
                  Tendance · {data.days} derniers jours
                </div>
                <div className="mt-1 font-display text-2xl font-black flex items-baseline gap-3">
                  {data.kpi.period.toLocaleString('fr-FR')}{' '}
                  <span className="text-sm font-bold text-slate-500">visites</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Précédent : <span className="font-semibold text-slate-700 dark:text-slate-300">
                    {data.kpi.previous_period.toLocaleString('fr-FR')}
                  </span>
                </div>
              </div>
              <div className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ${
                trendNeutral ? 'bg-slate-100 text-slate-600'
                : trendUp ? 'bg-emerald-50 text-emerald-700'
                : 'bg-rose-50 text-rose-700'
              }`}>
                {trendNeutral ? <span>—</span>
                  : trendUp ? <ArrowUp className="h-3.5 w-3.5" />
                  : <ArrowDown className="h-3.5 w-3.5" />}
                {Math.abs(data.kpi.trend_pct)}% vs période précédente
              </div>
            </header>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.by_day} margin={{ top: 10, right: 20, bottom: 0, left: -10 }}>
                  <defs>
                    <linearGradient id="visitGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#F77F00" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#F77F00" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#64748B' }}
                    tickFormatter={(v) => new Date(v).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#64748B' }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0' }}
                    labelFormatter={(v) => new Date(v as string).toLocaleDateString('fr-FR')}
                    formatter={(v: number | string) => [v, 'Visites']}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#F77F00"
                    strokeWidth={2.5}
                    fill="url(#visitGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-4 text-[11px] text-slate-500 flex flex-wrap items-center gap-4">
              <span className="inline-flex items-center gap-1">
                <Clock3 className="h-3 w-3" />
                Rapport actualisé à {new Date(data.generated_at).toLocaleTimeString('fr-FR')}
              </span>
              <span>Bots : <b>{data.exclude_bots ? 'exclus' : 'inclus'}</b></span>
              {data.portal_filter && (
                <span>Portail : <b>{PORTAL_LABEL[data.portal_filter] || data.portal_filter}</b></span>
              )}
              {busiestHour && (
                <span>Heure de pointe : <b>{String(busiestHour.hour).padStart(2, '0')}h — {busiestHour.count} vues</b></span>
              )}
            </div>
          </article>

          {/* Heatmap jour × heure */}
          {data.by_hour_dow && data.by_hour_dow.length > 0 && (
            <article className="card p-6">
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 mb-4">
                <div>
                  <h3 className="font-display text-lg font-black flex items-center gap-2">
                    <Clock3 className="h-5 w-5 text-ciOrange" /> Distribution horaire
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Chaque cellule = pages vues à cette heure locale de ce jour de la semaine, sur toute la période.
                  </p>
                </div>
                <HeatLegend max={heatmap.max} />
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-[10px]">
                  <thead>
                    <tr>
                      <th className="w-10"></th>
                      {Array.from({ length: 24 }).map((_, h) => (
                        <th key={h} className="text-center font-mono text-slate-400 py-1 w-[3.4%]">
                          {h % 3 === 0 ? String(h).padStart(2, '0') : ''}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {DOW_LABELS.map((label, dowIdx) => (
                      <tr key={label}>
                        <td className="pr-2 text-slate-500 font-semibold text-right">{label}</td>
                        {heatmap.grid[dowIdx].map((count, h) => {
                          const intensity = heatmap.max > 0 ? count / heatmap.max : 0;
                          return (
                            <td key={h} className="p-0.5">
                              <div
                                className={`h-6 rounded ${heatColor(intensity)} transition hover:ring-2 hover:ring-ciOrange`}
                                title={`${label} ${String(h).padStart(2, '0')}h — ${count} visite${count > 1 ? 's' : ''}`}
                              />
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          )}

          {/* Répartition par portail + Devices */}
          <div className="grid lg:grid-cols-2 gap-6">
            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Server className="h-5 w-5 text-ciOrange" /> Répartition par portail
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Trafic public (voyageurs) vs administration (agents INHP) vs endpoints API.
              </p>
              <ul className="mt-4 space-y-3">
                {data.by_portal.map((p) => {
                  const total = data.by_portal.reduce((s, x) => s + x.count, 0) || 1;
                  const pct = Math.round((p.count / total) * 100);
                  return (
                    <li key={p.portal}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-semibold flex items-center gap-2">
                          {p.portal === 'admin' ? <Laptop2 className="h-3.5 w-3.5 text-slate-500" />
                            : p.portal === 'api' ? <Server className="h-3.5 w-3.5 text-slate-500" />
                            : <Globe2 className="h-3.5 w-3.5 text-slate-500" />}
                          {PORTAL_LABEL[p.portal] || p.portal}
                        </span>
                        <span className="font-bold text-ciDark dark:text-emerald-200">
                          {p.count.toLocaleString('fr-FR')} <span className="text-xs text-slate-400">· {pct}%</span>
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div
                          className={`h-full ${p.portal === 'admin' ? 'bg-ciDark dark:bg-emerald-500' : p.portal === 'api' ? 'bg-slate-500' : 'bg-ciOrange'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </li>
                  );
                })}
                {data.by_portal.length === 0 && <li className="text-sm text-slate-500">—</li>}
              </ul>
            </article>

            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Smartphone className="h-5 w-5 text-ciGreen" /> Type d'appareil
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Détecté depuis l'user-agent — précision indicative.
              </p>
              <ul className="mt-4 space-y-3">
                {(data.devices ?? []).map((d) => {
                  const total = (data.devices ?? []).reduce((s, x) => s + x.count, 0) || 1;
                  const pct = Math.round((d.count / total) * 100);
                  const label = d.device === 'mobile' ? 'Mobile / tablette' : d.device === 'desktop' ? 'Desktop' : 'API / bot';
                  const icon = d.device === 'mobile' ? <Smartphone className="h-3.5 w-3.5" />
                    : d.device === 'desktop' ? <Laptop2 className="h-3.5 w-3.5" />
                    : <Server className="h-3.5 w-3.5" />;
                  const barColor = d.device === 'mobile' ? 'bg-emerald-500'
                    : d.device === 'desktop' ? 'bg-sky-500' : 'bg-slate-500';
                  return (
                    <li key={d.device}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-semibold flex items-center gap-2">
                          {icon} {label}
                        </span>
                        <span className="font-bold text-ciDark dark:text-emerald-200">
                          {d.count.toLocaleString('fr-FR')} <span className="text-xs text-slate-400">· {pct}%</span>
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
                      </div>
                    </li>
                  );
                })}
                {(!data.devices || data.devices.length === 0) && (
                  <li className="text-sm text-slate-500">Aucune donnée.</li>
                )}
              </ul>
            </article>
          </div>

          {/* Top pays + Top villes */}
          <div className="grid lg:grid-cols-2 gap-6">
            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Globe2 className="h-5 w-5 text-ciOrange" /> Top pays d'origine
              </h3>
              {data.top_countries.length === 0 ? (
                <p className="text-sm text-slate-500 mt-3">Aucune donnée géographique sur la période.</p>
              ) : (
                <ul className="mt-4 space-y-2.5">
                  {data.top_countries.map((c) => (
                    <li key={c.country_code}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="flex items-center gap-2 min-w-0">
                          <span className="text-lg leading-none">{flag(c.country_code)}</span>
                          <span className="font-semibold truncate">{c.country_name || c.country_code}</span>
                          <span className="text-xs text-slate-400 font-mono">({c.country_code})</span>
                        </span>
                        <span className="font-bold text-ciDark dark:text-emerald-200 shrink-0 ml-2">
                          {c.count.toLocaleString('fr-FR')}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-ciOrange to-ciGreen"
                          style={{ width: `${(c.count / topCountryMax) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </article>

            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Building2 className="h-5 w-5 text-ciGreen" /> Top villes / localités
              </h3>
              {(data.top_cities || []).length === 0 ? (
                <p className="text-sm text-slate-500 mt-3">
                  Aucune ville détectée. L'enrichissement GeoIP est requis pour cette
                  statistique (voir <code className="text-xs">apps/analytics/services.py</code>).
                </p>
              ) : (
                <ul className="mt-4 space-y-2.5">
                  {data.top_cities.map((c, i) => (
                    <li key={`${c.city}-${c.country_code}-${i}`}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="flex items-center gap-2 min-w-0">
                          <span className="text-base leading-none">{flag(c.country_code)}</span>
                          <span className="font-semibold truncate">{c.city}</span>
                          <span className="text-xs text-slate-400 truncate">
                            {c.country_name || c.country_code}
                          </span>
                        </span>
                        <span className="font-bold text-ciDark dark:text-emerald-200 shrink-0 ml-2">
                          {c.count.toLocaleString('fr-FR')}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-500 to-ciOrange"
                          style={{ width: `${(c.count / topCityMax) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </div>

          {/* Pages + Referrers */}
          <div className="grid lg:grid-cols-2 gap-6">
            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <MousePointerClick className="h-5 w-5 text-ciGreen" /> Pages les plus visitées
              </h3>
              {data.top_paths.length === 0 ? (
                <p className="text-sm text-slate-500 mt-3">Aucune visite sur la période.</p>
              ) : (
                <ul className="mt-4 space-y-2.5">
                  {data.top_paths.map((p) => (
                    <li key={p.path}>
                      <div className="flex items-center justify-between text-sm mb-1 gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold truncate">{humanPath(p.path)}</div>
                          <div className="font-mono text-[10px] text-slate-400 truncate">{p.path}</div>
                        </div>
                        <span className="font-bold text-ciDark dark:text-emerald-200 shrink-0">
                          {p.count.toLocaleString('fr-FR')}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-ciGreen to-emerald-700"
                          style={{ width: `${(p.count / topPathMax) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </article>

            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <ExternalLink className="h-5 w-5 text-ciOrange" /> Sources / référents
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                D'où viennent vos visiteurs : moteurs de recherche, réseaux sociaux, accès direct.
              </p>
              {(data.top_referrers ?? []).length === 0 ? (
                <p className="text-sm text-slate-500 mt-3">Aucune donnée de référent sur la période.</p>
              ) : (
                <ul className="mt-4 space-y-2.5">
                  {(data.top_referrers ?? []).map((r) => (
                    <li key={r.referrer}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-mono text-xs truncate max-w-[70%]" title={r.referrer}>
                          {r.referrer}
                        </span>
                        <span className="font-bold text-ciDark dark:text-emerald-200">
                          {r.count.toLocaleString('fr-FR')}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-ciOrange to-rose-500"
                          style={{ width: `${(r.count / topRefMax) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </div>

          {/* Langues */}
          <article className="card p-6">
            <h3 className="font-display text-lg font-black flex items-center gap-2">
              <Languages className="h-5 w-5 text-ciOrange" /> Langues des visiteurs
            </h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {data.top_languages.map((l) => (
                <span
                  key={l.language}
                  className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 dark:bg-slate-800 px-3 py-1 text-xs font-semibold"
                  title={`${l.count} visites`}
                >
                  <span className="font-mono uppercase">{l.language}</span>
                  <span className="text-slate-500">·</span>
                  <span className="text-ciDark dark:text-emerald-200">{l.count.toLocaleString('fr-FR')}</span>
                </span>
              ))}
              {data.top_languages.length === 0 && (
                <span className="text-sm text-slate-500">Pas de donnée linguistique disponible.</span>
              )}
            </div>
          </article>

          <div className="card p-4 bg-sky-50 border-sky-200 text-sky-900 text-xs flex items-start gap-2">
            <Info className="h-4 w-4 mt-0.5 shrink-0" />
            <p>
              Toutes les statistiques sont calculées sur le serveur EpiTrace à partir de la
              table <code className="font-mono">PageVisit</code>. Aucun cookie tiers n'est
              posé côté visiteur. Les visites qualifiées comme bot (Googlebot, uptime, etc.)
              sont marquées automatiquement et exclues par défaut.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------- */

function Kpi({
  label, value, icon, accent, hint, pulse,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  accent: 'ciOrange' | 'ciGreen' | 'ciDark' | 'ciGold';
  hint?: string;
  pulse?: boolean;
}) {
  const color =
    accent === 'ciOrange' ? 'text-ciOrange'
    : accent === 'ciGreen' ? 'text-ciGreen'
    : accent === 'ciDark' ? 'text-ciDark dark:text-emerald-200'
    : 'text-ciGold';
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between text-slate-500 text-xs uppercase tracking-wide">
        <span>{label}</span>
        <span className={`relative ${color}`}>
          {icon}
          {pulse && value > 0 && (
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ciOrange opacity-70"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-ciOrange"></span>
            </span>
          )}
        </span>
      </div>
      <div className={`mt-2 font-display text-3xl font-black ${color}`}>{value.toLocaleString('fr-FR')}</div>
      {hint && <div className="text-[11px] text-slate-400 mt-1">{hint}</div>}
    </div>
  );
}

function MiniStat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3">
      <div className="text-[10px] uppercase tracking-wide text-slate-500 font-bold">{label}</div>
      <div className="mt-1 font-display text-xl font-black text-ciDark dark:text-emerald-100">
        {value}
      </div>
      {hint && <div className="text-[10px] text-slate-400">{hint}</div>}
    </div>
  );
}

function HeatLegend({ max }: { max: number }) {
  return (
    <div className="flex items-center gap-2 text-[10px] text-slate-500">
      <span>0</span>
      <div className="flex gap-0.5">
        <div className="w-4 h-3 rounded bg-slate-100 dark:bg-slate-800" />
        <div className="w-4 h-3 rounded bg-emerald-200 dark:bg-emerald-800/60" />
        <div className="w-4 h-3 rounded bg-emerald-400 dark:bg-emerald-700" />
        <div className="w-4 h-3 rounded bg-ciOrange" />
        <div className="w-4 h-3 rounded bg-rose-500" />
      </div>
      <span>{max.toLocaleString('fr-FR')}</span>
    </div>
  );
}
