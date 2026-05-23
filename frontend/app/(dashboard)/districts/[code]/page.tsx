'use client';

/**
 * /dashboard/districts/[code] — Détail d'une zone sanitaire.
 *
 * Affiche :
 *   - Breadcrumb hiérarchique (National → PRES → Région → ... → zone courante)
 *   - KPIs : voyageurs / alertes / quarantines / check-ins (agrégés sur tous
 *     les descendants si c'est une zone parent)
 *   - Mini-graphiques : répartition par sévérité d'alerte + statut quarantaine
 *   - Liste des sous-zones (enfants directs)
 *   - Lien "Voir sur la carte"
 */

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  ChevronRight, Map, AlertTriangle, Users, HeartPulse,
  ClipboardCheck, ArrowLeft, MapPin, ShieldAlert,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface BreadcrumbItem { code: string; name: string; level: string }
interface Child { code: string; name: string; level: string; risk_level: string; population?: number | null }
interface ZoneStats {
  zone: {
    code: string;
    name: string;
    level: string;
    level_display: string;
    risk_level: string;
    population?: number | null;
    has_geometry: boolean;
    n_descendants: number;
  };
  breadcrumb: BreadcrumbItem[];
  period_days: number;
  kpis: {
    travelers_total: number;
    travelers_recent: number;
    alerts_total: number;
    alerts_open: number;
    alerts_critical: number;
    quarantines_total: number;
    quarantines_active: number;
    quarantines_completed: number;
    checkins: number;
    checkins_symptomatic: number;
  };
  by_severity: { severity: string; n: number }[];
  by_quarantine_status: { status: string; n: number }[];
  children: Child[];
}

const LEVEL_COLOR: Record<string, string> = {
  country: '#0B1820', pres: '#FF7F00', region: '#009E60',
  district: '#0EA5E9', commune: '#7C3AED', quartier: '#94A3B8',
};

const SEVERITY_COLOR: Record<string, string> = {
  info: '#94A3B8', low: '#10B981', medium: '#F59E0B', high: '#EF4444', critical: '#7F1D1D',
};

const QR_STATUS_LABEL: Record<string, string> = {
  active: 'Active', extended: 'Prolongée', completed: 'Terminée',
  broken: 'Rompue', cancelled: 'Annulée',
};

export default function ZoneDetailPage() {
  const params = useParams<{ code: string }>();
  const code = params?.code;
  const [data, setData] = useState<ZoneStats | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    api.get<ZoneStats>(`/geo/zones/${code}/stats/?days=${days}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  }, [code, days]);

  if (loading) return <div className="card p-10 text-center text-slate-400">Chargement...</div>;
  if (err) return <div className="card p-6 text-rose-600">{err}</div>;
  if (!data) return null;

  const { zone, breadcrumb, kpis, by_severity, by_quarantine_status, children } = data;

  return (
    <div className="space-y-6">
      {/* Bouton retour + breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-500 flex-wrap">
        <Link href="/districts" className="inline-flex items-center gap-1 hover:text-emerald-600">
          <ArrowLeft className="h-4 w-4" /> Toutes les zones
        </Link>
        {breadcrumb.slice(0, -1).map((b) => (
          <span key={b.code} className="inline-flex items-center gap-1">
            <ChevronRight className="h-3 w-3" />
            <Link href={`/districts/${b.code}`} className="hover:text-emerald-600">{b.name}</Link>
          </span>
        ))}
      </div>

      {/* En-tête de la zone */}
      <header className="card p-6 flex flex-col md:flex-row md:items-center gap-4">
        <div
          className="h-14 w-14 rounded-2xl grid place-items-center text-white shrink-0"
          style={{ backgroundColor: LEVEL_COLOR[zone.level] || '#64748B' }}
        >
          <MapPin className="h-7 w-7" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs uppercase tracking-widest font-bold" style={{ color: LEVEL_COLOR[zone.level] }}>
            {zone.level_display}
          </div>
          <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100">
            {zone.name}
          </h1>
          <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-3">
            <span className="font-mono">{zone.code}</span>
            {zone.population != null && <span>👥 {zone.population.toLocaleString('fr-FR')} habitants</span>}
            {zone.n_descendants > 0 && <span>📊 {zone.n_descendants} sous-zone{zone.n_descendants > 1 ? 's' : ''}</span>}
            {zone.has_geometry && <span className="text-emerald-600">🗺 Géométrie disponible</span>}
          </div>
        </div>
        <div className="flex gap-2">
          {zone.has_geometry && (
            <Link
              href={`/cartographie?zone=${zone.code}`}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 text-white px-4 py-2 text-sm font-semibold hover:bg-emerald-700"
            >
              <Map className="h-4 w-4" /> Voir sur la carte
            </Link>
          )}
        </div>
      </header>

      {/* Sélecteur période */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-500">Période :</span>
        {[7, 30, 90, 365].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1 rounded-lg border text-xs font-semibold transition ${
              days === d
                ? 'bg-ciDark text-white border-ciDark'
                : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-900'
            }`}
          >
            {d === 365 ? '1 an' : `${d} jours`}
          </button>
        ))}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi icon={<Users />} label="Voyageurs" value={kpis.travelers_total} sub={`${kpis.travelers_recent} récents`} tone="emerald" />
        <Kpi icon={<AlertTriangle />} label="Alertes ouvertes" value={kpis.alerts_open} sub={`${kpis.alerts_critical} critiques`} tone={kpis.alerts_critical > 0 ? 'rose' : 'amber'} />
        <Kpi icon={<HeartPulse />} label="Suivis actifs" value={kpis.quarantines_active} sub={`${kpis.quarantines_total} cumulés`} tone="orange" />
        <Kpi icon={<ClipboardCheck />} label="Check-ins" value={kpis.checkins} sub={`${kpis.checkins_symptomatic} symptomatiques`} tone="sky" />
      </div>

      {/* Bandeau alerte si critique */}
      {kpis.alerts_critical > 0 && (
        <div className="card p-4 border-rose-200 bg-rose-50/40 dark:bg-rose-950/30 dark:border-rose-900 flex items-start gap-3">
          <ShieldAlert className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-sm text-rose-800 dark:text-rose-200">
            <strong>{kpis.alerts_critical} alerte{kpis.alerts_critical > 1 ? 's' : ''} critique{kpis.alerts_critical > 1 ? 's' : ''}</strong> ouverte{kpis.alerts_critical > 1 ? 's' : ''} sur cette zone.{' '}
            <Link href="/alertes" className="underline">Voir le détail →</Link>
          </div>
        </div>
      )}

      {/* Graphiques répartition */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="font-display font-bold text-sm mb-3 text-ciDark dark:text-emerald-100">
            Répartition des alertes par sévérité
          </h3>
          {by_severity.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">Aucune alerte sur la période.</p>
          ) : (
            <div className="space-y-2">
              {by_severity.map((row) => {
                const max = Math.max(...by_severity.map((r) => r.n));
                const pct = max > 0 ? (row.n / max) * 100 : 0;
                const color = SEVERITY_COLOR[(row.severity || '').toLowerCase()] || '#64748B';
                return (
                  <div key={row.severity} className="text-xs">
                    <div className="flex justify-between mb-1">
                      <span className="capitalize font-medium">{row.severity || 'inconnu'}</span>
                      <span className="font-mono text-slate-500">{row.n}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="card p-5">
          <h3 className="font-display font-bold text-sm mb-3 text-ciDark dark:text-emerald-100">
            Statut des suivis (quarantaines)
          </h3>
          {by_quarantine_status.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">Aucun suivi sur la période.</p>
          ) : (
            <div className="space-y-2">
              {by_quarantine_status.map((row) => {
                const max = Math.max(...by_quarantine_status.map((r) => r.n));
                const pct = max > 0 ? (row.n / max) * 100 : 0;
                const isActive = row.status === 'active' || row.status === 'extended';
                return (
                  <div key={row.status} className="text-xs">
                    <div className="flex justify-between mb-1">
                      <span className="font-medium">{QR_STATUS_LABEL[row.status] || row.status}</span>
                      <span className="font-mono text-slate-500">{row.n}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: isActive ? '#F59E0B' : '#94A3B8' }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Sous-zones */}
      {children.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-display font-bold text-sm text-ciDark dark:text-emerald-100">
              {children.length} sous-zone{children.length > 1 ? 's' : ''} directe{children.length > 1 ? 's' : ''}
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2 text-left">Nom</th>
                  <th className="px-4 py-2 text-left">Niveau</th>
                  <th className="px-4 py-2 text-left">Risque</th>
                  <th className="px-4 py-2 text-right">Population</th>
                  <th className="px-4 py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {children.map((c) => (
                  <tr key={c.code} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/40">
                    <td className="px-4 py-2 font-medium">
                      <Link href={`/districts/${c.code}`} className="hover:text-emerald-600">{c.name}</Link>
                    </td>
                    <td className="px-4 py-2 text-xs">
                      <span
                        className="inline-flex items-center rounded-full px-2 py-0.5 text-white font-semibold"
                        style={{ backgroundColor: LEVEL_COLOR[c.level] || '#64748B' }}
                      >
                        {c.level}
                      </span>
                    </td>
                    <td className="px-4 py-2 capitalize text-xs">{c.risk_level}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs">
                      {c.population != null ? c.population.toLocaleString('fr-FR') : '—'}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Link href={`/districts/${c.code}`} className="text-emerald-600 hover:underline text-xs">
                        Détail →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({
  icon, label, value, sub, tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  sub?: string;
  tone: 'emerald' | 'rose' | 'amber' | 'orange' | 'sky';
}) {
  const tones = {
    emerald: 'from-emerald-50 to-teal-50 text-emerald-700 border-emerald-200/60',
    rose: 'from-rose-50 to-pink-50 text-rose-700 border-rose-200/60',
    amber: 'from-amber-50 to-yellow-50 text-amber-700 border-amber-200/60',
    orange: 'from-orange-50 to-amber-50 text-orange-700 border-orange-200/60',
    sky: 'from-sky-50 to-blue-50 text-sky-700 border-sky-200/60',
  };
  return (
    <div className={`p-4 rounded-2xl border bg-gradient-to-br ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide font-bold opacity-80">{label}</span>
        <span className="opacity-50">{icon}</span>
      </div>
      <div className="mt-2 font-display text-3xl font-black">{value.toLocaleString('fr-FR')}</div>
      {sub && <div className="text-[10px] opacity-70 mt-0.5">{sub}</div>}
    </div>
  );
}
