'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import {
  ArrowDown, ArrowUp, Eye, Globe2, Languages, MousePointerClick, Users,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

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
  };
  by_day: { date: string; count: number }[];
  top_countries: { country_code: string; country_name: string; count: number }[];
  top_paths: { path: string; count: number }[];
  by_portal: { portal: string; count: number }[];
  top_languages: { language: string; count: number }[];
  generated_at: string;
}

const PORTAL_LABEL: Record<string, string> = {
  public: 'Portail public',
  admin: 'Portail admin',
  api: 'API',
};

const FLAG_FALLBACK = '🏳️';
function flag(code: string) {
  if (!code || code.length !== 2) return FLAG_FALLBACK;
  const A = 0x1f1e6;
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => A + c.charCodeAt(0) - 65));
}

export default function VisitsPage() {
  const [days, setDays] = useState(30);
  const [portal, setPortal] = useState<'' | 'public' | 'admin' | 'api'>('');
  const [data, setData] = useState<OverviewResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = (d: number, p: string) => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams({ days: String(d) });
    if (p) params.set('portal', p);
    api
      .get<OverviewResp>(`/analytics/visits/overview/?${params.toString()}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(days, portal); }, [days, portal]);

  const trendUp = (data?.kpi.trend_pct ?? 0) >= 0;

  const topPathMax = useMemo(
    () => Math.max(1, ...(data?.top_paths ?? []).map((p) => p.count)),
    [data],
  );
  const topCountryMax = useMemo(
    () => Math.max(1, ...(data?.top_countries ?? []).map((p) => p.count)),
    [data],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Analytics
          </div>
          <h1 className="font-display text-3xl font-black">Visites de la plateforme</h1>
          <p className="text-sm text-slate-500 mt-1">
            Trafic, tendance, pays d'origine et pages les plus consultées.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            className="select max-w-[180px]"
            value={portal}
            onChange={(e) => setPortal(e.target.value as any)}
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
          {/* KPIs */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Kpi
              label="Aujourd'hui"
              value={data.kpi.today}
              icon={<Eye className="h-5 w-5" />}
              accent="ciOrange"
            />
            <Kpi
              label="Cette semaine"
              value={data.kpi.this_week}
              icon={<MousePointerClick className="h-5 w-5" />}
              accent="ciGreen"
            />
            <Kpi
              label="Ce mois-ci"
              value={data.kpi.this_month}
              icon={<Globe2 className="h-5 w-5" />}
              accent="ciDark"
            />
            <Kpi
              label="Total cumulé"
              value={data.kpi.total}
              icon={<Users className="h-5 w-5" />}
              accent="ciGold"
            />
          </div>

          {/* Tendance et chiffres-clés période */}
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
              </div>
              <div className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ${trendUp ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                {trendUp ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
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
                    formatter={(v: any) => [v, 'Visites']}
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

            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <Mini label="Sessions uniques" value={data.kpi.unique_sessions_period} />
              <Mini label="Période précédente" value={data.kpi.previous_period} />
              <Mini label="Rapport actualisé" value={new Date(data.generated_at).toLocaleTimeString('fr-FR')} text />
              <Mini label="Bots exclus" value={data.exclude_bots ? 'Oui' : 'Non'} text />
            </div>
          </article>

          {/* Top pays + Top pages */}
          <div className="grid lg:grid-cols-2 gap-6">
            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Globe2 className="h-5 w-5 text-ciOrange" /> Top pays / origines
              </h3>
              {data.top_countries.length === 0 ? (
                <p className="text-sm text-slate-500 mt-3">Aucune donnée géographique sur la période.</p>
              ) : (
                <ul className="mt-4 space-y-2.5">
                  {data.top_countries.map((c) => (
                    <li key={c.country_code}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="flex items-center gap-2">
                          <span className="text-lg leading-none">{flag(c.country_code)}</span>
                          <span className="font-semibold">{c.country_name || c.country_code}</span>
                          <span className="text-xs text-slate-400">({c.country_code})</span>
                        </span>
                        <span className="font-bold text-ciDark">{c.count}</span>
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
                <MousePointerClick className="h-5 w-5 text-ciGreen" /> Pages les plus visitées
              </h3>
              {data.top_paths.length === 0 ? (
                <p className="text-sm text-slate-500 mt-3">Aucune visite sur la période.</p>
              ) : (
                <ul className="mt-4 space-y-2.5">
                  {data.top_paths.map((p) => (
                    <li key={p.path}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-mono text-xs truncate max-w-[60%]">{p.path}</span>
                        <span className="font-bold text-ciDark">{p.count}</span>
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
          </div>

          {/* Répartition portail + langues */}
          <div className="grid lg:grid-cols-2 gap-6">
            <article className="card p-6">
              <h3 className="font-display text-lg font-black">Répartition par portail</h3>
              <ul className="mt-4 space-y-3">
                {data.by_portal.map((p) => (
                  <li key={p.portal} className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-slate-900 px-4 py-3">
                    <span className="font-semibold">{PORTAL_LABEL[p.portal] || p.portal}</span>
                    <span className="font-black text-ciOrange">{p.count}</span>
                  </li>
                ))}
                {data.by_portal.length === 0 && <li className="text-sm text-slate-500">—</li>}
              </ul>
            </article>

            <article className="card p-6">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Languages className="h-5 w-5 text-ciOrange" /> Langues des visiteurs
              </h3>
              <div className="mt-4 flex flex-wrap gap-2">
                {data.top_languages.map((l) => (
                  <span key={l.language} className="badge-low">
                    {l.language} · {l.count}
                  </span>
                ))}
                {data.top_languages.length === 0 && (
                  <span className="text-sm text-slate-500">Pas de donnée linguistique disponible.</span>
                )}
              </div>
            </article>
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({
  label, value, icon, accent,
}: { label: string; value: number; icon: React.ReactNode; accent: 'ciOrange' | 'ciGreen' | 'ciDark' | 'ciGold' }) {
  const color =
    accent === 'ciOrange' ? 'text-ciOrange'
    : accent === 'ciGreen' ? 'text-ciGreen'
    : accent === 'ciDark' ? 'text-ciDark dark:text-emerald-200'
    : 'text-ciGold';
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between text-slate-500 text-xs uppercase tracking-wide">
        <span>{label}</span>
        <span className={color}>{icon}</span>
      </div>
      <div className={`mt-2 font-display text-3xl font-black ${color}`}>{value.toLocaleString('fr-FR')}</div>
    </div>
  );
}

function Mini({ label, value, text }: { label: string; value: any; text?: boolean }) {
  return (
    <div className="rounded-xl bg-slate-50 dark:bg-slate-900 p-3">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 font-bold ${text ? 'text-slate-700 dark:text-slate-200' : 'text-ciDark dark:text-emerald-200'}`}>
        {typeof value === 'number' ? value.toLocaleString('fr-FR') : value}
      </div>
    </div>
  );
}
