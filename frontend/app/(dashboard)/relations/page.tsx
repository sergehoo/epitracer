'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  Filter, Home, MapPin, Pause, Phone, Plane, Play, RefreshCcw, Search, Users, X,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import type { ClusterShape, ClusterType } from '@/components/dashboard/ForceGraph';

// D3 (180 KB) chargé uniquement quand la page Relations est ouverte.
// ssr:false évite l'évaluation côté serveur (Node sans canvas).
const ForceGraph = dynamic(
  () => import('@/components/dashboard/ForceGraph').then((m) => m.ForceGraph),
  { ssr: false, loading: () => <div className="h-[600px] animate-pulse bg-slate-100 dark:bg-slate-900 rounded-2xl" /> },
);

interface RelationsResp {
  clusters: ClusterShape[];
  stats: {
    total_travelers: number;
    total_clusters: number;
    by_type: Record<string, { clusters: number; members: number }>;
  };
}

/* ============================================================
   Config visuelle
   ============================================================ */
const TYPE_META: Record<ClusterType, { label: string; icon: React.ComponentType<any>; color: string }> = {
  flight:    { label: 'Vol',               icon: Plane,  color: '#F77F00' },
  phone:     { label: 'Téléphone',         icon: Phone,  color: '#0EA5E9' },
  origin:    { label: 'Provenance',        icon: MapPin, color: '#D4A017' },
  companion: { label: 'Cas-contact',       icon: Users,  color: '#EF4444' },
  residence: { label: 'Résidence Abidjan', icon: Home,   color: '#009B5A' },
};

const STATUS_LEGEND: { value: string; label: string; color: string }[] = [
  { value: 'cleared',    label: 'Autorisé',     color: '#10B981' },
  { value: 'monitoring', label: 'Surveillance', color: '#0EA5E9' },
  { value: 'quarantine', label: 'Quarantaine',  color: '#F59E0B' },
  { value: 'suspect',    label: 'Cas suspect',  color: '#EF4444' },
  { value: 'confirmed',  label: 'Cas confirmé', color: '#7F1D1D' },
];

/* ============================================================
   PAGE
   ============================================================ */
export default function RelationsPage() {
  const [data, setData] = useState<RelationsResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Filtres serveur
  const [search, setSearch] = useState('');
  const [minSize, setMinSize] = useState(2);
  const [days, setDays] = useState<string>('');

  // Filtres client
  const [typeFilter, setTypeFilter] = useState<Set<ClusterType>>(new Set());
  const [statusFilter, setStatusFilter] = useState<Set<string>>(new Set());
  const [topN, setTopN] = useState<number>(0);
  const [frozen, setFrozen] = useState(false);

  const load = () => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams();
    if (search.trim()) params.set('search', search.trim());
    if (minSize !== 2) params.set('min_size', String(minSize));
    if (days) params.set('days', days);
    api.get<RelationsResp>(`/surveillance/relations/?${params.toString()}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [minSize, days]);
  useEffect(() => {
    const id = setTimeout(load, 350);
    return () => clearTimeout(id);
    // eslint-disable-next-line
  }, [search]);

  // -----------------------------------------------------------
  // Filtrage CLIENT — supprime réellement clusters/voyageurs
  // -----------------------------------------------------------
  const visibleClusters: ClusterShape[] = useMemo(() => {
    if (!data) return [];
    let list = data.clusters;

    // (1) Filtre type (hubs) — supprime les clusters non sélectionnés
    if (typeFilter.size > 0) {
      list = list.filter((c) => typeFilter.has(c.type));
    }

    // (2) Filtre statut — supprime les voyageurs non sélectionnés
    if (statusFilter.size > 0) {
      list = list
        .map((c) => {
          const filteredMembers = c.members.filter((m) => statusFilter.has(m.status));
          const ids = new Set(filteredMembers.map((m) => m.public_id));
          const filteredPairs = c.pairs?.filter((p) => ids.has(p.a) && ids.has(p.b));
          return {
            ...c,
            members: filteredMembers,
            size: filteredMembers.length,
            pairs: filteredPairs,
          };
        })
        // On retire les clusters devenus vides ou sous le seuil
        .filter((c) => c.members.length >= Math.min(2, minSize));
    }

    // (3) Top N (plus gros clusters)
    if (topN > 0) {
      list = [...list].sort((a, b) => b.size - a.size).slice(0, topN);
    }
    return list;
  }, [data, typeFilter, statusFilter, topN, minSize]);

  const toggleType = (t: ClusterType) => {
    setTypeFilter((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };
  const toggleStatus = (s: string) => {
    setStatusFilter((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  const hasFilters = !!(typeFilter.size || statusFilter.size || search || minSize !== 2 || days || topN);

  return (
    <div className="space-y-5 animate-fade-up">
      {/* ============ Header ============ */}
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-ciOrange font-bold">
            Contact-tracing · réseau de relations
          </div>
          <h1 className="font-display text-3xl font-black">Mise en relation des voyageurs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Regroupements par vol, téléphone, pays de provenance, cas-contact déclaré et
            lieu de résidence à Abidjan.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFrozen((f) => !f)}
            className="btn-outline text-sm"
            title={frozen ? "Reprendre l'animation" : 'Figer le graphe (drag instantané)'}
          >
            {frozen ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            {frozen ? 'Animer' : 'Geler'}
          </button>
          <button onClick={load} className="btn-outline text-sm">
            <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Actualiser
          </button>
        </div>
      </header>

      {/* ============ Stats (cliquables → filtre type) ============ */}
      {data && (
        <section className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <StatBox
            label="Voyageurs analysés"
            value={data.stats.total_travelers}
            tone="dark"
            icon={<Users className="h-4 w-4" />}
          />
          {(Object.keys(TYPE_META) as ClusterType[]).map((t) => {
            const Meta = TYPE_META[t];
            const s = data.stats.by_type?.[t];
            const active = typeFilter.has(t);
            return (
              <StatBox
                key={t}
                label={Meta.label}
                value={s?.clusters || 0}
                sub={s ? `${s.members} voyageurs` : '0 voyageur'}
                tone="custom"
                customColor={Meta.color}
                icon={<Meta.icon className="h-4 w-4" />}
                active={active}
                onClick={() => toggleType(t)}
              />
            );
          })}
        </section>
      )}

      {/* ============ Barre de filtres complète ============ */}
      <section className="card p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[260px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher nom, public_id, vol, hôtel…"
              className="input pl-9"
            />
          </div>

          <select className="select max-w-[120px]" value={minSize} onChange={(e) => setMinSize(Number(e.target.value))}>
            <option value={2}>≥ 2</option>
            <option value={3}>≥ 3</option>
            <option value={5}>≥ 5</option>
            <option value={10}>≥ 10</option>
          </select>

          <select className="select max-w-[140px]" value={days} onChange={(e) => setDays(e.target.value)}>
            <option value="">Tout l'historique</option>
            <option value="7">7 derniers j.</option>
            <option value="14">14 derniers j.</option>
            <option value="30">30 derniers j.</option>
            <option value="90">90 derniers j.</option>
          </select>

          <select
            className="select max-w-[160px]"
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
            title="Affiche uniquement les N plus gros clusters pour soulager le rendu"
          >
            <option value={0}>Tous les clusters</option>
            <option value={20}>Top 20 clusters</option>
            <option value={50}>Top 50 clusters</option>
            <option value={100}>Top 100 clusters</option>
          </select>

          {hasFilters && (
            <button
              onClick={() => {
                setSearch(''); setMinSize(2); setDays('');
                setTypeFilter(new Set()); setStatusFilter(new Set());
                setTopN(0);
              }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <X className="h-3 w-3" /> Réinitialiser
            </button>
          )}
        </div>

        {/* Pills par type de hub */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mr-1">
            Hubs :
          </span>
          {(Object.keys(TYPE_META) as ClusterType[]).map((t) => {
            const M = TYPE_META[t];
            const active = typeFilter.has(t);
            return (
              <button
                key={t}
                onClick={() => toggleType(t)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full font-bold transition border ${
                  active ? 'text-white border-transparent shadow-sm' : 'text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-400'
                }`}
                style={active ? { background: M.color } : undefined}
                title={active ? `Cliquer pour retirer ${M.label}` : `Filtrer sur ${M.label}`}
              >
                <M.icon className="h-3.5 w-3.5" />
                {M.label}
              </button>
            );
          })}

          <span className="mx-2 h-3 w-px bg-slate-300" />

          <span className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mr-1">
            Statuts :
          </span>
          {STATUS_LEGEND.map((s) => {
            const active = statusFilter.has(s.value);
            return (
              <button
                key={s.value}
                onClick={() => toggleStatus(s.value)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full font-bold transition border ${
                  active ? 'text-white border-transparent shadow-sm' : 'text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-400'
                }`}
                style={active ? { background: s.color } : undefined}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full ring-2 ring-white"
                  style={{ background: active ? '#ffffff' : s.color }}
                />
                {s.label}
              </button>
            );
          })}
        </div>
      </section>

      {err && <div className="card p-6 text-rose-600">{err}</div>}

      {/* ============ Graphe full-width ============ */}
      {loading && !data ? (
        <div className="card p-10 animate-pulse h-[60vh]" />
      ) : data ? (
        <section className="space-y-2">
          <ForceGraph clusters={visibleClusters} height={760} frozen={frozen} />

          <div className="text-[11px] text-slate-500 px-1 flex flex-wrap gap-x-4 gap-y-1">
            <span>
              <Filter className="inline h-3 w-3 mr-1 -mt-0.5" />
              Molette pour zoomer · glisser pour déplacer · clic voyageur → fiche détaillée
            </span>
            <span>· {visibleClusters.length} cluster(s) affiché(s) sur {data.clusters.length}</span>
            {frozen && <span className="font-bold text-ciOrange">· Graphe figé</span>}
          </div>
        </section>
      ) : null}
    </div>
  );
}

/* ============================================================
   Sub-components
   ============================================================ */
function StatBox({
  label, value, sub, icon, tone, customColor, active, onClick,
}: {
  label: string;
  value: number;
  sub?: string;
  icon: React.ReactNode;
  tone: 'dark' | 'custom';
  customColor?: string;
  active?: boolean;
  onClick?: () => void;
}) {
  const color = tone === 'dark' ? '#064E3B' : (customColor || '#0F172A');
  const Tag: any = onClick ? 'button' : 'div';
  return (
    <Tag
      onClick={onClick}
      className={`relative card p-3.5 overflow-hidden text-left w-full transition ${
        onClick ? 'cursor-pointer hover:-translate-y-0.5 hover:shadow-md' : ''
      } ${active ? 'ring-2 ring-offset-1' : ''}`}
      style={active ? { boxShadow: `0 0 0 2px ${color}88` } : undefined}
    >
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ background: color }} />
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wide text-slate-500 font-bold truncate">{label}</div>
          <div className="font-display text-xl font-black mt-0.5" style={{ color }}>
            {value.toLocaleString('fr-FR')}
          </div>
          {sub && <div className="text-[10px] text-slate-500 truncate">{sub}</div>}
        </div>
        <div
          className="h-8 w-8 rounded-lg grid place-items-center text-white shrink-0"
          style={{ background: color }}
        >
          {icon}
        </div>
      </div>
    </Tag>
  );
}
