'use client';

/**
 * /dashboard/audit-logs — Journaux d'accès aux données.
 *
 * Flux unifié de 3 sources :
 *  - Consultations de données voyageur (location, contacts, identité)
 *  - Scans de pass sanitaires (QR)
 *  - Actions administratives (AuditLog)
 *
 * Filtres : source, période, recherche libre, voyageur précis.
 * Pagination serveur (25 / page).
 *
 * Réservé NATIONAL_ADMIN / MINISTRY / INHP.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronLeft, ChevronRight, FileText, MapPin, QrCode,
  Search, Settings, ShieldAlert, ShieldCheck, ShieldX,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

type LogSource = 'data_access' | 'pass_scan' | 'admin';

interface AuditRow {
  id: string;
  source: LogSource;
  occurred_at: string;
  user_label: string;
  user_role: string;
  action: string;
  target: string;
  reason: string;
  ip_address: string | null;
  entry_point?: string | null;
  pass_number?: string | null;
  ok: boolean;
}

interface Payload {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  by_source: Record<string, number>;
  rows: AuditRow[];
}

const SOURCE_META: Record<LogSource, { label: string; icon: React.ReactNode; color: string }> = {
  data_access: {
    label: 'Accès données',
    icon: <MapPin className="h-3.5 w-3.5" />,
    color: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
  },
  pass_scan: {
    label: 'Scan pass',
    icon: <QrCode className="h-3.5 w-3.5" />,
    color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  },
  admin: {
    label: 'Action admin',
    icon: <Settings className="h-3.5 w-3.5" />,
    color: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  },
};

const PAGE_SIZE = 25;

export default function AuditLogsPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // Filtres
  const [source, setSource] = useState<'' | LogSource>('');
  const [travelerId, setTravelerId] = useState('');
  const [q, setQ] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Debounce search
  const [debouncedQ, setDebouncedQ] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 350);
    return () => clearTimeout(t);
  }, [q]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(PAGE_SIZE),
      });
      if (source) params.set('source', source);
      if (travelerId.trim()) params.set('traveler', travelerId.trim().toUpperCase());
      if (debouncedQ.trim()) params.set('q', debouncedQ.trim());
      if (dateFrom) params.set('from', dateFrom);
      if (dateTo) params.set('to', dateTo);

      const { data } = await api.get<Payload>(`/admin/companion/audit/?${params}`);
      setData(data);
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        setError("Vous n'avez pas le droit de consulter ces journaux. Demandez l'accès à un administrateur national.");
      } else {
        setError(extractApiError(e));
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [page, source, travelerId, debouncedQ, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  // Reset page when filters change
  useEffect(() => { setPage(1); }, [source, travelerId, debouncedQ, dateFrom, dateTo]);

  const hasFilters = !!(source || travelerId || debouncedQ || dateFrom || dateTo);
  const totalPages = data?.total_pages || 1;

  const sourceCounts = useMemo(() => data?.by_source || {}, [data]);

  return (
    <div className="space-y-6">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Sécurité & audit
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Journaux d'accès aux données
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Chaque consultation de localisation, contact ou pièce d'identité d'un voyageur,
          ainsi que chaque scan de pass sanitaire, est tracée ici. Cette page est réservée
          aux administrateurs nationaux et à l'INHP.
        </p>
      </header>

      {/* Stats par source */}
      <div className="grid grid-cols-3 gap-3">
        <SourceKpi
          source="data_access"
          count={sourceCounts.data_access || 0}
          active={source === 'data_access'}
          onClick={() => setSource(source === 'data_access' ? '' : 'data_access')}
        />
        <SourceKpi
          source="pass_scan"
          count={sourceCounts.pass_scan || 0}
          active={source === 'pass_scan'}
          onClick={() => setSource(source === 'pass_scan' ? '' : 'pass_scan')}
        />
        <SourceKpi
          source="admin"
          count={sourceCounts.admin || 0}
          active={source === 'admin'}
          onClick={() => setSource(source === 'admin' ? '' : 'admin')}
        />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Rechercher (agent, IP, motif, n° pass…)"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>

        <input
          className="input max-w-[200px]"
          placeholder="Voyageur (TRV-XXXXXXX)"
          value={travelerId}
          onChange={(e) => setTravelerId(e.target.value)}
        />

        <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 dark:border-slate-700 px-2 py-1">
          <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold pl-1">
            Période
          </span>
          <input
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(e) => setDateFrom(e.target.value)}
            className="bg-transparent px-2 py-1 text-xs focus:outline-none"
          />
          <span className="text-slate-400 text-xs">→</span>
          <input
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => setDateTo(e.target.value)}
            className="bg-transparent px-2 py-1 text-xs focus:outline-none"
          />
        </div>

        {hasFilters && (
          <button
            onClick={() => {
              setSource(''); setTravelerId(''); setQ(''); setDateFrom(''); setDateTo('');
            }}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            Réinitialiser
          </button>
        )}
      </div>

      {error && (
        <div className="card p-4 bg-rose-50 border-rose-200 text-rose-700 text-sm flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" /> {error}
        </div>
      )}

      {/* Tableau */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-left">
              <tr>
                <Th>Date</Th>
                <Th>Type</Th>
                <Th>Acteur</Th>
                <Th>Action</Th>
                <Th>Cible</Th>
                <Th>Motif</Th>
                <Th>IP</Th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={7} className="p-8 text-center text-slate-400">Chargement…</td></tr>
              )}
              {!loading && !error && (data?.rows.length ?? 0) === 0 && (
                <tr><td colSpan={7} className="p-8 text-center text-slate-400">Aucun journal ne correspond aux filtres.</td></tr>
              )}
              {!loading && data?.rows.map((r) => {
                const meta = SOURCE_META[r.source];
                return (
                  <tr key={r.id} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50">
                    <Td className="text-xs text-slate-600 whitespace-nowrap">{formatDateTime(r.occurred_at)}</Td>
                    <Td>
                      <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold ${meta.color}`}>
                        {meta.icon} {meta.label}
                      </span>
                    </Td>
                    <Td className="text-xs">
                      <div className="font-semibold">{r.user_label}</div>
                      {r.user_role && (
                        <div className="text-[10px] text-slate-500 uppercase">{r.user_role}</div>
                      )}
                    </Td>
                    <Td>
                      <div className="flex items-center gap-1 text-xs">
                        {r.source === 'pass_scan' && (
                          r.ok
                            ? <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                            : <ShieldX className="h-3.5 w-3.5 text-rose-600" />
                        )}
                        <span className={r.source === 'pass_scan' && !r.ok ? 'text-rose-700 font-semibold' : ''}>
                          {r.action}
                        </span>
                      </div>
                      {r.entry_point && (
                        <div className="text-[10px] text-slate-500 mt-0.5">{r.entry_point}</div>
                      )}
                    </Td>
                    <Td className="font-mono text-xs">{r.target || '—'}</Td>
                    <Td className="text-xs text-slate-600 max-w-[260px]">
                      <div className="truncate" title={r.reason}>{r.reason || '—'}</div>
                    </Td>
                    <Td className="text-xs text-slate-500 font-mono">{r.ip_address || '—'}</Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && data && data.count > 0 && (
          <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 px-4 py-3 text-sm">
            <div className="text-xs text-slate-500">
              {data.count} entrée(s) · page {page} / {totalPages}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <ChevronLeft className="h-3.5 w-3.5" /> Préc.
              </button>
              <span className="text-xs px-2 font-bold">{page} / {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Suiv. <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="card p-4 bg-amber-50 border-amber-200 text-amber-900 text-xs flex items-start gap-2">
        <FileText className="h-4 w-4 mt-0.5 shrink-0" />
        <p>
          Pour un export complet ou un audit forensique (toutes consultations sur une période,
          tentatives d'accès refusées, exports massifs), contactez l'équipe sécurité MSHPCMU.
          Les données sont conservées 5 ans conformément aux obligations légales.
        </p>
      </div>
    </div>
  );
}

function SourceKpi({
  source, count, active, onClick,
}: { source: LogSource; count: number; active: boolean; onClick: () => void }) {
  const meta = SOURCE_META[source];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`card p-4 text-left transition ${
        active
          ? 'ring-2 ring-ciOrange border-ciOrange'
          : 'hover:bg-slate-50 dark:hover:bg-slate-900/50'
      }`}
    >
      <div className={`inline-flex items-center justify-center h-10 w-10 rounded-xl mb-2 ${meta.color}`}>
        {meta.icon}
      </div>
      <div className="text-2xl font-display font-black text-ciDark dark:text-emerald-100">{count}</div>
      <div className="text-xs text-slate-500 mt-1">{meta.label}</div>
    </button>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-500">{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-3 ${className}`}>{children}</td>;
}
