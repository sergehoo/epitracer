'use client';

/**
 * /dashboard/notifications/echecs
 *
 * Vue dédiée aux notifications en échec (status=failed).
 * Permet de relancer une notif à la fois OU plusieurs en lot, OU toutes
 * celles des dernières 24h en un clic.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  AlertTriangle, RefreshCcw, Check, X, MessageCircle, Smartphone,
  ChevronLeft, ChevronRight, Calendar, Filter, Phone, Send, ArrowLeft,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface FailedNotif {
  id: number;
  uuid: string;
  channel: 'sms' | 'whatsapp' | 'email' | 'push';
  provider: string;
  recipient: string;
  masked_recipient: string;
  body: string;
  error_message: string;
  retry_count: number;
  max_retries: number;
  failed_at: string;
  created_at: string;
  traveler?: { public_id: string; full_name?: string } | null;
  sent_by?: { email: string } | null;
}

const PROVIDER_OPTS = [
  { value: '', label: 'Tous les providers' },
  { value: 'orange_ci', label: 'Orange CI' },
  { value: 'twilio', label: 'Twilio' },
  { value: 'meta_whatsapp', label: 'Meta WhatsApp' },
];

const CHANNEL_OPTS = [
  { value: '', label: 'Tous canaux' },
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'email', label: 'Email' },
];

const TIME_OPTS = [
  { value: '24', label: 'Dernières 24 h' },
  { value: '168', label: '7 derniers jours' },
  { value: '720', label: '30 derniers jours' },
  { value: '', label: 'Tout l\'historique' },
];

export default function NotificationsFailedPage() {
  const [items, setItems] = useState<FailedNotif[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);

  // Filtres
  const [provider, setProvider] = useState('');
  const [channel, setChannel] = useState('sms'); // SMS par défaut (focus du besoin)
  const [hoursWindow, setHoursWindow] = useState('24');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {
        status: 'failed',
        page: String(page),
        page_size: String(pageSize),
        ordering: '-failed_at',
      };
      if (provider) params.provider = provider;
      if (channel) params.channel = channel;
      const r = await api.get('/notifications/', { params });
      let results = (r.data.results || r.data) as FailedNotif[];
      // Filtre client-side sur la fenêtre temporelle (DRF ne le supporte pas direct)
      if (hoursWindow) {
        const cutoff = Date.now() - parseInt(hoursWindow, 10) * 3600 * 1000;
        results = results.filter((n) => {
          const t = new Date(n.failed_at || n.created_at).getTime();
          return t >= cutoff;
        });
      }
      setItems(results);
      setCount(r.data.count ?? results.length);
      setSelected(new Set());
    } catch (e) {
      setError(extractApiError(e));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, provider, channel, hoursWindow]);

  useEffect(() => {
    load();
  }, [load]);

  // ── Actions ────────────────────────────────────────────────────────────
  const retryOne = async (id: number) => {
    setBusy(true);
    try {
      await api.post(`/notifications/${id}/retry/`);
      await load();
    } catch (e) {
      alert('Échec relance : ' + extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const retrySelection = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Relancer ${selected.size} notification(s) sélectionnée(s) ?`)) return;
    setBusy(true);
    try {
      const r = await api.post('/notifications/bulk-retry/', { ids: Array.from(selected) });
      alert(`✅ ${r.data.requeued} notification(s) remises en file.`);
      await load();
    } catch (e) {
      alert('Échec relance en lot : ' + extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const retryAllRecent = async () => {
    const hours = parseInt(hoursWindow || '24', 10) || 24;
    if (!confirm(
      `Relancer TOUTES les notifications FAILED des ${hours} dernières heures ?\n\n` +
      `Cap de sécurité : 500 max.`,
    )) return;
    setBusy(true);
    try {
      const r = await api.post('/notifications/bulk-retry/', {
        all_failed: true,
        max_age_hours: hours,
      });
      alert(`✅ ${r.data.requeued} notification(s) remises en file.`);
      await load();
    } catch (e) {
      alert('Échec relance globale : ' + extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const toggleAll = () => {
    if (selected.size === items.length) setSelected(new Set());
    else setSelected(new Set(items.map((n) => n.id)));
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
            <ArrowLeft className="h-3 w-3" /> Retour à toutes les notifications
          </Link>
          <span className="text-xs uppercase tracking-widest text-rose-600 font-bold">
            Échecs d'envoi
          </span>
          <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
            Notifications en échec
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
            Liste des messages dont l'envoi a échoué. Vous pouvez relancer une notification
            individuellement, plusieurs en lot, ou toutes celles d'une période donnée.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
          <button
            onClick={retryAllRecent}
            disabled={busy || items.length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ciOrange text-white px-3 py-2 text-xs font-bold hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-3.5 w-3.5" />
            Relancer tous les échecs
          </button>
        </div>
      </header>

      {/* KPI échecs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Kpi label="Échecs affichés" value={items.length} tone="rose" icon={<AlertTriangle className="h-4 w-4" />} />
        <Kpi label="Sélectionnés" value={selected.size} tone="amber" icon={<Check className="h-4 w-4" />} />
        <Kpi label="Total filtré" value={count} tone="slate" icon={<Filter className="h-4 w-4" />} />
        <Kpi label="Avec retry possible" value={items.filter((n) => n.retry_count < (n.max_retries || 3)).length} tone="sky" icon={<RefreshCcw className="h-4 w-4" />} />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Canal</label>
          <select
            value={channel}
            onChange={(e) => { setChannel(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs"
          >
            {CHANNEL_OPTS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Provider</label>
          <select
            value={provider}
            onChange={(e) => { setProvider(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs"
          >
            {PROVIDER_OPTS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Période</label>
          <select
            value={hoursWindow}
            onChange={(e) => { setHoursWindow(e.target.value); setPage(1); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs"
          >
            {TIME_OPTS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        {selected.size > 0 && (
          <button
            onClick={retrySelection}
            disabled={busy}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 text-white px-3 py-2 text-xs font-bold hover:bg-emerald-700 disabled:opacity-50"
          >
            <RefreshCcw className="h-3.5 w-3.5" />
            Relancer {selected.size} sélectionnée(s)
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
                  <input
                    type="checkbox"
                    checked={allChecked}
                    onChange={toggleAll}
                    className="rounded"
                  />
                </th>
                <th className="px-3 py-2">Date échec</th>
                <th className="px-3 py-2">Canal · Provider</th>
                <th className="px-3 py-2">Destinataire</th>
                <th className="px-3 py-2">Voyageur</th>
                <th className="px-3 py-2">Erreur</th>
                <th className="px-3 py-2 text-center">Retries</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-xs text-slate-400">
                    Chargement…
                  </td>
                </tr>
              )}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-8 text-center">
                    <div className="text-emerald-600 dark:text-emerald-400">
                      <Check className="h-8 w-8 mx-auto mb-2" />
                      <p className="text-sm font-bold">Aucun échec sur la période</p>
                      <p className="text-xs text-slate-500 mt-1">Tout est délivré ou en cours.</p>
                    </div>
                  </td>
                </tr>
              )}
              {items.map((n) => {
                const canRetry = n.retry_count < (n.max_retries || 3);
                return (
                  <tr key={n.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="px-3 py-2 align-top">
                      <input
                        type="checkbox"
                        checked={selected.has(n.id)}
                        onChange={() => toggleSelect(n.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-3 py-2 align-top text-xs">
                      {n.failed_at
                        ? new Date(n.failed_at).toLocaleString('fr-FR', {
                            day: '2-digit', month: '2-digit', year: '2-digit',
                            hour: '2-digit', minute: '2-digit',
                          })
                        : '—'}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex items-center gap-1.5 text-xs">
                        {n.channel === 'sms' && <Smartphone className="h-3.5 w-3.5 text-sky-600" />}
                        {n.channel === 'whatsapp' && <MessageCircle className="h-3.5 w-3.5 text-emerald-600" />}
                        <span className="font-semibold uppercase">{n.channel}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 uppercase tracking-wide">
                        {n.provider}
                      </span>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex items-center gap-1.5 text-xs font-mono">
                        <Phone className="h-3 w-3 text-slate-400" />
                        {n.masked_recipient || n.recipient}
                      </div>
                    </td>
                    <td className="px-3 py-2 align-top text-xs">
                      {n.traveler ? (
                        <Link
                          href={`/surveillance/${n.traveler.public_id}`}
                          className="text-ciOrange hover:underline font-semibold"
                        >
                          {n.traveler.public_id}
                        </Link>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top max-w-md">
                      <p
                        className="text-xs text-rose-700 dark:text-rose-300 line-clamp-2"
                        title={n.error_message}
                      >
                        {n.error_message || '—'}
                      </p>
                    </td>
                    <td className="px-3 py-2 align-top text-center">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          canRetry
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {n.retry_count}/{n.max_retries || 3}
                      </span>
                    </td>
                    <td className="px-3 py-2 align-top text-right">
                      <button
                        onClick={() => retryOne(n.id)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 rounded-md bg-ciOrange/10 hover:bg-ciOrange/20 text-ciOrange px-2 py-1 text-[11px] font-bold disabled:opacity-50"
                      >
                        <RefreshCcw className="h-3 w-3" />
                        Relancer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3 border-t border-slate-200 dark:border-slate-700 text-xs">
            <span className="text-slate-500">
              Page {page} / {totalPages} — {count} échec(s) au total
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <ChevronLeft className="h-3 w-3" /> Précédent
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="inline-flex items-center gap-1 rounded border border-slate-200 dark:border-slate-700 px-2 py-1 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Suivant <ChevronRight className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

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
