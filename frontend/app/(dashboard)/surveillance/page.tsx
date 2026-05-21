'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowDown, ArrowUp, ChevronLeft, ChevronRight,
  Download, Eye, FileText, Filter, MoreVertical, RefreshCcw, Search,
  ShieldCheck, ShieldX, Siren, X,
} from 'lucide-react';
import { API_URL, api, extractApiError } from '@/lib/api';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { formatDateTime, STATUS_LABELS } from '@/lib/utils';
import type { RiskLevel } from '@/types/ebola';

interface InvRow {
  case_number: string;
  status: string;
  risk_level: RiskLevel;
  risk_score: number;
  entry_point: number | null;
  entry_point_name: string;
  created_at: string;
  traveler: number;
  traveler_detail: {
    public_id: string;
    full_name?: string;
    last_name?: string;
    first_name?: string;
    current_health_status?: string;
    arrival_date?: string | null;
    nationality_code?: string | null;
    phone_mobile?: string | null;
  };
}

interface EntryPoint { id: number; name: string; code: string }

const PAGE_SIZE = 20;

const STATUS_OPTS = [
  { value: '',             label: 'Tous statuts' },
  { value: 'new',          label: 'Nouvelle' },
  { value: 'in_review',    label: 'En revue' },
  { value: 'surveillance', label: 'Surveillance' },
  { value: 'quarantine',   label: 'Quarantaine' },
  { value: 'suspect',      label: 'Cas suspect' },
  { value: 'confirmed',    label: 'Cas confirmé' },
  { value: 'cleared',      label: 'Autorisé' },
  { value: 'closed',       label: 'Clôturé' },
];

const RISK_OPTS: { value: '' | RiskLevel; label: string; tone: string }[] = [
  { value: '',         label: 'Tous risques', tone: 'bg-slate-100 text-slate-700' },
  { value: 'low',      label: 'Faible',       tone: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  { value: 'moderate', label: 'Modéré',       tone: 'bg-amber-50 text-amber-800 ring-amber-200' },
  { value: 'high',     label: 'Élevé',        tone: 'bg-rose-50 text-rose-700 ring-rose-200' },
  { value: 'critical', label: 'Critique',     tone: 'bg-red-900 text-white ring-red-700' },
];

export default function SurveillancePage() {
  const [items, setItems] = useState<InvRow[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Filtres
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState<'' | RiskLevel>('');
  const [entryFilter, setEntryFilter] = useState('');
  const [ordering, setOrdering] = useState('-created_at');
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([]);

  // Action menu open per row
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  // Charger les points d'entrée une seule fois
  useEffect(() => {
    api.get('/geo/entry-points/?is_active=true')
      .then((r) => setEntryPoints(r.data.results || r.data || []))
      .catch(() => undefined);
  }, []);

  const load = () => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams({
      ordering,
      page: String(page),
      page_size: String(PAGE_SIZE),
    });
    if (search) params.set('search', search);
    if (statusFilter) params.set('status', statusFilter);
    if (riskFilter) params.set('risk_level', riskFilter);
    if (entryFilter) params.set('entry_point', entryFilter);

    api.get(`/ebola/investigations/?${params.toString()}`)
      .then((r) => {
        const data: any = r.data;
        if (Array.isArray(data)) {
          setItems(data);
          setCount(data.length);
        } else {
          setItems(data.results || []);
          setCount(data.count || 0);
        }
      })
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [page, ordering, statusFilter, riskFilter, entryFilter]);

  // Search debouncé local
  useEffect(() => {
    const id = setTimeout(() => { setPage(1); load(); }, 350);
    return () => clearTimeout(id);
    // eslint-disable-next-line
  }, [search]);

  // KPIs locaux (sur la page courante — pour le total filtré, count global)
  const kpis = useMemo(() => {
    const by: Record<string, number> = { low: 0, moderate: 0, high: 0, critical: 0 };
    items.forEach((r) => { if (r.risk_level) by[r.risk_level] = (by[r.risk_level] || 0) + 1; });
    return {
      total: count,
      pageSize: items.length,
      low: by.low, moderate: by.moderate, high: by.high, critical: by.critical,
    };
  }, [items, count]);

  // Actions
  const downloadForm = (publicId: string) => {
    window.open(`${API_URL}/api/v1/ebola/public/pass/${publicId}/official-form.pdf`, '_blank');
  };
  const downloadPass = (publicId: string) => {
    window.open(`${API_URL}/api/v1/ebola/public/pass/${publicId}/pdf/`, '_blank');
  };
  const recompute = (caseNumber: string) => {
    api.post(`/ebola/investigations/${caseNumber}/recompute-score/`)
      .then(() => load())
      .catch((e) => alert(extractApiError(e)));
  };
  const closeCase = (caseNumber: string) => {
    if (!confirm(`Clôturer l'enquête ${caseNumber} ?`)) return;
    api.post(`/ebola/investigations/${caseNumber}/close/`)
      .then(() => load())
      .catch((e) => alert(extractApiError(e)));
  };

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const hasFilters = !!(search || statusFilter || riskFilter || entryFilter);

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-ciOrange font-bold">
            Surveillance épidémiologique
          </div>
          <h1 className="font-display text-3xl font-black">Enquêtes Ebola</h1>
          <p className="text-sm text-slate-500 mt-1">
            {count.toLocaleString('fr-FR')} enquête(s) — page {page}/{totalPages}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={load} className="btn-outline text-sm" title="Actualiser">
            <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Actualiser
          </button>
        </div>
      </header>

      {/* KPI */}
      <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatBox label="Total" value={kpis.total} icon={<Activity className="h-5 w-5" />} tone="dark" />
        <StatBox label="Faible" value={kpis.low} icon={<ShieldCheck className="h-5 w-5" />} tone="green" />
        <StatBox label="Modéré" value={kpis.moderate} icon={<AlertTriangle className="h-5 w-5" />} tone="amber" />
        <StatBox label="Élevé" value={kpis.high} icon={<Siren className="h-5 w-5" />} tone="rose" />
        <StatBox label="Critique" value={kpis.critical} icon={<ShieldX className="h-5 w-5" />} tone="red" />
      </section>

      {/* Filtres */}
      <section className="card p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher cas, voyageur, public_id, notes…"
              className="input pl-9"
            />
          </div>

          <select className="select max-w-[180px]" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
            {STATUS_OPTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>

          <div className="inline-flex rounded-xl border border-slate-200 dark:border-slate-700 p-1">
            {RISK_OPTS.map((r) => (
              <button
                key={r.value || 'all'}
                onClick={() => { setRiskFilter(r.value); setPage(1); }}
                className={`px-3 py-1.5 text-xs rounded-lg font-bold transition ${
                  riskFilter === r.value
                    ? 'bg-ciDark text-white'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>

          <select className="select max-w-[220px]" value={entryFilter} onChange={(e) => { setEntryFilter(e.target.value); setPage(1); }}>
            <option value="">Tous points d'entrée</option>
            {entryPoints.map((e) => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </select>

          {hasFilters && (
            <button
              onClick={() => {
                setSearch(''); setStatusFilter(''); setRiskFilter('');
                setEntryFilter(''); setPage(1);
              }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <X className="h-3 w-3" /> Réinitialiser
            </button>
          )}
        </div>
      </section>

      {err && <div className="card p-6 text-rose-600">{err}</div>}

      {/* Tableau */}
      <section className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <Th label="Cas" onSort={() => setOrdering(ordering === 'case_number' ? '-case_number' : 'case_number')} active={ordering.endsWith('case_number')} dir={ordering.startsWith('-') ? 'desc' : 'asc'} />
                <Th label="Voyageur" />
                <Th label="Risque" onSort={() => setOrdering(ordering === 'risk_score' ? '-risk_score' : 'risk_score')} active={ordering.endsWith('risk_score')} dir={ordering.startsWith('-') ? 'desc' : 'asc'} />
                <Th label="Statut" />
                <Th label="Point d'entrée" />
                <Th label="Créé le" onSort={() => setOrdering(ordering === 'created_at' ? '-created_at' : 'created_at')} active={ordering.endsWith('created_at')} dir={ordering.startsWith('-') ? 'desc' : 'asc'} />
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && items.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-slate-400">Chargement…</td></tr>
              )}
              {!loading && items.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-slate-400">Aucune enquête correspondante.</td></tr>
              )}
              {items.map((r) => {
                const pid = r.traveler_detail?.public_id;
                const name = r.traveler_detail?.full_name
                  || `${r.traveler_detail?.last_name || ''} ${r.traveler_detail?.first_name || ''}`.trim()
                  || '—';
                return (
                  <tr key={r.case_number} className="hover:bg-slate-50 dark:hover:bg-slate-900/60 transition">
                    <td className="px-4 py-3 font-mono text-xs">{r.case_number}</td>
                    <td className="px-4 py-3">
                      <Link href={pid ? `/surveillance/${pid}` : '#'} className="block group">
                        <div className="font-semibold group-hover:text-ciOrange transition">{name}</div>
                        <div className="text-[11px] font-mono text-slate-400">{pid || '—'}</div>
                      </Link>
                    </td>
                    <td className="px-4 py-3"><RiskBadge level={r.risk_level} score={r.risk_score} /></td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-xs font-semibold">
                        {STATUS_LABELS[r.status] || r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{r.entry_point_name || '—'}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{formatDateTime(r.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-1 relative">
                        {pid && (
                          <Link
                            href={`/surveillance/${pid}`}
                            title="Ouvrir la fiche détaillée"
                            className="inline-flex items-center justify-center h-8 w-8 rounded-lg text-slate-500 hover:bg-emerald-50 hover:text-ciGreen"
                          >
                            <Eye className="h-4 w-4" />
                          </Link>
                        )}
                        {pid && (
                          <button
                            onClick={() => downloadForm(pid)}
                            title="Télécharger la fiche d'enquête INHP (PDF)"
                            className="inline-flex items-center justify-center h-8 w-8 rounded-lg text-slate-500 hover:bg-orange-50 hover:text-ciOrange"
                          >
                            <FileText className="h-4 w-4" />
                          </button>
                        )}
                        {pid && (
                          <button
                            onClick={() => downloadPass(pid)}
                            title="Télécharger le pass sanitaire (PDF)"
                            className="inline-flex items-center justify-center h-8 w-8 rounded-lg text-slate-500 hover:bg-emerald-50 hover:text-ciGreen"
                          >
                            <Download className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          onClick={() => setOpenMenu(openMenu === r.case_number ? null : r.case_number)}
                          className="inline-flex items-center justify-center h-8 w-8 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                          title="Plus d'actions"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                        {openMenu === r.case_number && (
                          <div
                            className="absolute right-0 top-9 z-10 w-52 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl p-1 text-left"
                            onMouseLeave={() => setOpenMenu(null)}
                          >
                            <button
                              onClick={() => { recompute(r.case_number); setOpenMenu(null); }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                            >
                              <RefreshCcw className="h-4 w-4 text-ciOrange" /> Recalculer le score
                            </button>
                            <button
                              onClick={() => { closeCase(r.case_number); setOpenMenu(null); }}
                              disabled={r.status === 'closed'}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/30 text-rose-600 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <X className="h-4 w-4" /> Clôturer l'enquête
                            </button>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {count > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-800 text-sm">
            <div className="text-slate-500">
              Page <span className="font-bold text-slate-700 dark:text-slate-200">{page}</span> sur {totalPages}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <ChevronLeft className="h-4 w-4" /> Précédent
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Suivant <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

/* ============================================================
   Sub-components
   ============================================================ */
function StatBox({
  label, value, icon, tone,
}: { label: string; value: number; icon: React.ReactNode; tone: 'dark' | 'green' | 'amber' | 'rose' | 'red' }) {
  const map = {
    dark:  { bg: 'bg-emerald-50 dark:bg-emerald-950/40', text: 'text-ciDark dark:text-emerald-200', bar: 'bg-ciDark dark:bg-emerald-500' },
    green: { bg: 'bg-emerald-50 dark:bg-emerald-950/40', text: 'text-ciGreen',  bar: 'bg-ciGreen' },
    amber: { bg: 'bg-amber-50 dark:bg-amber-950/40',     text: 'text-amber-700 dark:text-amber-300', bar: 'bg-amber-500' },
    rose:  { bg: 'bg-rose-50 dark:bg-rose-950/40',       text: 'text-rose-700 dark:text-rose-300', bar: 'bg-rose-500' },
    red:   { bg: 'bg-red-50 dark:bg-red-950/40',         text: 'text-red-800 dark:text-red-200', bar: 'bg-red-900' },
  }[tone];
  return (
    <div className="relative card p-4 overflow-hidden">
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${map.bar}`} />
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-slate-500 font-bold">{label}</div>
          <div className={`font-display text-2xl font-black mt-0.5 ${map.text}`}>{value.toLocaleString('fr-FR')}</div>
        </div>
        <div className={`h-9 w-9 rounded-xl ${map.bg} ${map.text} grid place-items-center`}>{icon}</div>
      </div>
    </div>
  );
}

function Th({
  label, onSort, active, dir,
}: { label: string; onSort?: () => void; active?: boolean; dir?: 'asc' | 'desc' }) {
  if (!onSort) return <th className="px-4 py-3 text-left">{label}</th>;
  return (
    <th className="px-4 py-3 text-left">
      <button onClick={onSort} className={`inline-flex items-center gap-1 hover:text-ciOrange ${active ? 'text-ciOrange' : ''}`}>
        {label}
        {active && (dir === 'desc' ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
      </button>
    </th>
  );
}
