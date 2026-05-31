'use client';

/**
 * /dashboard/notifications/emails
 *
 * Historique des emails envoyés (PUBLIC + INTERNAL) avec filtres,
 * relance unitaire et en lot, KPIs par statut, et indication claire
 * de l'expéditeur utilisé pour chaque type.
 */

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Mail, Send, AlertTriangle, CheckCircle2, Clock, XCircle, Eye,
  RefreshCcw, Filter, Search, Inbox, ArrowLeft, AtSign, Shield,
  Users, ChevronLeft, ChevronRight, ExternalLink,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface EmailLog {
  id: number;
  uuid: string;
  recipient: string;
  masked_recipient: string;
  email_type: string;
  sender_address: string;
  subject: string;
  status: string;
  retry_count: number;
  max_retries: number;
  error_message: string;
  template_code?: string | null;
  sent_at?: string | null;
  failed_at?: string | null;
  created_at: string;
  related_user_email?: string | null;
  related_traveler_public_id?: string | null;
}

const STATUS_OPTS = [
  { value: '', label: 'Tous statuts' },
  { value: 'sent', label: 'Envoyés' },
  { value: 'delivered', label: 'Délivrés' },
  { value: 'opened', label: 'Ouverts' },
  { value: 'clicked', label: 'Cliqués' },
  { value: 'queued', label: 'En file' },
  { value: 'failed', label: 'Échec' },
  { value: 'bounced', label: 'Rejetés' },
  { value: 'cancelled', label: 'Annulés' },
];

const EMAIL_TYPE_OPTS: Array<{ value: string; label: string; scope: 'public' | 'internal' }> = [
  { value: '', label: 'Tous types', scope: 'public' },
  // Public
  { value: 'traveler_info', label: 'Information voyageur', scope: 'public' },
  { value: 'traveler_campaign', label: 'Campagne sensibilisation', scope: 'public' },
  { value: 'health_notification', label: 'Notification sanitaire', scope: 'public' },
  { value: 'followup_reminder', label: 'Rappel suivi 21j', scope: 'public' },
  { value: 'pass_confirmation', label: 'Confirmation pass', scope: 'public' },
  { value: 'public_assistance', label: 'Assistance publique', scope: 'public' },
  { value: 'traveler_alert', label: 'Alerte voyageur', scope: 'public' },
  { value: 'followup_completed', label: 'Fin de suivi', scope: 'public' },
  // Internal
  { value: 'admin_account_created', label: 'Création compte admin', scope: 'internal' },
  { value: 'admin_password_reset', label: 'Reset mot de passe', scope: 'internal' },
  { value: 'admin_security_alert', label: 'Alerte sécurité', scope: 'internal' },
  { value: 'staff_notification', label: 'Notification agent', scope: 'internal' },
  { value: 'internal_report', label: 'Rapport interne', scope: 'internal' },
  { value: 'mfa_notification', label: 'MFA', scope: 'internal' },
  { value: 'user_invitation', label: 'Invitation utilisateur', scope: 'internal' },
  { value: 'system_alert', label: 'Alerte système', scope: 'internal' },
];

const SCOPE_OPTS = [
  { value: '', label: 'Tous expéditeurs' },
  { value: 'public', label: 'PUBLIC (voyageurs)' },
  { value: 'internal', label: 'INTERNAL (admin)' },
];

const STATUS_STYLES: Record<string, string> = {
  sent: 'bg-emerald-100 text-emerald-700',
  delivered: 'bg-emerald-200 text-emerald-800',
  opened: 'bg-sky-100 text-sky-700',
  clicked: 'bg-violet-100 text-violet-700',
  queued: 'bg-blue-100 text-blue-700',
  pending: 'bg-slate-100 text-slate-600',
  failed: 'bg-rose-100 text-rose-700',
  bounced: 'bg-red-200 text-red-800',
  cancelled: 'bg-slate-200 text-slate-500',
};

export default function NotificationsEmailsPage() {
  const [items, setItems] = useState<EmailLog[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [previewLog, setPreviewLog] = useState<EmailLog | null>(null);

  // Filtres
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [scopeFilter, setScopeFilter] = useState('');
  const [search, setSearch] = useState('');

  // KPIs
  const [kpis, setKpis] = useState<Record<string, number>>({});

  const loadKpis = useCallback(() => {
    Promise.all(
      ['sent', 'delivered', 'queued', 'failed', 'bounced'].map((s) =>
        api.get(`/notifications/emails/?status=${s}&page_size=1`)
          .then((r) => [s, r.data.count ?? 0] as const)
          .catch(() => [s, 0] as const)
      )
    ).then((entries) => setKpis(Object.fromEntries(entries)));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {
        page: String(page),
        page_size: String(pageSize),
        ordering: '-created_at',
      };
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.email_type = typeFilter;
      if (search.trim()) params.search = search.trim();
      const r = await api.get('/notifications/emails/', { params });
      let results = (r.data.results || r.data) as EmailLog[];
      // Filtre client-side par scope (public/internal) — basé sur sender_address
      if (scopeFilter === 'public') {
        results = results.filter((e) => e.sender_address.endsWith('@destinationci.com'));
      } else if (scopeFilter === 'internal') {
        results = results.filter((e) => e.sender_address.endsWith('@veillesanitaire.com'));
      }
      setItems(results);
      setCount(r.data.count ?? results.length);
      setSelected(new Set());
    } catch (e) {
      setError(extractApiError(e));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter, typeFilter, scopeFilter, search]);

  useEffect(() => { loadKpis(); }, [loadKpis]);
  useEffect(() => { load(); }, [load]);

  // ── Actions ────────────────────────────────────────────────────────────
  const retryOne = async (id: number) => {
    setBusy(true);
    try {
      await api.post(`/notifications/emails/${id}/retry/`);
      await load();
      await loadKpis();
    } catch (e) {
      alert('Échec relance : ' + extractApiError(e));
    } finally {
      setBusy(false);
    }
  };
  const retrySelection = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Relancer ${selected.size} email(s) sélectionné(s) ?`)) return;
    setBusy(true);
    try {
      const r = await api.post('/notifications/emails/bulk-retry/', { ids: Array.from(selected) });
      alert(`✅ ${r.data.requeued} email(s) re-queué(s).`);
      await load();
      await loadKpis();
    } catch (e) {
      alert('Échec bulk retry : ' + extractApiError(e));
    } finally {
      setBusy(false);
    }
  };
  const retryAllRecent = async () => {
    if (!confirm("Relancer TOUS les emails FAILED des 24 dernières heures ? (Max 500)")) return;
    setBusy(true);
    try {
      const r = await api.post('/notifications/emails/bulk-retry/', {
        all_failed: true, max_age_hours: 24,
      });
      alert(`✅ ${r.data.requeued} email(s) re-queué(s).`);
      await load();
      await loadKpis();
    } catch (e) {
      alert('Échec : ' + extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const toggleSelect = (id: number) => {
    setSelected((p) => {
      const n = new Set(p);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  };
  const toggleAll = () => {
    if (selected.size === items.length) setSelected(new Set());
    else setSelected(new Set(items.map((e) => e.id)));
  };

  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const allChecked = items.length > 0 && selected.size === items.length;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/notifications"
            className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange mb-2"
          >
            <ArrowLeft className="h-3 w-3" /> Toutes les notifications
          </Link>
          <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Communication
          </span>
          <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
            Historique des emails
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
            Suivi des envois automatiques (création comptes, suivi voyageur, alertes, campagnes).
            Deux expéditeurs strictement séparés : <strong>infos@destinationci.com</strong> pour
            les voyageurs, <strong>inhp@veillesanitaire.com</strong> pour l'administration.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { load(); loadKpis(); }}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
          {(kpis.failed || 0) + (kpis.bounced || 0) > 0 && (
            <button
              onClick={retryAllRecent}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg bg-ciOrange text-white px-3 py-2 text-xs font-bold hover:bg-orange-600 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
              Relancer tous les échecs (24h)
            </button>
          )}
        </div>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <Kpi label="Délivrés" value={kpis.delivered ?? 0} tone="emerald" icon={<CheckCircle2 className="h-4 w-4" />} />
        <Kpi label="Envoyés" value={kpis.sent ?? 0} tone="sky" icon={<Send className="h-4 w-4" />} />
        <Kpi label="En file" value={kpis.queued ?? 0} tone="amber" icon={<Clock className="h-4 w-4" />} />
        <Kpi label="Échec" value={kpis.failed ?? 0} tone="rose" icon={<XCircle className="h-4 w-4" />} />
        <Kpi label="Rejetés (bounce)" value={kpis.bounced ?? 0} tone="rose" icon={<AlertTriangle className="h-4 w-4" />} />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Recherche</label>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Email, sujet, erreur..."
              className="pl-7 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs w-56"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Statut</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs"
          >
            {STATUS_OPTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Type d'email</label>
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs"
          >
            {EMAIL_TYPE_OPTS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Expéditeur</label>
          <select
            value={scopeFilter}
            onChange={(e) => { setScopeFilter(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs"
          >
            {SCOPE_OPTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        {selected.size > 0 && (
          <button
            onClick={retrySelection}
            disabled={busy}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 text-white px-3 py-2 text-xs font-bold hover:bg-emerald-700 disabled:opacity-50"
          >
            <RefreshCcw className="h-3.5 w-3.5" />
            Relancer {selected.size} sélectionné(s)
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {error && (
          <div className="bg-rose-50 dark:bg-rose-900/20 border-b border-rose-200 dark:border-rose-800 p-3 text-xs text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
              <tr className="text-left text-xs uppercase text-slate-500">
                <th className="px-3 py-2 w-10">
                  <input type="checkbox" checked={allChecked} onChange={toggleAll} className="rounded" />
                </th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Type / Expéditeur</th>
                <th className="px-3 py-2">Destinataire</th>
                <th className="px-3 py-2">Sujet</th>
                <th className="px-3 py-2 text-center">Statut</th>
                <th className="px-3 py-2 text-center">Retries</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-xs text-slate-400">Chargement…</td>
                </tr>
              )}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-10 text-center">
                    <Inbox className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                    <p className="text-sm font-bold text-slate-500">Aucun email pour ces filtres</p>
                  </td>
                </tr>
              )}
              {items.map((e) => {
                const isInternal = e.sender_address.endsWith('@veillesanitaire.com');
                const typeLabel = EMAIL_TYPE_OPTS.find((t) => t.value === e.email_type)?.label || e.email_type;
                const canRetry = ['failed', 'bounced', 'cancelled'].includes(e.status);
                return (
                  <tr key={e.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="px-3 py-2 align-top">
                      <input
                        type="checkbox"
                        checked={selected.has(e.id)}
                        onChange={() => toggleSelect(e.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-3 py-2 align-top text-xs">
                      {new Date(e.created_at).toLocaleString('fr-FR', {
                        day: '2-digit', month: '2-digit', year: '2-digit',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex items-center gap-1.5 text-xs font-semibold">
                        {isInternal
                          ? <Shield className="h-3.5 w-3.5 text-indigo-600" />
                          : <Users className="h-3.5 w-3.5 text-ciOrange" />}
                        <span>{typeLabel}</span>
                      </div>
                      <span className="block text-[10px] text-slate-400 mt-0.5 font-mono">
                        {e.sender_address}
                      </span>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex items-center gap-1.5 text-xs">
                        <AtSign className="h-3 w-3 text-slate-400" />
                        <span className="font-mono">{e.masked_recipient}</span>
                      </div>
                      {e.related_traveler_public_id && (
                        <Link
                          href={`/surveillance/${e.related_traveler_public_id}`}
                          className="text-[11px] text-ciOrange hover:underline inline-flex items-center gap-0.5 mt-0.5"
                        >
                          Voyageur {e.related_traveler_public_id} <ExternalLink className="h-2.5 w-2.5" />
                        </Link>
                      )}
                      {e.related_user_email && (
                        <span className="block text-[11px] text-slate-400 mt-0.5">{e.related_user_email}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top max-w-xs">
                      <p className="text-xs truncate" title={e.subject}>{e.subject || '—'}</p>
                      {e.error_message && (
                        <p
                          className="text-[11px] text-rose-600 line-clamp-2 mt-0.5"
                          title={e.error_message}
                        >
                          ⚠ {e.error_message}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          STATUS_STYLES[e.status] || 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {STATUS_OPTS.find((s) => s.value === e.status)?.label || e.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 align-top text-center text-xs">
                      <span className={
                        e.retry_count < (e.max_retries || 3)
                          ? 'text-amber-700' : 'text-slate-400'
                      }>
                        {e.retry_count}/{e.max_retries || 3}
                      </span>
                    </td>
                    <td className="px-3 py-2 align-top text-right space-x-1">
                      <button
                        onClick={() => setPreviewLog(e)}
                        title="Aperçu"
                        className="inline-flex items-center rounded-md p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                      {canRetry && (
                        <button
                          onClick={() => retryOne(e.id)}
                          disabled={busy}
                          title="Relancer"
                          className="inline-flex items-center gap-1 rounded-md bg-ciOrange/10 hover:bg-ciOrange/20 text-ciOrange px-2 py-1 text-[11px] font-bold disabled:opacity-50"
                        >
                          <RefreshCcw className="h-3 w-3" />
                          Relancer
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3 border-t border-slate-200 dark:border-slate-700 text-xs">
            <span className="text-slate-500">
              Page {page} / {totalPages} — {count} email(s)
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronLeft className="h-3 w-3" /> Précédent
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 disabled:opacity-40 hover:bg-slate-50"
              >
                Suivant <ChevronRight className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal aperçu */}
      {previewLog && (
        <PreviewModal log={previewLog} onClose={() => setPreviewLog(null)} />
      )}
    </div>
  );
}

/* ============================================================ */
/*                       UI HELPERS                              */
/* ============================================================ */

function Kpi({
  label, value, icon, tone,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: 'emerald' | 'sky' | 'amber' | 'rose' | 'slate';
}) {
  const tones = {
    emerald: 'from-emerald-50 to-teal-50 text-emerald-700 border-emerald-200/60',
    sky: 'from-sky-50 to-blue-50 text-sky-700 border-sky-200/60',
    amber: 'from-amber-50 to-yellow-50 text-amber-700 border-amber-200/60',
    rose: 'from-rose-50 to-pink-50 text-rose-700 border-rose-200/60',
    slate: 'from-slate-50 to-gray-50 text-slate-700 border-slate-200/60',
  };
  return (
    <div className={`p-3 rounded-2xl border bg-gradient-to-br ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide font-bold opacity-80">{label}</span>
        <span className="opacity-50">{icon}</span>
      </div>
      <div className="mt-1 font-display text-2xl font-black">{value}</div>
    </div>
  );
}

function PreviewModal({ log, onClose }: { log: EmailLog; onClose: () => void }) {
  const [detail, setDetail] = useState<any>(null);
  useEffect(() => {
    api.get(`/notifications/emails/${log.id}/`).then((r) => setDetail(r.data)).catch(() => undefined);
  }, [log.id]);

  const html = detail?.body_html || '';
  const text = detail?.body_text || '';

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-start justify-between gap-2">
          <div>
            <h2 className="font-display text-lg font-black text-ciDark dark:text-emerald-100">
              {log.subject || '—'}
            </h2>
            <div className="text-xs text-slate-500 mt-1 space-y-0.5">
              <div><strong>De :</strong> <code>{log.sender_address}</code></div>
              <div><strong>À :</strong> <code>{log.recipient}</code></div>
              <div><strong>Type :</strong> {log.email_type}</div>
              <div><strong>Statut :</strong> {log.status} · retries {log.retry_count}/{log.max_retries || 3}</div>
              {log.error_message && (
                <div className="text-rose-600 mt-1"><strong>Erreur :</strong> {log.error_message}</div>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-xl leading-none px-2"
            aria-label="Fermer"
          >
            ×
          </button>
        </header>
        <div className="overflow-auto p-4 flex-1">
          {!detail && <p className="text-xs text-slate-400 text-center">Chargement du contenu…</p>}
          {detail && html && (
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              {/* iframe pour isoler le HTML envoyé du DOM admin */}
              <iframe
                title="Aperçu email"
                srcDoc={html}
                className="w-full min-h-[400px] bg-white"
                sandbox=""
              />
            </div>
          )}
          {detail && !html && text && (
            <pre className="whitespace-pre-wrap text-xs font-mono bg-slate-50 dark:bg-slate-800 p-3 rounded-xl">
              {text}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
