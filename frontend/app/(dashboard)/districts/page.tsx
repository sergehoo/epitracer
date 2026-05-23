'use client';

/**
 * /dashboard/districts — Hub de gestion des zones sanitaires.
 *
 * Affiche la hiérarchie des HealthZone (PRES / Région / District / Commune /
 * Quartier) avec stats globales en haut, filtres dynamiques par niveau,
 * recherche, pagination et boutons d'action (détail / voir sur carte).
 */

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  Building2, Eye, Map, ShieldCheck, Filter, ChevronLeft, ChevronRight,
  Search, Layers,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface Zone {
  id: number;
  code: string;
  name: string;
  level: string;
  risk_level: string;
  population?: number | null;
  parent?: number | null;
}

interface PageResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const LEVELS = [
  { value: '',         label: 'Tous niveaux',     color: '#64748B' },
  { value: 'country',  label: 'National',         color: '#0B1820' },
  { value: 'pres',     label: 'PRES',             color: '#FF7F00' },
  { value: 'region',   label: 'Régions',          color: '#009E60' },
  { value: 'district', label: 'Districts',        color: '#0EA5E9' },
  { value: 'commune',  label: 'Communes',         color: '#7C3AED' },
  { value: 'quartier', label: 'Quartiers',        color: '#94A3B8' },
];

const RISK_COLORS: Record<string, string> = {
  low: 'badge-low', moderate: 'badge-moderate', high: 'badge-high', red: 'badge-critical',
};

export default function DistrictsPage() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Filtres
  const [level, setLevel] = useState<string>('district');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  // Stats globales (compteurs par niveau)
  const [countsByLevel, setCountsByLevel] = useState<Record<string, number>>({});

  // Charge les compteurs globaux une fois
  useEffect(() => {
    Promise.all(
      LEVELS.filter((l) => l.value).map((l) =>
        api.get(`/geo/zones/?level=${l.value}&page_size=1`)
          .then((r) => [l.value, r.data.count ?? (r.data.results || r.data).length] as const)
          .catch(() => [l.value, 0] as const)
      )
    ).then((entries) => {
      setCountsByLevel(Object.fromEntries(entries));
    });
  }, []);

  // Charge la liste filtrée
  useEffect(() => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
    });
    if (level) params.set('level', level);
    if (search) params.set('search', search);

    api.get<PageResponse<Zone>>(`/geo/zones/?${params}`)
      .then((r) => {
        const data = r.data;
        if (Array.isArray(data)) {
          setZones(data);
          setTotalCount(data.length);
        } else {
          setZones(data.results || []);
          setTotalCount(data.count || 0);
        }
      })
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  }, [level, search, page]);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  // Stats KPIs
  const totalZones = useMemo(
    () => Object.values(countsByLevel).reduce((s, n) => s + n, 0),
    [countsByLevel],
  );

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <header className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Pyramide sanitaire
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100">
          Zones sanitaires
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl">
          Hiérarchie complète : National → PRES → Région → District → Commune → Quartier.
          Source : Arrêté n° 00203/MSHPCMU du 02/05/2023 et découpage administratif CI 2011.
        </p>
      </header>

      {/* KPIs par niveau */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {LEVELS.filter((l) => l.value && l.value !== 'country').map((l) => {
          const n = countsByLevel[l.value] ?? 0;
          const active = level === l.value;
          return (
            <button
              key={l.value}
              onClick={() => { setLevel(l.value); setPage(1); }}
              className={`card p-3 text-left transition hover:shadow-md ${active ? 'ring-2 ring-offset-2 ring-ciOrange' : ''}`}
              style={{ borderLeft: `4px solid ${l.color}` }}
            >
              <div className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold">
                {l.label}
              </div>
              <div className="font-display text-2xl font-bold mt-1">{n}</div>
            </button>
          );
        })}
      </div>
      <div className="text-xs text-slate-500">
        Total zones : <strong>{totalZones}</strong>
        {' · '}
        <Link href="/cartographie" className="text-emerald-600 hover:underline inline-flex items-center gap-1">
          <Map className="h-3 w-3" /> Voir sur la carte
        </Link>
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-slate-500 mb-1">Recherche</label>
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Nom de la zone, code..."
              className="w-full pl-9 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Niveau</label>
          <select
            value={level}
            onChange={(e) => { setLevel(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            {LEVELS.map((l) => (
              <option key={l.value || 'all'} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>
        <div className="ml-auto text-xs text-slate-500 self-end">
          {totalCount} zones · page {page}/{totalPages}
        </div>
      </div>

      {err && <div className="card p-6 text-rose-600">{err}</div>}

      {/* Listing */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 text-left">Nom</th>
                <th className="px-4 py-3 text-left">Niveau</th>
                <th className="px-4 py-3 text-left">Code</th>
                <th className="px-4 py-3 text-left">Risque</th>
                <th className="px-4 py-3 text-right">Population</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">Chargement...</td></tr>
              )}
              {!loading && zones.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">
                  Aucune zone trouvée avec ces filtres.
                </td></tr>
              )}
              {!loading && zones.map((z) => {
                const lvl = LEVELS.find((l) => l.value === z.level);
                return (
                  <tr key={z.code} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/40">
                    <td className="px-4 py-3 font-medium">
                      <Link href={`/districts/${z.code}`} className="hover:text-emerald-600">
                        {z.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold text-white"
                        style={{ backgroundColor: lvl?.color || '#64748B' }}
                      >
                        {lvl?.label.replace('s', '') || z.level}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{z.code}</td>
                    <td className="px-4 py-3">
                      <span className={RISK_COLORS[z.risk_level] || 'badge-low'}>{z.risk_level}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {z.population != null ? z.population.toLocaleString('fr-FR') : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          href={`/districts/${z.code}`}
                          title="Détail & statistiques"
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>
                        <Link
                          href={`/cartographie?zone=${z.code}`}
                          title="Voir sur la carte"
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        >
                          <Map className="h-4 w-4" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-slate-100 dark:border-slate-800 text-sm">
            <div className="text-slate-500">
              {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, totalCount)} sur {totalCount}
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
              >
                <ChevronLeft className="h-4 w-4" /> Précédent
              </button>
              <span className="text-xs text-slate-500 px-2">page {page} / {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
              >
                Suivant <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
