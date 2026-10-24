'use client';

/**
 * /notifications — Historique global des notifications.
 *
 * Bandeau de disponibilité des fournisseurs (crédit Orange CI épuisé →
 * envois en attente + reprise contrôlée), indicateurs calculés côté serveur
 * sur la sélection, filtres combinables, tableau compact paginé et panneau
 * de détail par message.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  AlertTriangle, Ban, CheckCircle2, ChevronRight, Clock, Copy, PauseCircle,
  PlayCircle, RefreshCcw, Search, Send, ShieldCheck, Smartphone, X, XCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { Pagination } from '@/components/ui/Pagination';
import {
  NOTIF_CHANNEL, NOTIF_PROVIDER, NOTIF_STATUS, NOTIF_TYPE,
  type NotificationItem, type NotificationStats, type ProviderStatus,
} from '@/lib/notifications';

interface Filters {
  search: string;
  date_from: string;
  date_to: string;
  status: string;
  channel: string;
  provider: string;
  disease: string;
}

const EMPTY_FILTERS: Filters = {
  search: '', date_from: '', date_to: '', status: '', channel: '', provider: '', disease: '',
};

const STATUS_FILTERS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'sent_all', label: 'Envoyés (dont délivrés)' },
  { value: 'delivered', label: 'Délivrés' },
  { value: 'failed', label: 'Échecs' },
  { value: 'waiting', label: 'En attente (tous)' },
  { value: 'on_hold', label: 'Attente fournisseur' },
  { value: 'cancelled', label: 'Annulés' },
];

const CHANNEL_FILTERS = ['', 'sms', 'whatsapp', 'email', 'push', 'telegram'];
const PROVIDER_FILTERS = ['', 'orange_ci', 'twilio', 'meta_whatsapp', 'smtp', 'fcm', 'telegram_bot'];
const PAGE_SIZES = [25, 50, 100];

function toParams(f: Filters): Record<string, string> {
  const p: Record<string, string> = {};
  (Object.keys(f) as (keyof Filters)[]).forEach((k) => {
    const v = f[k].trim();
    if (v) p[k] = v;
  });
  return p;
}

export default function NotificationsPage() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const [items, setItems] = useState<NotificationItem[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [stats, setStats] = useState<NotificationStats | null>(null);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [diseases, setDiseases] = useState<{ id: number; code: string; name: string }[]>([]);
  const [selected, setSelected] = useState<NotificationItem | null>(null);

  // Recherche : saisie libre appliquée après une courte pause.
  useEffect(() => {
    const t = setTimeout(() => {
      setFilters((f) => (f.search === searchInput ? f : { ...f, search: searchInput }));
      setPage(1);
    }, 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const setFilter = (key: keyof Filters, value: string) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get('/notifications/', {
        params: { ...toParams(filters), page, page_size: pageSize, ordering: '-created_at' },
      });
      setItems(r.data.results || r.data);
      setCount(r.data.count ?? (r.data.results || r.data).length);
    } catch (e) {
      setError(extractApiError(e));
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);

  const loadStats = useCallback(() => {
    api.get('/notifications/stats/', { params: toParams(filters) })
      .then((r) => setStats(r.data))
      .catch(() => setStats(null));
  }, [filters]);

  const loadProviders = useCallback(() => {
    api.get('/notifications/providers/')
      .then((r) => setProviders(r.data.results || []))
      .catch(() => setProviders([]));
  }, []);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { loadStats(); }, [loadStats]);
  useEffect(() => { loadProviders(); }, [loadProviders]);
  useEffect(() => {
    api.get('/diseases/?page_size=100')
      .then((r) => setDiseases(r.data.results || r.data))
      .catch(() => setDiseases([]));
  }, []);

  const refreshAll = () => { loadList(); loadStats(); loadProviders(); };
  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-ciOrange">Communication voyageurs</span>
          <h1 className="mt-1 font-display text-2xl font-black text-ciDark dark:text-emerald-100 md:text-3xl">
            Notifications &amp; messages
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Historique des SMS, WhatsApp, emails et push. Numéros ivoiriens (+225) → Orange CI uniquement,
            autres numéros → Twilio.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/notifications/emails"
            className="inline-flex items-center gap-1.5 rounded-lg bg-sky-100 px-3 py-2 text-xs font-bold text-sky-800 transition hover:bg-sky-200"
          >
            <Send className="h-3.5 w-3.5" aria-hidden="true" /> Historique emails
          </Link>
          <Link
            href="/notifications/echecs"
            className="inline-flex items-center gap-1.5 rounded-lg bg-rose-100 px-3 py-2 text-xs font-bold text-rose-800 transition hover:bg-rose-200"
          >
            <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" /> Gérer les échecs
          </Link>
          <button
            type="button"
            onClick={refreshAll}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <RefreshCcw className="h-3.5 w-3.5" aria-hidden="true" /> Actualiser
          </button>
        </div>
      </header>

      <ProviderBanner providers={providers} onResumed={refreshAll} />

      <KpiRow stats={stats} />

      {/* Filtres */}
      <section aria-label="Filtres" className="card space-y-3 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[14rem] flex-1">
            <label htmlFor="notif-search" className="mb-1 block text-xs font-medium text-slate-500">Recherche</label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <input
                id="notif-search"
                type="search"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Téléphone, nom, ID voyageur, texte du message…"
                className="input w-full !pl-8 text-sm"
              />
            </div>
          </div>
          <FilterDate id="notif-from" label="Du" value={filters.date_from} max={filters.date_to || undefined} onChange={(v) => setFilter('date_from', v)} />
          <FilterDate id="notif-to" label="Au" value={filters.date_to} min={filters.date_from || undefined} onChange={(v) => setFilter('date_to', v)} />
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <FilterSelect id="notif-status" label="Statut" value={filters.status} onChange={(v) => setFilter('status', v)}
            options={STATUS_FILTERS} />
          <FilterSelect id="notif-channel" label="Canal" value={filters.channel} onChange={(v) => setFilter('channel', v)}
            options={CHANNEL_FILTERS.map((c) => ({ value: c, label: c ? NOTIF_CHANNEL[c] : 'Tous les canaux' }))} />
          <FilterSelect id="notif-provider" label="Fournisseur" value={filters.provider} onChange={(v) => setFilter('provider', v)}
            options={PROVIDER_FILTERS.map((p) => ({ value: p, label: p ? NOTIF_PROVIDER[p] : 'Tous les fournisseurs' }))} />
          <FilterSelect id="notif-disease" label="Maladie suivie" value={filters.disease} onChange={(v) => setFilter('disease', v)}
            options={[{ value: '', label: 'Toutes les maladies' }, ...diseases.map((d) => ({ value: d.code, label: d.name }))]} />
        </div>
        {hasFilters && (
          <button
            type="button"
            onClick={() => { setFilters(EMPTY_FILTERS); setSearchInput(''); setPage(1); }}
            className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" /> Réinitialiser les filtres
          </button>
        )}
      </section>

      {/* Tableau */}
      <section aria-label="Historique des notifications" className="card overflow-hidden p-0">
        {error && (
          <p role="alert" className="border-b border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
            {error}
          </p>
        )}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[48rem] text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Date</th>
                <th scope="col" className="px-3 py-2 font-semibold">Statut</th>
                <th scope="col" className="px-3 py-2 font-semibold">Destinataire</th>
                <th scope="col" className="px-3 py-2 font-semibold">Canal · fournisseur</th>
                <th scope="col" className="px-3 py-2 font-semibold">Type</th>
                <th scope="col" className="px-3 py-2 font-semibold">Message</th>
                <th scope="col" className="px-3 py-2"><span className="sr-only">Détails</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && items.length === 0 && Array.from({ length: 6 }).map((_, i) => (
                <tr key={`sk-${i}`}><td colSpan={7} className="px-3 py-3"><div className="h-4 animate-pulse rounded bg-slate-100 dark:bg-slate-800" /></td></tr>
              ))}
              {!loading && items.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-10 text-center text-sm text-slate-400">Aucune notification pour cette sélection.</td></tr>
              )}
              {items.map((n) => (
                <tr
                  key={n.uuid}
                  onClick={() => setSelected(n)}
                  className={`cursor-pointer align-top transition hover:bg-slate-50 dark:hover:bg-slate-800/50 ${loading ? 'opacity-60' : ''}`}
                >
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-[11px] text-slate-500">{formatDateTime(n.created_at)}</td>
                  <td className="whitespace-nowrap px-3 py-2"><StatusBadge status={n.status} /></td>
                  <td className="px-3 py-2">
                    <div className="font-mono">{n.masked_recipient || n.recipient}</div>
                    {(n.traveler_name || n.traveler_public_id) && (
                      <div className="max-w-[12rem] truncate text-[11px] text-slate-500">
                        {n.traveler_name || n.traveler_public_id}
                      </div>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span className="font-semibold">{NOTIF_CHANNEL[n.channel] || n.channel}</span>
                    {n.provider && <span className="text-slate-500"> · {NOTIF_PROVIDER[n.provider] || n.provider}</span>}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600 dark:text-slate-300">{NOTIF_TYPE[n.message_type] || n.message_type}</td>
                  <td className="max-w-[18rem] px-3 py-2">
                    <p className="truncate text-slate-700 dark:text-slate-200">{n.subject || n.body}</p>
                    {n.error_message && (
                      <p className="mt-0.5 truncate text-[11px] text-rose-600 dark:text-rose-400">{n.error_message}</p>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setSelected(n); }}
                      className="inline-flex items-center rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
                      aria-label={`Détails du message du ${formatDateTime(n.created_at)}`}
                    >
                      <ChevronRight className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 dark:border-slate-800">
          <div className="flex-1">
            <Pagination page={page} total={count} pageSize={pageSize} onPageChange={setPage} itemLabel="message(s)" />
          </div>
          <label className="flex items-center gap-2 px-4 py-3 text-xs text-slate-500">
            Par page
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
              className="input py-1 text-xs"
            >
              {PAGE_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
        </div>
      </section>

      {selected && (
        <NotificationDrawer
          notif={selected}
          onClose={() => setSelected(null)}
          onChanged={(updated) => { setSelected(updated); loadList(); loadStats(); }}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------------ */

function StatusBadge({ status }: { status: string }) {
  const meta = NOTIF_STATUS[status] || NOTIF_STATUS.pending;
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold ${meta.className}`}>
      {meta.label}
    </span>
  );
}

function FilterSelect({
  id, label, value, onChange, options,
}: {
  id: string; label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className="input w-full text-sm">
        {options.map((o) => <option key={o.value || 'all'} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function FilterDate({
  id, label, value, onChange, min, max,
}: {
  id: string; label: string; value: string; onChange: (v: string) => void; min?: string; max?: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <input id={id} type="date" value={value} min={min} max={max} onChange={(e) => onChange(e.target.value)} className="input text-sm" />
    </div>
  );
}

function KpiRow({ stats }: { stats: NotificationStats | null }) {
  const n = (v?: number) => (stats ? (v ?? 0).toLocaleString('fr-FR') : '—');
  const sms = stats?.sms;
  return (
    <section aria-label="Indicateurs sur la sélection" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <Kpi label="Envoyées" value={n(stats?.sent)} hint={stats ? `dont ${n(stats.delivered)} délivrées` : undefined}
        icon={<CheckCircle2 className="h-4 w-4" />} tone="emerald" />
      <Kpi label="Échouées" value={n(stats?.failed)} hint={stats?.cancelled ? `${n(stats.cancelled)} annulées` : undefined}
        icon={<XCircle className="h-4 w-4" />} tone="rose" />
      <Kpi label="En attente" value={n(stats?.pending)}
        hint={stats?.on_hold ? `dont ${n(stats.on_hold)} en attente fournisseur` : undefined}
        icon={<Clock className="h-4 w-4" />} tone="amber" />
      <Kpi label="Doublons évités" value={n(stats?.duplicates_avoided)} hint="rappels non renvoyés sur la période"
        icon={<ShieldCheck className="h-4 w-4" />} tone="sky" />
      <Kpi
        label="Consommation SMS"
        value={sms ? `${sms.segments.toLocaleString('fr-FR')} SMS` : '—'}
        hint={sms ? (sms.by_provider.length
          ? sms.by_provider.map((p) => `${NOTIF_PROVIDER[p.provider] || p.provider} ${p.segments}`).join(' · ')
          : `${sms.messages} message(s)`) : undefined}
        icon={<Smartphone className="h-4 w-4" />} tone="slate"
      />
    </section>
  );
}

function Kpi({
  label, value, hint, icon, tone,
}: {
  label: string; value: string; hint?: string; icon: React.ReactNode;
  tone: 'emerald' | 'sky' | 'amber' | 'rose' | 'slate';
}) {
  const tones = {
    emerald: 'border-emerald-200/70 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200',
    sky: 'border-sky-200/70 bg-sky-50 text-sky-800 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200',
    amber: 'border-amber-200/70 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200',
    rose: 'border-rose-200/70 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200',
    slate: 'border-slate-200/70 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200',
  };
  return (
    <div className={`rounded-2xl border p-3 ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wide opacity-80">{label}</span>
        <span className="opacity-60" aria-hidden="true">{icon}</span>
      </div>
      <div className="mt-1 font-display text-2xl font-black">{value}</div>
      {hint && <div className="mt-0.5 truncate text-[11px] opacity-80" title={hint}>{hint}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------------ */

function ProviderBanner({ providers, onResumed }: { providers: ProviderStatus[]; onResumed: () => void }) {
  const [confirm, setConfirm] = useState<ProviderStatus | null>(null);
  const suspended = providers.filter((p) => p.is_suspended);
  if (suspended.length === 0) return null;
  return (
    <>
      {suspended.map((p) => (
        <div
          key={p.provider}
          role="alert"
          className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-orange-300 bg-orange-50 p-4 text-orange-900 dark:border-orange-800 dark:bg-orange-950/40 dark:text-orange-100"
        >
          <div className="flex min-w-0 flex-1 items-start gap-3">
            <PauseCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <div className="min-w-0">
              <p className="font-bold">
                {p.provider_label} — {p.state === 'quota_exhausted' ? 'crédit épuisé' : 'fournisseur indisponible'}
              </p>
              <p className="mt-0.5 text-sm">
                Envois suspendus depuis le {formatDateTime(p.suspended_at)}.{' '}
                {p.held_count > 0 ? `${p.held_count} message(s) en attente` : 'Aucun message en attente'} ;
                aucune nouvelle tentative et aucune bascule vers un autre fournisseur pour les numéros +225.
              </p>
              {p.technical_detail && (
                <details className="mt-1 text-xs">
                  <summary className="cursor-pointer font-semibold">Détail technique (administrateurs)</summary>
                  <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap break-all rounded bg-white/70 p-2 font-mono text-[11px] dark:bg-black/30">{p.technical_detail}</pre>
                </details>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setConfirm(p)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-orange-600 px-3 py-2 text-xs font-bold text-white hover:bg-orange-700"
          >
            <PlayCircle className="h-4 w-4" aria-hidden="true" /> Reprendre les envois
          </button>
        </div>
      ))}
      {confirm && (
        <ResumeDialog provider={confirm} onClose={() => setConfirm(null)} onDone={() => { setConfirm(null); onResumed(); }} />
      )}
    </>
  );
}

function ResumeDialog({
  provider, onClose, onDone,
}: { provider: ProviderStatus; onClose: () => void; onDone: () => void }) {
  const [requeue, setRequeue] = useState(true);
  const [busy, setBusy] = useState(false);
  useEscape(onClose);

  const submit = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/notifications/providers/${provider.provider}/resume/`, { requeue });
      const { requeued, expired } = r.data as { requeued: number; expired: number };
      toast.success(`${provider.provider_label} réactivé : ${requeued} message(s) renvoyé(s), ${expired} rappel(s) obsolète(s) annulé(s).`);
      onDone();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/50 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="resume-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl dark:bg-slate-900"
      >
        <h2 id="resume-title" className="font-display text-lg font-black">Reprendre les envois {provider.provider_label}</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          À confirmer uniquement après réapprovisionnement du crédit. Les envois automatiques reprendront normalement.
        </p>
        <label className="mt-4 flex items-start gap-2 text-sm">
          <input type="checkbox" checked={requeue} onChange={(e) => setRequeue(e.target.checked)} className="mt-0.5" />
          <span>
            Renvoyer les {provider.held_count} message(s) en attente encore pertinents.
            <span className="block text-xs text-slate-500">
              Les rappels quotidiens d&apos;un jour passé sont annulés pour ne pas envoyer d&apos;information périmée.
            </span>
          </span>
        </label>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">Annuler</button>
          <button
            type="button"
            onClick={submit}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ciGreen px-3 py-2 text-sm font-bold text-white disabled:opacity-50"
          >
            <PlayCircle className="h-4 w-4" aria-hidden="true" /> {busy ? 'Reprise…' : 'Confirmer la reprise'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------ */

function NotificationDrawer({
  notif, onClose, onChanged,
}: { notif: NotificationItem; onClose: () => void; onChanged: (n: NotificationItem) => void }) {
  const [busy, setBusy] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEscape(onClose);
  useEffect(() => { closeRef.current?.focus(); }, [notif.id]);

  const act = async (kind: 'retry' | 'cancel') => {
    setBusy(true);
    try {
      const r = await api.post(`/notifications/${notif.id}/${kind}/`);
      toast.success(kind === 'retry' ? 'Notification relancée' : 'Notification annulée');
      onChanged(r.data);
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const canRetry = notif.status === 'failed' || notif.status === 'cancelled';
  const canCancel = ['pending', 'queued', 'on_hold', 'failed', 'draft'].includes(notif.status);
  const timeline: [string, string | null | undefined][] = [
    ['Créé', notif.created_at],
    ['Mis en file', notif.queued_at],
    ['Envoyé', notif.sent_at],
    ['Délivré', notif.delivered_at],
    ['Échec', notif.failed_at],
  ];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40" onClick={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="notif-drawer-title"
        onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-lg flex-col overflow-y-auto bg-white shadow-2xl dark:bg-slate-900"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 p-4 dark:border-slate-800">
          <div>
            <h2 id="notif-drawer-title" className="font-display text-lg font-black">
              {NOTIF_TYPE[notif.message_type] || 'Message'} · {NOTIF_CHANNEL[notif.channel] || notif.channel}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <StatusBadge status={notif.status} />
              <span>#{notif.id}</span>
            </div>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Fermer" className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="space-y-5 p-4 text-sm">
          {notif.error_message && (
            <div className={`rounded-xl p-3 ${notif.status === 'on_hold' ? 'bg-orange-50 text-orange-900 dark:bg-orange-950/40 dark:text-orange-100' : 'bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-200'}`}>
              <p className="flex items-start gap-2 font-semibold">
                {notif.status === 'on_hold'
                  ? <PauseCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
                {notif.error_message}
              </p>
              {notif.status === 'on_hold' && (
                <p className="mt-1 text-xs">
                  Message conservé : il sera renvoyé lors de la reprise des envois par un administrateur
                  (sauf rappel quotidien devenu obsolète).
                </p>
              )}
              {notif.technical_error && (
                <details className="mt-2 text-xs">
                  <summary className="cursor-pointer font-semibold">Détail technique (administrateurs)</summary>
                  <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded bg-white/70 p-2 font-mono text-[11px] dark:bg-black/30">{notif.technical_error}</pre>
                </details>
              )}
            </div>
          )}

          <dl className="grid grid-cols-[8rem,1fr] gap-x-3 gap-y-2">
            <dt className="text-slate-500">Destinataire</dt>
            <dd className="font-mono">{notif.masked_recipient || notif.recipient}</dd>
            {(notif.traveler_name || notif.traveler_public_id) && (
              <>
                <dt className="text-slate-500">Voyageur</dt>
                <dd>
                  {notif.traveler_public_id ? (
                    <Link href={`/surveillance/${notif.traveler_public_id}`} className="font-semibold text-ciGreen hover:underline">
                      {notif.traveler_name || notif.traveler_public_id}
                    </Link>
                  ) : notif.traveler_name}
                  {notif.traveler_public_id && <span className="ml-1 font-mono text-xs text-slate-500">{notif.traveler_public_id}</span>}
                </dd>
              </>
            )}
            <dt className="text-slate-500">Fournisseur</dt>
            <dd>{NOTIF_PROVIDER[notif.provider] || notif.provider || '—'}</dd>
            <dt className="text-slate-500">Modèle</dt>
            <dd>{notif.template_name || 'Message libre'}</dd>
            <dt className="text-slate-500">Essais</dt>
            <dd>{notif.retry_count}{notif.max_retries ? ` / ${notif.max_retries}` : ''}</dd>
            {notif.sms_segments != null && (
              <>
                <dt className="text-slate-500">SMS facturés</dt>
                <dd>{notif.sms_segments}</dd>
              </>
            )}
            <dt className="text-slate-500">Émis par</dt>
            <dd>{notif.sent_by_email || 'Envoi automatique'}</dd>
          </dl>

          <div>
            <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-500">Message</h3>
            {notif.subject && <p className="mb-1 font-semibold">{notif.subject}</p>}
            {notif.channel === 'email' ? (
              <p className="text-xs text-slate-500">Contenu email : consulter l&apos;historique emails pour l&apos;aperçu.</p>
            ) : (
              <p className="whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-3 text-slate-800 dark:bg-slate-800 dark:text-slate-100">{notif.body}</p>
            )}
            {notif.channel !== 'email' && (
              <button
                type="button"
                onClick={() => { navigator.clipboard?.writeText(notif.body); toast.success('Message copié'); }}
                className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              >
                <Copy className="h-3 w-3" aria-hidden="true" /> Copier
              </button>
            )}
          </div>

          <div>
            <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-500">Chronologie</h3>
            <ol className="space-y-1 text-xs">
              {timeline.filter(([, d]) => d).map(([label, d]) => (
                <li key={label} className="flex justify-between gap-3 border-b border-slate-100 pb-1 dark:border-slate-800">
                  <span>{label}</span><span className="font-mono text-slate-500">{formatDateTime(d)}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {(canRetry || canCancel) && (
          <div className="mt-auto flex flex-wrap justify-end gap-2 border-t border-slate-100 p-4 dark:border-slate-800">
            {canCancel && (
              <button
                type="button"
                disabled={busy}
                onClick={() => act('cancel')}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold disabled:opacity-50 dark:border-slate-700"
              >
                <Ban className="h-3.5 w-3.5" aria-hidden="true" /> Annuler l&apos;envoi
              </button>
            )}
            {canRetry && (
              <button
                type="button"
                disabled={busy}
                onClick={() => act('retry')}
                className="inline-flex items-center gap-1.5 rounded-lg bg-ciGreen px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
              >
                <RefreshCcw className="h-3.5 w-3.5" aria-hidden="true" /> Relancer
              </button>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}

function useEscape(onClose: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
}
