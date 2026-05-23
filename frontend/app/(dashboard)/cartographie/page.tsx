'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Activity, Download, Filter, Layers, MapPin, RefreshCcw, Search, X,
  ShieldAlert,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import type { HeatPoint, ZoneCollection } from '@/components/dashboard/MapView';

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

const ZONE_LEVELS = [
  { value: '',         label: 'Tous niveaux' },
  { value: 'region',   label: 'Régions sanitaires (33)' },
  { value: 'district', label: 'Districts sanitaires' },
  { value: 'commune',  label: 'Communes' },
  { value: 'quartier', label: 'Quartiers' },
];

export default function CartoPage() {
  const sp = useSearchParams();
  const focusZone = sp.get('zone'); // permet le drill-down depuis /districts

  const [points, setPoints] = useState<HeatPoint[]>([]);
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([]);
  const [zones, setZones] = useState<ZoneCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingZones, setLoadingZones] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Filtres voyageurs
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [entryFilter, setEntryFilter] = useState('');

  // Filtres zones
  const [showZones, setShowZones] = useState(true);
  const [zoneLevel, setZoneLevel] = useState<string>('region');
  const [zonesColorBy, setZonesColorBy] = useState<'risk' | 'level'>('risk');

  // Calques généraux
  const [showEntryPoints, setShowEntryPoints] = useState(true);
  const [showTravelers, setShowTravelers] = useState(true);
  const [panelOpen, setPanelOpen] = useState(true);

  // Charge voyageurs + entry points
  const load = () => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    if (entryFilter)  params.set('entry_point', entryFilter);
    Promise.allSettled([
      api.get(`/analytics/heatmap/${params.toString() ? '?' + params.toString() : ''}`),
      api.get('/geo/entry-points/?is_active=true&page_size=100'),
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

  // Charge les zones GeoJSON (seulement si le calque est activé)
  const loadZones = (level: string) => {
    if (!showZones) {
      setZones(null);
      return;
    }
    setLoadingZones(true);
    const url = level
      ? `/geo/zones/geojson/?level=${level}`
      : '/geo/zones/geojson/';
    api.get(url)
      .then((r) => setZones(r.data as ZoneCollection))
      .catch(() => setZones(null))
      .finally(() => setLoadingZones(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [statusFilter, entryFilter]);
  useEffect(() => { loadZones(zoneLevel); /* eslint-disable-next-line */ }, [zoneLevel, showZones]);

  // Filtres côté client (search + risque)
  const filtered = useMemo(() => {
    if (!showTravelers) return [];
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
  }, [points, riskFilter, search, showTravelers]);

  // Stats
  const stats = useMemo(() => {
    const byStatus: Record<string, number> = {};
    filtered.forEach((p) => { byStatus[p.status] = (byStatus[p.status] || 0) + 1; });
    const zoneCount = zones?.features.length || 0;
    const zoneRedCount = zones?.features.filter((f) => ['red', 'critical', 'high'].includes(f.properties.risk_level)).length || 0;
    return { travelers: filtered.length, byStatus, zoneCount, zoneRedCount };
  }, [filtered, zones]);

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
    <div className="h-[calc(100vh-4rem-3rem)] flex flex-col gap-3 -m-3 sm:-m-6 lg:-m-8 p-3 sm:p-6 lg:p-8">
      {/* En-tête compact */}
      <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-ciOrange font-bold">
            Cartographie nationale
          </div>
          <h1 className="font-display text-xl md:text-3xl font-black leading-tight">
            Répartition géographique
            {focusZone && <span className="text-base font-bold text-emerald-600 ml-2">— Zone {focusZone}</span>}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher voyageur, ville…"
              className="input pl-9 min-w-[240px]"
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

      {/* Zone carte + panneau */}
      <div className="relative flex-1 min-h-[480px] rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 shadow-card">
        <div className="absolute inset-0">
          <MapView
            points={filtered}
            showEntryPoints={showEntryPoints}
            zones={zones}
            zonesColorBy={zonesColorBy}
            focusZoneCode={focusZone}
          />
        </div>

        {/* Panneau filtres flottant */}
        {panelOpen ? (
          <aside className="absolute top-3 left-3 z-[1100] w-[300px] max-h-[calc(100%-7rem)] overflow-y-auto rounded-2xl bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-200 dark:border-slate-800 shadow-xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
              <div className="font-display text-sm font-black flex items-center gap-2">
                <Filter className="h-4 w-4 text-ciOrange" /> Filtres & calques
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
              {/* ===== ZONES SANITAIRES ===== */}
              <div>
                <label className="flex items-center justify-between text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1.5">
                  <span className="flex items-center gap-1">
                    <Layers className="inline h-3 w-3" /> Zones sanitaires
                  </span>
                  <input
                    type="checkbox"
                    className="accent-ciOrange"
                    checked={showZones}
                    onChange={(e) => setShowZones(e.target.checked)}
                  />
                </label>
                {showZones && (
                  <div className="space-y-2">
                    <select
                      value={zoneLevel}
                      onChange={(e) => setZoneLevel(e.target.value)}
                      className="select text-sm"
                    >
                      {ZONE_LEVELS.map((l) => (
                        <option key={l.value || 'all'} value={l.value}>{l.label}</option>
                      ))}
                    </select>
                    <div className="flex gap-1">
                      <button
                        onClick={() => setZonesColorBy('risk')}
                        className={`flex-1 px-2 py-1.5 rounded-lg text-[11px] font-semibold border transition ${
                          zonesColorBy === 'risk'
                            ? 'bg-ciOrange text-white border-ciOrange'
                            : 'border-slate-200 dark:border-slate-700'
                        }`}
                      >
                        Par risque
                      </button>
                      <button
                        onClick={() => setZonesColorBy('level')}
                        className={`flex-1 px-2 py-1.5 rounded-lg text-[11px] font-semibold border transition ${
                          zonesColorBy === 'level'
                            ? 'bg-ciOrange text-white border-ciOrange'
                            : 'border-slate-200 dark:border-slate-700'
                        }`}
                      >
                        Par niveau
                      </button>
                    </div>
                    {loadingZones && (
                      <div className="text-[10px] text-slate-400 italic">Chargement des zones...</div>
                    )}
                    {zones && (
                      <div className="text-[10px] text-slate-500">
                        {zones.features.length} polygone{zones.features.length > 1 ? 's' : ''} affiché{zones.features.length > 1 ? 's' : ''}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <hr className="border-slate-100 dark:border-slate-800" />

              {/* ===== VOYAGEURS ===== */}
              <div>
                <label className="flex items-center justify-between text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1.5">
                  <span>Voyageurs</span>
                  <input
                    type="checkbox"
                    className="accent-ciOrange"
                    checked={showTravelers}
                    onChange={(e) => setShowTravelers(e.target.checked)}
                  />
                </label>
                {showTravelers && (
                  <>
                    <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mt-3 mb-1.5">
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
                          <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                          {s.label}
                        </button>
                      ))}
                    </div>

                    <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mt-3 mb-1.5">
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

                    <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mt-3 mb-1.5">
                      Point d'entrée
                    </div>
                    <select
                      value={entryFilter}
                      onChange={(e) => setEntryFilter(e.target.value)}
                      className="select text-sm"
                    >
                      <option value="">Tous les points</option>
                      {entryPoints.map((e) => (
                        <option key={e.id} value={e.id}>{e.name}</option>
                      ))}
                    </select>
                  </>
                )}
              </div>

              <hr className="border-slate-100 dark:border-slate-800" />

              {/* ===== AUTRES CALQUES ===== */}
              <div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="accent-ciOrange"
                    checked={showEntryPoints}
                    onChange={(e) => setShowEntryPoints(e.target.checked)}
                  />
                  📍 Points d'entrée
                </label>
              </div>

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
                  <X className="h-3 w-3" /> Réinitialiser
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
        <div className="absolute bottom-3 right-3 z-[1100] max-w-[280px] rounded-2xl bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-200 dark:border-slate-800 shadow-xl px-4 py-3 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500">
                Voyageurs affichés
              </div>
              <div className="font-display text-2xl font-black text-ciDark dark:text-emerald-200 leading-none mt-0.5">
                {stats.travelers.toLocaleString('fr-FR')}
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-orange-50 dark:bg-orange-950/40 grid place-items-center text-ciOrange">
              <Activity className="h-5 w-5" />
            </div>
          </div>
          {stats.zoneCount > 0 && (
            <div className="text-[11px] text-slate-500 border-t border-slate-100 dark:border-slate-800 pt-2 flex items-center justify-between">
              <span>🗺 {stats.zoneCount} zones</span>
              {stats.zoneRedCount > 0 && (
                <span className="text-rose-600 font-bold inline-flex items-center gap-1">
                  <ShieldAlert className="h-3 w-3" /> {stats.zoneRedCount} à risque
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
