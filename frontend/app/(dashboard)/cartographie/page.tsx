'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';
import {
  Activity, Download, Filter, Layers, MapPin, RefreshCcw, Search, X,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import type { HeatPoint } from '@/components/dashboard/MapView';

const MapView = dynamic(() => import('@/components/dashboard/MapView').then((m) => m.MapView), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full grid place-items-center text-slate-400 text-sm">
      Chargement de la carte…
    </div>
  ),
});

interface EntryPoint { id: number; name: string; code: string; type?: string }

const STATUS_OPTS = [
  { value: '',           label: 'Tous statuts',     color: '#94A3B8' },
  { value: 'cleared',    label: 'Autorisé',         color: '#10B981' },
  { value: 'monitoring', label: 'Surveillance',     color: '#0EA5E9' },
  { value: 'quarantine', label: 'Quarantaine',      color: '#F59E0B' },
  { value: 'suspect',    label: 'Cas suspect',      color: '#EF4444' },
  { value: 'confirmed',  label: 'Cas confirmé',     color: '#7F1D1D' },
  { value: 'recovered',  label: 'Rétabli',          color: '#6366F1' },
  { value: 'deceased',   label: 'Décédé',           color: '#111827' },
];

const RISK_OPTS = [
  { value: '',         label: 'Tous risques' },
  { value: 'low',      label: 'Faible' },
  { value: 'moderate', label: 'Modéré' },
  { value: 'high',     label: 'Élevé' },
  { value: 'critical', label: 'Critique' },
];

export default function CartoPage() {
  const [points, setPoints] = useState<HeatPoint[]>([]);
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Filtres
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [entryFilter, setEntryFilter] = useState('');
  const [showEntryPoints, setShowEntryPoints] = useState(true);
  const [panelOpen, setPanelOpen] = useState(true);

  const load = () => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    if (entryFilter)  params.set('entry_point', entryFilter);
    Promise.allSettled([
      api.get(`/analytics/heatmap/${params.toString() ? '?' + params.toString() : ''}`),
      api.get('/geo/entry-points/?is_active=true'),
    ])
      .then(([h, e]) => {
        if (h.status === 'fulfilled') setPoints((h.value.data as HeatPoint[]) || []);
        else setErr(extractApiError(h.reason));
        if (e.status === 'fulfilled') {
          const data: any = e.value.data;
          setEntryPoints(data.results || data || []);
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [statusFilter, entryFilter]);

  // Filtres côté client (search + risque)
  const filtered = useMemo(() => {
    return points.filter((p) => {
      if (riskFilter && p.risk_level !== riskFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const hay = [p.full_name, p.public_id, p.city, p.entry_point, p.nationality]
          .filter(Boolean).join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [points, riskFilter, search]);

  // Statistiques de la carte
  const stats = useMemo(() => {
    const byStatus: Record<string, number> = {};
    const byRisk: Record<string, number> = {};
    filtered.forEach((p) => {
      byStatus[p.status] = (byStatus[p.status] || 0) + 1;
      if (p.risk_level) byRisk[p.risk_level] = (byRisk[p.risk_level] || 0) + 1;
    });
    return { total: filtered.length, byStatus, byRisk };
  }, [filtered]);

  const exportCsv = () => {
    const header = ['public_id', 'full_name', 'status', 'risk_level', 'risk_score',
      'entry_point', 'nationality', 'city', 'arrival_date', 'lat', 'lng'];
    const rows = filtered.map((p) =>
      header.map((k) => JSON.stringify((p as any)[k] ?? '')).join(','),
    );
    const csv = [header.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `cartographie-voyageurs-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  return (
    /* Hauteur fixe pour étendre la carte sur tout l'espace disponible */
    <div className="h-[calc(100vh-4rem-3rem)] flex flex-col gap-3 -m-6 lg:-m-8 p-6 lg:p-8">
      {/* En-tête compact */}
      <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-ciOrange font-bold">
            Cartographie nationale
          </div>
          <h1 className="font-display text-2xl md:text-3xl font-black leading-tight">
            Répartition géographique des voyageurs
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher nom, ID, ville…"
              className="input pl-9 min-w-[260px]"
            />
          </div>
          <button onClick={load} className="btn-outline text-sm" title="Actualiser">
            <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Actualiser
          </button>
          <button onClick={exportCsv} className="btn-outline text-sm" title="Exporter CSV">
            <Download className="h-4 w-4" /> CSV
          </button>
        </div>
      </header>

      {err && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 text-rose-700 px-4 py-2 text-sm">
          {err}
        </div>
      )}

      {/* Zone carte + panneau filtres */}
      <div className="relative flex-1 min-h-[480px] rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 shadow-card">
        <div className="absolute inset-0">
          <MapView points={filtered} showEntryPoints={showEntryPoints} />
        </div>

        {/* Panneau filtres flottant — z-[1100] pour passer au-dessus des panes Leaflet (max 1000).
            max-h limite à 100% moins la hauteur réservée à la légende en bas-gauche. */}
        {panelOpen ? (
          <aside className="absolute top-3 left-3 z-[1100] w-[280px] max-h-[calc(100%-7rem)] overflow-y-auto rounded-2xl bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-200 dark:border-slate-800 shadow-xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
              <div className="font-display text-sm font-black flex items-center gap-2">
                <Filter className="h-4 w-4 text-ciOrange" /> Filtres
              </div>
              <button
                onClick={() => setPanelOpen(false)}
                className="text-slate-400 hover:text-slate-700"
                aria-label="Fermer le panneau"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* Statut */}
              <div>
                <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1.5">
                  Statut sanitaire
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {STATUS_OPTS.map((s) => (
                    <button
                      key={s.value}
                      onClick={() => setStatusFilter(s.value)}
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold border transition ${
                        statusFilter === s.value
                          ? 'bg-ciDark text-white border-ciDark'
                          : 'bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-ciOrange/60'
                      }`}
                    >
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ background: s.color }}
                      />
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Risque */}
              <div>
                <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1.5">
                  Niveau de risque
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {RISK_OPTS.map((r) => (
                    <button
                      key={r.value}
                      onClick={() => setRiskFilter(r.value)}
                      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold border transition ${
                        riskFilter === r.value
                          ? 'bg-ciOrange text-white border-ciOrange'
                          : 'bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-ciOrange/60'
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Point d'entrée */}
              <div>
                <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1.5">
                  Point d'entrée
                </div>
                <select
                  value={entryFilter}
                  onChange={(e) => setEntryFilter(e.target.value)}
                  className="select"
                >
                  <option value="">Tous les points</option>
                  {entryPoints.map((e) => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>

              {/* Calques */}
              <div>
                <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1.5">
                  <Layers className="inline h-3 w-3 mr-1" /> Calques
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="accent-ciOrange"
                    checked={showEntryPoints}
                    onChange={(e) => setShowEntryPoints(e.target.checked)}
                  />
                  Points d'entrée (aéroports, ports, frontières)
                </label>
              </div>

              {/* Reset */}
              {(statusFilter || riskFilter || entryFilter || search) && (
                <button
                  onClick={() => {
                    setStatusFilter('');
                    setRiskFilter('');
                    setEntryFilter('');
                    setSearch('');
                  }}
                  className="w-full inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <X className="h-3 w-3" /> Réinitialiser les filtres
                </button>
              )}
            </div>
          </aside>
        ) : (
          <button
            onClick={() => setPanelOpen(true)}
            className="absolute top-3 left-3 z-[1100] inline-flex items-center gap-2 rounded-xl bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-200 dark:border-slate-800 shadow-xl px-3 py-2 text-xs font-bold text-ciDark dark:text-emerald-200"
          >
            <Filter className="h-4 w-4 text-ciOrange" /> Filtres
          </button>
        )}

        {/* Stats overlay (bas-droite) */}
        <div className="absolute bottom-3 right-3 z-[1100] max-w-[280px] rounded-2xl bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-200 dark:border-slate-800 shadow-xl px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500">
                Voyageurs affichés
              </div>
              <div className="font-display text-2xl font-black text-ciDark dark:text-emerald-200 leading-none mt-0.5">
                {stats.total.toLocaleString('fr-FR')}
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-orange-50 dark:bg-orange-950/40 grid place-items-center text-ciOrange">
              <Activity className="h-5 w-5" />
            </div>
          </div>
          {Object.keys(stats.byStatus).length > 0 && (
            <ul className="mt-3 space-y-1 text-xs">
              {Object.entries(stats.byStatus).map(([k, v]) => {
                const opt = STATUS_OPTS.find((s) => s.value === k);
                return (
                  <li key={k} className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full" style={{ background: opt?.color || '#94A3B8' }} />
                      {opt?.label || k}
                    </span>
                    <span className="font-bold">{v}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Légende (bas-gauche) — compacte, max-w réduit pour ne pas mordre sous le panneau filtres */}
        <div className="absolute bottom-3 left-3 z-[1100] max-w-[260px] rounded-2xl bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-200 dark:border-slate-800 shadow-xl px-2.5 py-1.5 text-[10.5px]">
          <div className="font-bold text-slate-500 mb-1 flex items-center gap-1">
            <MapPin className="h-3 w-3 text-ciGreen" /> Légende
          </div>
          <ul className="flex flex-wrap gap-x-2.5 gap-y-0.5">
            {STATUS_OPTS.filter((s) => s.value).map((s) => (
              <li key={s.value} className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                {s.label}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
