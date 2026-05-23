'use client';

/**
 * /dashboard/alertes — Centre de gestion des alertes sanitaires.
 *
 * KPIs en haut + filtres (sévérité, statut, maladie, période) + recherche
 * full-text + pagination. Chaque alerte mène à sa page détail enrichie.
 */

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  ChevronLeft, ChevronRight, Search, Siren, Filter, RefreshCcw,
  AlertTriangle, CheckCircle2, Clock, XCircle,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface Alert {
  id: number;
  uuid: string;
  code: string;
  title: string;
  severity: string;
  status: string;
  disease_code?: string | null;
  entry_point_name?: string | null;
  created_at: string;
  metadata?: { duplicate_count?: number };
}

interface PageResponse<T> { count: number; results: T[]; next: string | null; previous: string | null }

const SEV_OPTS = [
  { value: '',         label: 'Toutes',   color: '#94A3B8' },
  { value: 'critical', label: 'Critique', color: '#7F1D1D' },
  { value: 'high',     label: 'Élevée',   color: '#EF4444' },
  { value: 'medium',   label: 'Moyenne',  color: '#F59E0B' },
  { value: 'low',      label: 'Faible',   color: '#10B981' },
  { value: 'info',     label: 'Info',     color: '#0EA5E9' },
];

const STATUS_OPTS = [
  { value: '',              label: 'Tous statuts',  icon: <AlertTriangle className="h-3 w-3" /> },
  { value: 'OPEN',          label: 'Nouvelles',     icon: <Siren className="h-3 w-3" /> },
  { value: 'ACK',           label: 'Reconnues',     icon: <Clock className="h-3 w-3" /> },
  { value: 'INVESTIGATING', label: 'En cours',      icon: <Filter className="h-3 w-3" /> },
  { value: 'RESOLVED',      label: 'Résolues',      icon: <CheckCircle2 className="h-3 w-3" /> },
  { value: 'DISMISSED',     label: 'Fausses',       icon: <XCircle className="h-3 w-3" /> },
];

const SEV_BADGE: Record<string, string> = {
  critical: 'bg-rose-100 text-rose-800 border-rose-300',
  high:     'bg-orange-100 text-orange-800 border-orange-300',
  medium:   'bg-amber-100 text-amber-800 border-amber-300',
  low:      'bg-emerald-100 text-emerald-800 border-emerald-300',
  info:     'bg-sky-100 text-sky-800 border-sky-300',
};

const STATUS_BADGE: Record<string, string> = {
  OPEN: 'bg-rose-50 text-rose-700',
  ACK: 'bg-amber-50 text-amber-700',
  INVESTIGATING: 'bg-sky-50 text-sky-700',
  RESOLVED: 'bg-emerald-50 text-emerald-700',
  DISMISSED: 'bg-slate-100 text-slate-500',
};

const PAGE_SIZE = 25;

export default function AlertesPage() {
  const [items, setItems] = useState<Alert[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Filtres
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState('');
  const [status, setStatus] = useState('');
  const [disease, setDisease] = useState('');
  const [days, setDays] = useState(30);
  const [page, setPage] = useState(1);

  const [diseases, setDiseases] = useState<{ id: number; code: string; name: string }[]>([]);

  // Compteurs KPI (par statut)
  const [kpis, setKpis] = useState<Record<string, number>>({});

  // Liste maladies
  useEffect(() => {
    api.get('/diseases/?page_size=50')
      .then((r) => setDiseases(r.data.results || r.data))
      .catch(() => {});
  }, []);

  // KPIs (1 requête par statut, count=1 → léger)
  const loadKpis = () => {
    Promise.all(
      STATUS_OPTS.filter((s) => s.value).map((s) =>
        api.get(`/surveillance/alerts/?status=${s.value}&page_size=1`)
          .then((r) => [s.value, (r.data as any).count ?? (r.data.results || r.data).length] as const)
          .catch(() => [s.value, 0] as const)
      )
    ).then((entries) => setKpis(Object.fromEntries(entries)));
  };
  useEffect(() => { loadKpis(); }, []);

  // Liste filtrée
  const load = () => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
      ordering: '-created_at',
    });
    if (severity) params.set('severity', severity);
    if (status) params.set('status', status);
    if (disease) params.set('disease', disease);
    if (search) params.set('search', search);
    // Période : on filtre côté front (DRF n'accepte pas created_at__gte par défaut)

    api.get<PageResponse<Alert> | Alert[]>(`/surveillance/alerts/?${params}`)
      .then((r) => {
        const data: any = r.data;
        if (Array.isArray(data)) {
          setItems(data);
          setTotalCount(data.length);
        } else {
          setItems(data.results || []);
          setTotalCount(data.count || 0);
        }
      })
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [severity, status, disease, search, page]);

  // Filtre période côté front (les autres filtres restent côté serveur)
  const visibleItems = useMemo(() => {
    if (!days || days >= 1825) return items;
    const cutoff = Date.now() - days * 86400_000;
    return items.filter((a) => new Date(a.created_at).getTime() >= cutoff);
  }, [items, days]);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  const resetFilters = () => {
    setSearch(''); setSeverity(''); setStatus(''); setDisease(''); setDays(30); setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <header>
        <span className="text-xs uppercase tracking-widest text-rose-600 font-bold">
          Centre des alertes
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Alertes sanitaires
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Toutes les alertes générées automatiquement (check-ins symptomatiques, clusters,
          assistance demandée) ou créées manuellement par les agents.
        </p>
      </header>

      {/* KPIs cliquables */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {STATUS_OPTS.filter((s) => s.value).map((s) => {
          const n = kpis[s.value] ?? 0;
          const active = status === s.value;
          const isAlert = ['OPEN', 'ACK'].includes(s.value);
          return (
            <button
              key={s.value}
              onClick={() => { setStatus(s.value); setPage(1); }}
              className={`card p-3 text-left transition hover:shadow-md ${
                active ? 'ring-2 ring-offset-2 ring-rose-500' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wide text-slate-500 font-bold">
                  {s.label}
                </span>
                <span className={isAlert && n > 0 ? 'text-rose-600' : 'text-slate-400'}>
                  {s.icon}
                </span>
              </div>
              <div className={`font-display text-2xl font-black mt-1 ${
                isAlert && n > 0 ? 'text-rose-700' : 'text-slate-900 dark:text-slate-100'
              }`}>
                {n}
              </div>
            </button>
          );
        })}
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
              placeholder="Titre, code, description..."
              className="w-full pl-9 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Sévérité</label>
          <select
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            {SEV_OPTS.map((s) => (
              <option key={s.value || 'all'} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Maladie</label>
          <select
            value={disease}
            onChange={(e) => { setDisease(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="">Toutes</option>
            {diseases.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Période</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value={1}>24h</option>
            <option value={7}>7 jours</option>
            <option value={30}>30 jours</option>
            <option value={90}>3 mois</option>
            <option value={365}>1 an</option>
            <option value={1825}>Tout</option>
          </select>
        </div>
        <button
          onClick={resetFilters}
          className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
          title="Réinitialiser"
        >
          Reset
        </button>
        <button
          onClick={() => { load(); loadKpis(); }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
          title="Rafraîchir"
        >
          <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
        <div className="ml-auto text-xs text-slate-500 self-end">
          {visibleItems.length} sur {totalCount} alertes
        </div>
      </div>

      {err && <div className="card p-6 text-rose-600">{err}</div>}

      {/* Liste */}
      <div className="space-y-2">
        {loading && <div className="card p-10 animate-pulse h-32" />}
        {!loading && visibleItems.length === 0 && (
          <div className="card p-10 text-center text-slate-400">
            Aucune alerte avec ces filtres.
          </div>
        )}
        {!loading && visibleItems.map((a) => {
          const sev = (a.severity || 'info').toLowerCase();
          const dup = a.metadata?.duplicate_count;
          return (
            <Link
              key={a.uuid}
              href={`/alertes/${a.uuid}`}
              className="card p-4 flex items-start justify-between gap-3 hover:shadow-md transition group"
            >
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <div className={`h-10 w-10 rounded-xl grid place-items-center shrink-0 border ${SEV_BADGE[sev] || SEV_BADGE.info}`}>
                  <Siren className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-display text-base font-bold group-hover:text-ciOrange transition truncate">
                    {a.title}
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-x-2">
                    <span className="font-mono">{a.code}</span>
                    {a.disease_code && <><span>·</span><span>{a.disease_code}</span></>}
                    {a.entry_point_name && <><span>·</span><span>{a.entry_point_name}</span></>}
                    <span>·</span>
                    <span>{formatDateTime(a.created_at)}</span>
                    {dup != null && dup > 0 && (
                      <span className="inline-flex items-center gap-1 bg-amber-100 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 px-1.5 py-0.5 rounded text-[10px] font-bold">
                        +{dup} doublon{dup > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${SEV_BADGE[sev] || SEV_BADGE.info}`}>
                  {sev}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${STATUS_BADGE[a.status] || 'bg-slate-100'}`}>
                  {STATUS_OPTS.find((s) => s.value === a.status)?.label || a.status}
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between gap-2 px-1">
          <div className="text-xs text-slate-500">
            Page {page} sur {totalPages} · {totalCount} alertes au total
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
            >
              <ChevronLeft className="h-4 w-4" /> Précédent
            </button>
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
  );
}
