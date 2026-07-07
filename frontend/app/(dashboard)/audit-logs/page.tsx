'use client';

/**
 * /dashboard/audit-logs — Journaux d'accès aux données.
 *
 * Flux unifié de 3 sources :
 *  - Consultations de données voyageur (location, contacts, identité)
 *  - Scans de pass sanitaires (QR)
 *  - Actions administratives (AuditLog)
 *
 * Réservé NATIONAL_ADMIN / MINISTRY / INHP.
 */

import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertOctagon, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight,
  ChevronUp, Clock, Database, Download, FileText, Info, MapPin, QrCode,
  RefreshCw, Search, Settings, ShieldAlert, ShieldCheck, ShieldX, User2, XCircle,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

type LogSource = 'data_access' | 'pass_scan' | 'admin';
type Severity = 'info' | 'success' | 'warning' | 'danger';

interface AuditRow {
  id: string;
  source: LogSource;
  occurred_at: string;
  user_label: string;
  user_role: string;
  action: string;
  action_code?: string;
  target: string;
  target_kind?: string;
  reason: string;
  ip_address: string | null;
  user_agent?: string | null;
  entry_point?: string | null;
  pass_number?: string | null;
  payload?: Record<string, unknown>;
  request_id?: string;
  severity?: Severity;
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

const SOURCE_META: Record<LogSource, {
  label: string;
  short: string;
  hint: string;
  icon: React.ReactNode;
  color: string;
  ring: string;
  bar: string;
}> = {
  data_access: {
    label: 'Consultation de données',
    short: 'Accès données',
    hint: 'Un agent a consulté la localisation, les contacts ou l\'identité d\'un voyageur.',
    icon: <MapPin className="h-3.5 w-3.5" />,
    color: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
    ring: 'ring-sky-500',
    bar: 'bg-sky-500',
  },
  pass_scan: {
    label: 'Scan de pass sanitaire',
    short: 'Scan pass',
    hint: 'Un pass a été présenté à un point d\'entrée ou de contrôle.',
    icon: <QrCode className="h-3.5 w-3.5" />,
    color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    ring: 'ring-emerald-500',
    bar: 'bg-emerald-500',
  },
  admin: {
    label: 'Action administrative',
    short: 'Action admin',
    hint: 'Création, modification, suppression, connexion ou export.',
    icon: <Settings className="h-3.5 w-3.5" />,
    color: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    ring: 'ring-slate-500',
    bar: 'bg-slate-500',
  },
};

const SEVERITY_META: Record<Severity, { label: string; className: string; icon: React.ReactNode }> = {
  info:    { label: 'Info',    className: 'bg-sky-50 text-sky-700 border border-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-900',       icon: <Info className="h-3 w-3" /> },
  success: { label: 'Succès',  className: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900', icon: <CheckCircle2 className="h-3 w-3" /> },
  warning: { label: 'Vigilance', className: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900',        icon: <AlertOctagon className="h-3 w-3" /> },
  danger:  { label: 'Critique', className: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900',              icon: <XCircle className="h-3 w-3" /> },
};

// Traduction lisible des codes d'action AuditLog
const ACTION_LABEL: Record<string, string> = {
  login: 'Connexion',
  logout: 'Déconnexion',
  login_failed: 'Échec de connexion',
  password_change: 'Changement de mot de passe',
  password_reset: 'Réinitialisation de mot de passe',
  mfa_enabled: 'MFA activé',
  mfa_disabled: 'MFA désactivé',
  create: 'Création',
  update: 'Modification',
  delete: 'Suppression',
  send: 'Envoi',
  export: 'Export',
  read: 'Consultation',
  view: 'Consultation',
  list: 'Liste consultée',
  assign: 'Assignation',
  revoke: 'Révocation',
  issue: 'Émission',
  denied: 'Accès refusé',
  block: 'Blocage',
  scan_ok: 'Scan valide',
  scan_denied: 'Scan refusé',
  location: 'Localisation',
  contacts: 'Contacts',
  identity: 'Identité',
  passport: 'Passeport',
  medical: 'Données médicales',
};

function humanAction(action: string, code?: string): string {
  const key = (code || action || '').toString().toLowerCase().trim();
  if (ACTION_LABEL[key]) return ACTION_LABEL[key];
  // Fallback : `document.create` → « Document · Création »
  if (key.includes('.')) {
    const [scope, verb] = key.split('.');
    const scopeLabel = ACTION_LABEL[scope] || scope.replace(/_/g, ' ');
    const verbLabel = ACTION_LABEL[verb] || verb.replace(/_/g, ' ');
    return `${cap(scopeLabel)} · ${cap(verbLabel)}`;
  }
  return action || key || '—';
}

function cap(s: string) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

/** Best-effort User-Agent → device + navigateur. */
function parseUA(ua?: string | null): string {
  if (!ua) return '';
  const u = ua.toLowerCase();
  const os =
    u.includes('android') ? 'Android'
    : u.includes('iphone') || u.includes('ipad') ? 'iOS'
    : u.includes('mac os') ? 'macOS'
    : u.includes('windows') ? 'Windows'
    : u.includes('linux') ? 'Linux'
    : '';
  const browser =
    u.includes('edg/') ? 'Edge'
    : u.includes('chrome') && !u.includes('edg/') ? 'Chrome'
    : u.includes('firefox') ? 'Firefox'
    : u.includes('safari') && !u.includes('chrome') ? 'Safari'
    : u.includes('flutter') || u.includes('dart:io') ? 'App mobile EpiTrace'
    : '';
  return [os, browser].filter(Boolean).join(' · ');
}

const PAGE_SIZE = 25;

export default function AuditLogsPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // Filtres
  const [source, setSource] = useState<'' | LogSource>('');
  const [severity, setSeverity] = useState<'' | Severity>('');
  const [travelerId, setTravelerId] = useState('');
  const [q, setQ] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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
  useEffect(() => { setPage(1); }, [source, travelerId, debouncedQ, dateFrom, dateTo, severity]);

  const hasFilters = !!(source || severity || travelerId || debouncedQ || dateFrom || dateTo);
  const totalPages = data?.total_pages || 1;

  const sourceCounts = useMemo(() => data?.by_source || {}, [data]);
  const rows = useMemo(() => data?.rows || [], [data]);

  // Filtrage local par sévérité (le backend renvoie déjà la sévérité inférée)
  const filteredRows = useMemo(() => {
    if (!severity) return rows;
    return rows.filter((r) => (r.severity || 'info') === severity);
  }, [rows, severity]);

  // KPIs dérivés (calculés sur la page courante — approximation utile mais claire)
  const kpi = useMemo(() => {
    const total = data?.count ?? 0;
    const uniqueActors = new Set(rows.map((r) => r.user_label).filter(Boolean)).size;
    const critical = rows.filter((r) => (r.severity || 'info') === 'danger').length;
    const scanDenied = rows.filter((r) => r.source === 'pass_scan' && !r.ok).length;
    return { total, uniqueActors, critical, scanDenied };
  }, [data, rows]);

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const exportCSV = () => {
    const header = [
      'date', 'source', 'sévérité', 'acteur', 'rôle', 'action',
      'cible', 'motif', 'IP', 'pass', 'point_entree', 'user_agent', 'request_id',
    ];
    const escape = (v: unknown) => {
      const s = v === null || v === undefined ? '' : String(v);
      return `"${s.replace(/"/g, '""')}"`;
    };
    const lines = [header.join(';')];
    for (const r of filteredRows) {
      lines.push([
        formatDateTime(r.occurred_at),
        SOURCE_META[r.source]?.label || r.source,
        SEVERITY_META[r.severity || 'info']?.label,
        r.user_label,
        r.user_role,
        humanAction(r.action, r.action_code),
        r.target,
        r.reason,
        r.ip_address || '',
        r.pass_number || '',
        r.entry_point || '',
        r.user_agent || '',
        r.request_id || '',
      ].map(escape).join(';'));
    }
    const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    a.download = `audit-logs-${stamp}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Sécurité & audit
          </span>
          <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
            Journaux d'accès aux données
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
            Chaque consultation de données voyageur, chaque scan de pass sanitaire et chaque
            action administrative est tracée ici. Cette page est réservée à l'administration
            nationale (MSHPCMU / INHP) — conservée 5 ans conformément aux obligations légales.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            title="Rafraîchir"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Actualiser
          </button>
          <button
            onClick={exportCSV}
            disabled={filteredRows.length === 0}
            className="inline-flex items-center gap-1.5 rounded-xl bg-ciDark text-white dark:bg-emerald-600 px-3 py-2 text-xs font-bold hover:opacity-90 disabled:opacity-40"
            title="Exporter la page courante en CSV"
          >
            <Download className="h-3.5 w-3.5" /> Export CSV
          </button>
        </div>
      </header>

      {/* Bandeau KPIs — 4 métriques claires */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard
          icon={<Database className="h-5 w-5" />}
          label="Total d'événements"
          value={kpi.total}
          hint="Filtrés selon les critères"
          accent="text-ciDark dark:text-emerald-200"
        />
        <KpiCard
          icon={<User2 className="h-5 w-5" />}
          label="Acteurs distincts"
          value={kpi.uniqueActors}
          hint={`Sur cette page (${rows.length} ligne${rows.length > 1 ? 's' : ''})`}
          accent="text-sky-600"
        />
        <KpiCard
          icon={<ShieldX className="h-5 w-5" />}
          label="Scans refusés"
          value={kpi.scanDenied}
          hint="Pass invalides ou expirés"
          accent="text-rose-600"
        />
        <KpiCard
          icon={<AlertOctagon className="h-5 w-5" />}
          label="Événements critiques"
          value={kpi.critical}
          hint="Suppression, révocation, échec"
          accent="text-amber-600"
        />
      </div>

      {/* Répartition par source — cliquables */}
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

      {/* Barre de filtres */}
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

        <select
          className="select max-w-[160px]"
          value={severity}
          onChange={(e) => setSeverity(e.target.value as '' | Severity)}
          title="Filtrer par sévérité"
        >
          <option value="">Toute sévérité</option>
          <option value="info">Info</option>
          <option value="success">Succès</option>
          <option value="warning">Vigilance</option>
          <option value="danger">Critique</option>
        </select>

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
              setSource(''); setSeverity(''); setTravelerId(''); setQ(''); setDateFrom(''); setDateTo('');
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
                <Th className="w-6"></Th>
                <Th>Quand</Th>
                <Th>Type</Th>
                <Th>Sévérité</Th>
                <Th>Acteur</Th>
                <Th>Action</Th>
                <Th>Cible</Th>
                <Th>Motif / résumé</Th>
                <Th>IP</Th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={9} className="p-8 text-center text-slate-400">Chargement…</td></tr>
              )}
              {!loading && !error && filteredRows.length === 0 && (
                <tr><td colSpan={9} className="p-8 text-center text-slate-400">Aucun journal ne correspond aux filtres.</td></tr>
              )}
              {!loading && filteredRows.map((r) => {
                const meta = SOURCE_META[r.source];
                const sev = r.severity || 'info';
                const sevMeta = SEVERITY_META[sev];
                const isOpen = expanded.has(r.id);
                const label = humanAction(r.action, r.action_code);
                return (
                  <Fragment key={r.id}>
                    <tr
                      className={`border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer ${isOpen ? 'bg-slate-50/70 dark:bg-slate-900/40' : ''}`}
                      onClick={() => toggleExpand(r.id)}
                    >
                      <Td>
                        <button
                          type="button"
                          className="text-slate-400 hover:text-ciOrange"
                          onClick={(e) => { e.stopPropagation(); toggleExpand(r.id); }}
                          aria-label={isOpen ? 'Réduire' : 'Développer'}
                        >
                          {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </button>
                      </Td>
                      <Td className="text-xs text-slate-600 whitespace-nowrap">
                        <div className="flex items-center gap-1 font-semibold text-slate-700 dark:text-slate-200">
                          <Clock className="h-3 w-3" /> {formatDateTime(r.occurred_at)}
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{relTime(r.occurred_at)}</div>
                      </Td>
                      <Td>
                        <span
                          className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold ${meta.color}`}
                          title={meta.hint}
                        >
                          {meta.icon} {meta.short}
                        </span>
                      </Td>
                      <Td>
                        <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold ${sevMeta.className}`}>
                          {sevMeta.icon} {sevMeta.label}
                        </span>
                      </Td>
                      <Td className="text-xs max-w-[180px]">
                        <div className="font-semibold truncate" title={r.user_label}>{r.user_label}</div>
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
                          <span className={r.source === 'pass_scan' && !r.ok ? 'text-rose-700 font-semibold' : 'font-medium'}>
                            {label}
                          </span>
                        </div>
                        {r.entry_point && (
                          <div className="text-[10px] text-slate-500 mt-0.5 flex items-center gap-1">
                            <MapPin className="h-2.5 w-2.5" /> {r.entry_point}
                          </div>
                        )}
                        {r.pass_number && (
                          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                            {r.pass_number}
                          </div>
                        )}
                      </Td>
                      <Td className="font-mono text-xs">
                        {r.target ? (
                          <span className="inline-flex items-center gap-1 rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5">
                            {r.target}
                          </span>
                        ) : '—'}
                      </Td>
                      <Td className="text-xs text-slate-600 max-w-[260px]">
                        <div className="truncate" title={r.reason}>{r.reason || '—'}</div>
                      </Td>
                      <Td className="text-xs text-slate-500 font-mono">
                        {r.ip_address || '—'}
                      </Td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-slate-50/50 dark:bg-slate-900/20 border-t border-slate-100 dark:border-slate-800">
                        <td></td>
                        <td colSpan={8} className="px-3 py-4">
                          <DetailPanel row={r} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && data && data.count > 0 && (
          <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 px-4 py-3 text-sm">
            <div className="text-xs text-slate-500">
              <span className="font-bold text-slate-700 dark:text-slate-200">{data.count}</span> entrée{data.count > 1 ? 's' : ''} — page{' '}
              <span className="font-bold text-slate-700 dark:text-slate-200">{page}</span> / {totalPages}
              {severity && (
                <span className="ml-2 text-slate-400">
                  · {filteredRows.length} affichée{filteredRows.length > 1 ? 's' : ''} (filtre sévérité)
                </span>
              )}
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
          Pour un export forensique complet (toutes consultations sur une période, tentatives
          d'accès refusées, exports massifs), contactez l'équipe sécurité MSHPCMU. Les données
          sont conservées 5 ans conformément aux obligations légales (arrêté MSHPCMU).
        </p>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* Composants internes                                                    */
/* ---------------------------------------------------------------------- */

function DetailPanel({ row }: { row: AuditRow }) {
  const ua = parseUA(row.user_agent);
  return (
    <div className="grid md:grid-cols-3 gap-4 text-xs">
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-950">
        <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-2 flex items-center gap-1">
          <User2 className="h-3 w-3" /> Contexte d'accès
        </div>
        <dl className="space-y-1.5">
          <Field label="Adresse IP" value={row.ip_address || '—'} mono />
          <Field label="Navigateur / device" value={ua || '—'} />
          <Field label="Full user-agent" value={row.user_agent || '—'} mono clamp />
          {row.request_id && <Field label="Request-ID" value={row.request_id} mono />}
        </dl>
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-950">
        <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-2 flex items-center gap-1">
          <Activity className="h-3 w-3" /> Événement
        </div>
        <dl className="space-y-1.5">
          <Field label="Type" value={SOURCE_META[row.source].label} />
          <Field label="Action" value={humanAction(row.action, row.action_code)} />
          <Field label="Code brut" value={row.action_code || row.action} mono />
          {row.entry_point && <Field label="Point d'entrée" value={row.entry_point} />}
          {row.pass_number && <Field label="N° pass" value={row.pass_number} mono />}
          {row.target && <Field label="Cible" value={row.target} mono />}
        </dl>
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-950">
        <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-2 flex items-center gap-1">
          <FileText className="h-3 w-3" /> Détails
        </div>
        <div>
          <div className="text-[10px] text-slate-500 mb-1">Motif / résumé</div>
          <div className="text-sm text-slate-700 dark:text-slate-200">
            {row.reason || <span className="text-slate-400 italic">Aucun motif renseigné.</span>}
          </div>
        </div>
        {row.payload && Object.keys(row.payload).length > 0 && (
          <div className="mt-3">
            <div className="text-[10px] text-slate-500 mb-1">Payload</div>
            <pre className="max-h-40 overflow-auto rounded bg-slate-900 text-emerald-100 text-[10px] p-2 font-mono">
              {JSON.stringify(row.payload, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, mono, clamp }: { label: string; value: string; mono?: boolean; clamp?: boolean }) {
  return (
    <div className="flex items-start gap-2">
      <dt className="text-[10px] uppercase tracking-wide text-slate-500 w-24 shrink-0 pt-0.5">{label}</dt>
      <dd className={`flex-1 min-w-0 text-slate-700 dark:text-slate-200 ${mono ? 'font-mono text-[11px]' : ''} ${clamp ? 'break-words line-clamp-3' : 'break-words'}`}>
        {value}
      </dd>
    </div>
  );
}

function KpiCard({
  icon, label, value, hint, accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between text-slate-500 text-[11px] uppercase tracking-wide">
        <span>{label}</span>
        <span className={accent || 'text-ciOrange'}>{icon}</span>
      </div>
      <div className={`mt-1 font-display text-2xl md:text-3xl font-black ${accent || 'text-ciDark dark:text-emerald-100'}`}>
        {value.toLocaleString('fr-FR')}
      </div>
      {hint && <div className="text-[10px] text-slate-400 mt-0.5">{hint}</div>}
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
      title={meta.hint}
    >
      <div className="flex items-center justify-between">
        <div className={`inline-flex items-center justify-center h-10 w-10 rounded-xl ${meta.color}`}>
          {meta.icon}
        </div>
        {active && (
          <span className="text-[10px] font-bold text-ciOrange uppercase">Filtré</span>
        )}
      </div>
      <div className="mt-2 text-2xl font-display font-black text-ciDark dark:text-emerald-100">{count}</div>
      <div className="text-xs text-slate-500 mt-0.5">{meta.label}</div>
      <div className="mt-2 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
        <div className={`h-full ${meta.bar}`} style={{ width: `${Math.min(100, count > 0 ? Math.max(6, count * 2) : 0)}%` }} />
      </div>
    </button>
  );
}

function Th({ children, className = '' }: { children?: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-500 ${className}`}>{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-3 align-top ${className}`}>{children}</td>;
}

/** Format « il y a X min / X h / X j ». */
function relTime(iso: string): string {
  try {
    const d = new Date(iso).getTime();
    const now = Date.now();
    const diff = Math.max(0, now - d);
    const mn = Math.floor(diff / 60_000);
    if (mn < 1) return 'à l\'instant';
    if (mn < 60) return `il y a ${mn} min`;
    const h = Math.floor(mn / 60);
    if (h < 24) return `il y a ${h} h`;
    const j = Math.floor(h / 24);
    if (j < 30) return `il y a ${j} j`;
    return new Date(iso).toLocaleDateString('fr-FR');
  } catch {
    return '';
  }
}
