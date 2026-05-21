'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  ChevronDown, ChevronRight, Filter, Home, Hospital, MapPin, Phone, Plane,
  RefreshCcw, Search, Users, X,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { STATUS_LABELS } from '@/lib/utils';
import type { RiskLevel } from '@/types/ebola';

/* ============================================================
   Types
   ============================================================ */
type ClusterType = 'flight' | 'phone' | 'origin' | 'companion' | 'residence';

interface Member {
  public_id: string;
  full_name: string;
  status: string;
  risk_level: RiskLevel | null;
  risk_score: number | null;
  phone: string | null;
  flight: string | null;
  arrival_date: string | null;
  entry_point: string | null;
  nationality: string | null;
  hotel: string | null;
  commune: string | null;
}

interface Cluster {
  type: ClusterType;
  key: string;
  label: string;
  size: number;
  members: Member[];
}

interface RelationsResp {
  clusters: Cluster[];
  stats: {
    total_travelers: number;
    total_clusters: number;
    by_type: Record<string, { clusters: number; members: number }>;
  };
}

/* ============================================================
   Config visuelle par type de relation
   ============================================================ */
const TYPE_META: Record<ClusterType, { label: string; icon: React.ComponentType<any>; color: string; ring: string }> = {
  flight:    { label: 'Vol',              icon: Plane,    color: '#F77F00', ring: 'ring-orange-200/60'  },
  phone:     { label: 'Téléphone',        icon: Phone,    color: '#0EA5E9', ring: 'ring-sky-200/60'     },
  origin:    { label: 'Provenance',       icon: MapPin,   color: '#D4A017', ring: 'ring-amber-200/60'   },
  companion: { label: 'Cas-contact',      icon: Users,    color: '#EF4444', ring: 'ring-rose-200/60'    },
  residence: { label: 'Résidence Abidjan', icon: Home,    color: '#009B5A', ring: 'ring-emerald-200/60' },
};

const STATUS_COLOR: Record<string, string> = {
  cleared:    '#10B981',
  monitoring: '#0EA5E9',
  quarantine: '#F59E0B',
  suspect:    '#EF4444',
  confirmed:  '#7F1D1D',
  recovered:  '#6366F1',
  deceased:   '#111827',
};

/* ============================================================
   PAGE
   ============================================================ */
export default function RelationsPage() {
  const [data, setData] = useState<RelationsResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Filtres
  const [type, setType] = useState<'' | ClusterType>('');
  const [search, setSearch] = useState('');
  const [minSize, setMinSize] = useState(2);
  const [days, setDays] = useState<string>('');

  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const load = () => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams();
    if (type) params.set('type', type);
    if (search.trim()) params.set('search', search.trim());
    if (minSize !== 2) params.set('min_size', String(minSize));
    if (days) params.set('days', days);
    api.get<RelationsResp>(`/surveillance/relations/?${params.toString()}`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [type, minSize, days]);
  // Debounce search
  useEffect(() => {
    const id = setTimeout(load, 350);
    return () => clearTimeout(id);
    // eslint-disable-next-line
  }, [search]);

  // Groupe les clusters par type pour l'arbre
  const grouped = useMemo(() => {
    const g: Record<ClusterType, Cluster[]> = {
      flight: [], phone: [], origin: [], companion: [], residence: [],
    };
    (data?.clusters || []).forEach((c) => g[c.type].push(c));
    return g;
  }, [data]);

  const toggle = (key: string) => setExpanded((e) => ({ ...e, [key]: !e[key] }));

  const hasFilters = !!(type || search || minSize !== 2 || days);

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
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
        <button onClick={load} className="btn-outline text-sm">
          <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Actualiser
        </button>
      </header>

      {/* Stats */}
      {data && (
        <section className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <StatBox label="Voyageurs analysés" value={data.stats.total_travelers} tone="dark" icon={<Users className="h-4 w-4" />} />
          {(Object.keys(TYPE_META) as ClusterType[]).map((t) => {
            const Meta = TYPE_META[t];
            const s = data.stats.by_type?.[t];
            return (
              <StatBox
                key={t}
                label={Meta.label}
                value={s?.clusters || 0}
                sub={s ? `${s.members} voyageurs` : '0 voyageur'}
                tone="custom"
                customColor={Meta.color}
                icon={<Meta.icon className="h-4 w-4" />}
              />
            );
          })}
        </section>
      )}

      {/* Filtres */}
      <section className="card p-4">
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

          <div className="inline-flex rounded-xl border border-slate-200 dark:border-slate-700 p-1">
            <PillType active={type === ''} onClick={() => setType('')}>Tous</PillType>
            {(Object.keys(TYPE_META) as ClusterType[]).map((t) => {
              const M = TYPE_META[t];
              return (
                <PillType key={t} active={type === t} onClick={() => setType(type === t ? '' : t)}>
                  <M.icon className="h-3.5 w-3.5" /> {M.label}
                </PillType>
              );
            })}
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

          {hasFilters && (
            <button
              onClick={() => { setType(''); setSearch(''); setMinSize(2); setDays(''); }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <X className="h-3 w-3" /> Réinitialiser
            </button>
          )}
        </div>
      </section>

      {err && <div className="card p-6 text-rose-600">{err}</div>}
      {loading && !data && <div className="card p-10 animate-pulse h-40" />}

      {/* Arbre */}
      {data && (
        <section className="space-y-3">
          {(Object.keys(TYPE_META) as ClusterType[]).map((t) => {
            const list = grouped[t];
            if (list.length === 0) return null;
            const Meta = TYPE_META[t];
            const sectionKey = `__sec__${t}`;
            const open = expanded[sectionKey] !== false; // par défaut ouvert
            const total = list.reduce((a, c) => a + c.size, 0);
            return (
              <article key={t} className="card overflow-hidden">
                <button
                  onClick={() => toggle(sectionKey)}
                  className="w-full px-5 py-3 flex items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-slate-900/60 transition"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="h-9 w-9 rounded-xl grid place-items-center text-white shadow-sm"
                      style={{ background: Meta.color }}
                    >
                      <Meta.icon className="h-4 w-4" />
                    </span>
                    <div className="text-left">
                      <div className="font-display text-base font-black">
                        Par {Meta.label.toLowerCase()}
                      </div>
                      <div className="text-xs text-slate-500">
                        {list.length} cluster(s) · {total} voyageur(s)
                      </div>
                    </div>
                  </div>
                  {open ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                </button>

                {open && (
                  <div className="divide-y divide-slate-100 dark:divide-slate-800">
                    {list.map((c) => (
                      <ClusterRow
                        key={c.key}
                        cluster={c}
                        meta={Meta}
                        expanded={!!expanded[c.key]}
                        onToggle={() => toggle(c.key)}
                      />
                    ))}
                  </div>
                )}
              </article>
            );
          })}

          {data.clusters.length === 0 && (
            <div className="card p-10 text-center text-slate-500">
              <Filter className="h-6 w-6 text-slate-300 mx-auto mb-2" />
              Aucun cluster ne correspond aux filtres actuels.
            </div>
          )}
        </section>
      )}
    </div>
  );
}

/* ============================================================
   Sub-components
   ============================================================ */
function PillType({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg font-bold transition ${
        active
          ? 'bg-ciDark text-white'
          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
      }`}
    >
      {children}
    </button>
  );
}

function StatBox({
  label, value, sub, icon, tone, customColor,
}: {
  label: string;
  value: number;
  sub?: string;
  icon: React.ReactNode;
  tone: 'dark' | 'custom';
  customColor?: string;
}) {
  const color = tone === 'dark' ? '#064E3B' : (customColor || '#0F172A');
  return (
    <div className="relative card p-3.5 overflow-hidden">
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
    </div>
  );
}

function ClusterRow({
  cluster, meta, expanded, onToggle,
}: {
  cluster: Cluster;
  meta: typeof TYPE_META[ClusterType];
  expanded: boolean;
  onToggle: () => void;
}) {
  const Icon = meta.icon;
  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full px-5 py-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-900/60 transition text-left"
      >
        {expanded ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />}
        <span
          className={`h-7 w-7 rounded-lg grid place-items-center text-white shrink-0 ring-2 ${meta.ring}`}
          style={{ background: meta.color }}
        >
          <Icon className="h-3.5 w-3.5" />
        </span>
        <div className="flex-1 min-w-0">
          <div className="font-semibold truncate">{cluster.label}</div>
          <div className="text-xs text-slate-500">{cluster.size} voyageur(s) regroupé(s)</div>
        </div>
        <span className="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 text-xs font-black text-slate-700 dark:text-slate-300">
          {cluster.size}
        </span>
      </button>

      {expanded && (
        <div className="px-5 pb-5 grid lg:grid-cols-[300px,1fr] gap-5 items-start">
          {/* Mini-graphe radial */}
          <RadialGraph cluster={cluster} color={meta.color} />

          {/* Liste des membres */}
          <ul className="space-y-1.5">
            {cluster.members.map((m) => (
              <li key={m.public_id}>
                <Link
                  href={`/surveillance/${m.public_id}`}
                  className="flex items-center gap-3 rounded-xl border border-slate-200 dark:border-slate-800 px-3 py-2 hover:border-ciOrange/60 hover:bg-orange-50/30 dark:hover:bg-orange-950/20 transition group"
                >
                  <span
                    className="h-2.5 w-2.5 rounded-full shrink-0 ring-2 ring-white dark:ring-slate-900"
                    style={{ background: STATUS_COLOR[m.status] || '#94A3B8' }}
                    title={STATUS_LABELS[m.status] || m.status}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm truncate group-hover:text-ciOrange transition">{m.full_name}</div>
                    <div className="text-[11px] text-slate-500 font-mono truncate">
                      {m.public_id}
                      {m.entry_point ? ` · ${m.entry_point}` : ''}
                      {m.arrival_date ? ` · ${new Date(m.arrival_date).toLocaleDateString('fr-FR')}` : ''}
                    </div>
                  </div>
                  {m.risk_level && (
                    <RiskBadge level={m.risk_level} score={m.risk_score ?? undefined} />
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ============================================================
   Mini-graphe radial : hub central + voyageurs autour
   ============================================================ */
function RadialGraph({ cluster, color }: { cluster: Cluster; color: string }) {
  const size = 280;
  const cx = size / 2;
  const cy = size / 2;
  const hubR = 28;
  const ringR = 100;
  const dotR = 11;

  const visible = cluster.members.slice(0, 14);
  const more = Math.max(0, cluster.members.length - visible.length);

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-950 p-3">
      <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">Vue tree</div>
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-auto">
        {/* Cercle de fond très léger */}
        <circle cx={cx} cy={cy} r={ringR + 22} fill="none" stroke={color} strokeOpacity={0.08} strokeDasharray="3 5" />

        {/* Lignes hub → membres */}
        {visible.map((m, i) => {
          const angle = (i / visible.length) * Math.PI * 2 - Math.PI / 2;
          const x = cx + Math.cos(angle) * ringR;
          const y = cy + Math.sin(angle) * ringR;
          return (
            <line
              key={`l-${m.public_id}`}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke={color}
              strokeOpacity={0.35}
              strokeWidth={1.5}
            />
          );
        })}

        {/* Hub central */}
        <circle cx={cx} cy={cy} r={hubR} fill={color} />
        <circle cx={cx} cy={cy} r={hubR} fill="none" stroke="#ffffff" strokeWidth={3} />
        <text
          x={cx} y={cy + 4} textAnchor="middle"
          fontSize="12" fontWeight="900" fill="#ffffff"
        >
          {cluster.size}
        </text>

        {/* Membres */}
        {visible.map((m, i) => {
          const angle = (i / visible.length) * Math.PI * 2 - Math.PI / 2;
          const x = cx + Math.cos(angle) * ringR;
          const y = cy + Math.sin(angle) * ringR;
          const c = STATUS_COLOR[m.status] || '#94A3B8';
          return (
            <g key={`m-${m.public_id}`}>
              <title>{m.full_name} · {STATUS_LABELS[m.status] || m.status}</title>
              <circle cx={x} cy={y} r={dotR + 2} fill="#ffffff" />
              <circle cx={x} cy={y} r={dotR} fill={c} />
            </g>
          );
        })}

        {/* Badge +N */}
        {more > 0 && (
          <g transform={`translate(${cx + ringR + 10}, ${cy + ringR - 6})`}>
            <rect x={-18} y={-10} width={36} height={20} rx={10} fill={color} />
            <text x={0} y={4} textAnchor="middle" fontSize="10" fontWeight="900" fill="#ffffff">
              +{more}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
