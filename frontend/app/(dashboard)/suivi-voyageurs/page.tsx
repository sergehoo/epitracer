'use client';

/**
 * Dashboard admin — Suivi des voyageurs accompagnés.
 *
 * Page de pilotage pour les agents INHP / districts / points d'entrée.
 * Affiche les KPIs du jour (actifs, check-ins reçus, manqués 48h,
 * alertes ouvertes) + la liste des voyageurs en suivi actif avec
 * filtres et accès rapide à leur itinéraire.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Activity, AlertTriangle, Bell, MapPin, Search, Users } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface FollowupRow {
  public_id: string;
  full_name: string;
  phone: string;
  entry_point: string | null;
  started_on: string;
  day_index: number;
  total_days: number;
  last_check_date: string | null;
  last_check_feeling: 'ok' | 'symptom' | 'assistance' | null;
  has_symptoms: boolean;
  last_location_at: string | null;
  current_health_status: string;
}

interface OverviewPayload {
  kpis: {
    active: number;
    checked_today: number;
    missed_48h: number;
    open_alerts: number;
    with_recent_location: number;
  };
  rows: FollowupRow[];
}

const FEELING_LABELS: Record<string, string> = {
  ok: 'Tout va bien',
  symptom: 'Symptôme déclaré',
  assistance: 'Demande aide',
};

export default function SuiviVoyageursPage() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [onlyMissed, setOnlyMissed] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<OverviewPayload>('/admin/companion/followups/');
      setData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    return data.rows.filter((r) => {
      if (q) {
        const hay = `${r.public_id} ${r.full_name} ${r.entry_point ?? ''} ${r.phone ?? ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (onlyMissed) {
        if (!r.last_check_date) return true;
        const ageDays = (Date.now() - new Date(r.last_check_date).getTime()) / 86_400_000;
        if (ageDays < 2) return false;
      }
      return true;
    });
  }, [data, search, onlyMissed]);

  return (
    <div className="space-y-6">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Companion
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Suivi des voyageurs accompagnés
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Vue d'ensemble des voyageurs actuellement en période d'accompagnement sanitaire
          (21 jours). Les données de localisation sont consultées uniquement après
          consentement du voyageur ; chaque consultation est journalisée.
        </p>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Kpi icon={<Users className="h-5 w-5" />} label="Voyageurs actifs" value={data?.kpis.active ?? '—'} color="emerald" />
        <Kpi icon={<Bell className="h-5 w-5" />} label="Check-ins reçus aujourd'hui" value={data?.kpis.checked_today ?? '—'} color="emerald" />
        <Kpi icon={<AlertTriangle className="h-5 w-5" />} label="Manqués (>48h)" value={data?.kpis.missed_48h ?? '—'} color="amber" />
        <Kpi icon={<Activity className="h-5 w-5" />} label="Alertes ouvertes" value={data?.kpis.open_alerts ?? '—'} color="rose" />
        <Kpi icon={<MapPin className="h-5 w-5" />} label="Avec position (7j)" value={data?.kpis.with_recent_location ?? '—'} color="slate" />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
        <div className="relative flex-1">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Rechercher un voyageur (ID, nom, point d'entrée…)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={onlyMissed}
            onChange={(e) => setOnlyMissed(e.target.checked)}
          />
          Sans check-in depuis 48h
        </label>
      </div>

      {/* Tableau */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-left">
              <tr>
                <Th>Voyageur</Th>
                <Th>Jour</Th>
                <Th>Dernier check-in</Th>
                <Th>État</Th>
                <Th>Point d'entrée</Th>
                <Th>Dernière position</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={7} className="p-6 text-center text-slate-400">Chargement…</td></tr>
              )}
              {!loading && error && (
                <tr><td colSpan={7} className="p-6 text-center text-rose-600">{error}</td></tr>
              )}
              {!loading && !error && filtered.length === 0 && (
                <tr><td colSpan={7} className="p-8 text-center text-slate-400">Aucun voyageur ne correspond aux filtres.</td></tr>
              )}
              {filtered.map((r) => (
                <tr key={r.public_id} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50">
                  <Td>
                    <div className="font-semibold">{r.full_name}</div>
                    <div className="text-xs text-slate-500">{r.public_id} · {r.phone || '—'}</div>
                  </Td>
                  <Td>
                    <span className="px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold">
                      J{r.day_index + 1} / {r.total_days + 1}
                    </span>
                  </Td>
                  <Td>{r.last_check_date ? new Date(r.last_check_date).toLocaleDateString('fr-FR') : '—'}</Td>
                  <Td>
                    {r.last_check_feeling ? (
                      <span className={
                        r.last_check_feeling === 'assistance'
                          ? 'text-rose-700 font-semibold'
                          : r.last_check_feeling === 'symptom'
                          ? 'text-amber-700 font-semibold'
                          : 'text-emerald-700 font-semibold'
                      }>
                        {FEELING_LABELS[r.last_check_feeling]}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </Td>
                  <Td className="text-xs text-slate-600">{r.entry_point ?? '—'}</Td>
                  <Td className="text-xs text-slate-600">
                    {r.last_location_at ? formatDateTime(r.last_location_at) : '—'}
                  </Td>
                  <Td>
                    <Link
                      href={`/voyageurs/${r.public_id}/itineraire`}
                      className="text-xs text-ciOrange hover:underline font-semibold"
                    >
                      Itinéraire
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Kpi({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number | string; color: string }) {
  const colors: Record<string, string> = {
    emerald: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    amber: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    rose: 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300',
    slate: 'bg-slate-50 text-slate-700 dark:bg-slate-900 dark:text-slate-300',
  };
  return (
    <div className="card p-4">
      <div className={`inline-flex items-center justify-center h-10 w-10 rounded-xl mb-2 ${colors[color]}`}>
        {icon}
      </div>
      <div className="text-2xl font-display font-black text-ciDark dark:text-emerald-100">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-500">{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-3 ${className}`}>{children}</td>;
}
