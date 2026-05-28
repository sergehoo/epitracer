'use client';

/**
 * NotificationHistory — Liste des notifications envoyées à un voyageur,
 * ou liste globale si `publicId` est null.
 */

import { useEffect, useState } from 'react';
import {
  CheckCircle2, Clock, MessageCircle, Send, Smartphone, XCircle,
  AlertTriangle, RefreshCw, Wifi, User,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface NotificationItem {
  id: number;
  uuid: string;
  channel: string;
  template_code?: string | null;
  template_name?: string | null;
  traveler_public_id?: string | null;
  recipient: string;
  normalized_phone: string;
  masked_recipient: string;
  subject: string;
  body: string;
  message_type: string;
  status: string;
  provider: string;
  provider_message_id: string;
  error_message: string;
  retry_count: number;
  sent_by_email?: string | null;
  queued_at?: string | null;
  sent_at?: string | null;
  delivered_at?: string | null;
  failed_at?: string | null;
  created_at: string;
}

const STATUS_META: Record<string, { label: string; icon: React.ReactNode; class: string }> = {
  draft:     { label: 'Brouillon',  icon: <Clock className="h-3 w-3" />, class: 'bg-slate-100 text-slate-600' },
  pending:   { label: 'En attente', icon: <Clock className="h-3 w-3" />, class: 'bg-amber-100 text-amber-700' },
  queued:    { label: 'En file',    icon: <Clock className="h-3 w-3" />, class: 'bg-sky-100 text-sky-700' },
  sent:      { label: 'Envoyé',     icon: <Send className="h-3 w-3" />, class: 'bg-emerald-100 text-emerald-700' },
  delivered: { label: 'Délivré',    icon: <CheckCircle2 className="h-3 w-3" />, class: 'bg-emerald-200 text-emerald-900' },
  failed:    { label: 'Échec',      icon: <XCircle className="h-3 w-3" />, class: 'bg-rose-100 text-rose-700' },
  cancelled: { label: 'Annulé',     icon: <XCircle className="h-3 w-3" />, class: 'bg-slate-200 text-slate-600' },
};

const CHANNEL_ICON: Record<string, React.ReactNode> = {
  sms: <Smartphone className="h-4 w-4" />,
  whatsapp: <MessageCircle className="h-4 w-4" />,
  email: <span>✉</span>,
  push: <span>📱</span>,
};

const PROVIDER_BADGE: Record<string, string> = {
  orange_ci: 'bg-orange-50 text-orange-700',
  twilio: 'bg-rose-50 text-rose-700',
  meta_whatsapp: 'bg-emerald-50 text-emerald-700',
  system: 'bg-slate-100 text-slate-500',
};

interface Props {
  /** Si fourni, charge l'historique d'un voyageur spécifique */
  publicId?: string;
  /** Filtre additionnel par canal */
  channel?: 'sms' | 'whatsapp' | 'email' | 'push';
  /** Limite d'affichage */
  pageSize?: number;
}

export function NotificationHistory({ publicId, channel, pageSize = 50 }: Props) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const url = publicId
      ? `/notifications/traveler/${publicId}/`
      : `/notifications/?page_size=${pageSize}${channel ? `&channel=${channel}` : ''}`;
    api.get(url)
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [publicId, channel]);

  const retry = async (id: number) => {
    try {
      await api.post(`/notifications/${id}/retry/`);
      toast.success('Notification relancée');
      load();
    } catch (e: any) {
      toast.error(extractApiError(e));
    }
  };

  if (loading) return <div className="card p-10 animate-pulse h-32" />;
  if (err) return <div className="card p-6 text-rose-600">{err}</div>;

  return (
    <div className="space-y-2">
      {items.length === 0 && (
        <div className="card p-10 text-center text-slate-400">
          Aucun message envoyé.
        </div>
      )}
      {items.map((n) => {
        const meta = STATUS_META[n.status] || STATUS_META.pending;
        return (
          <article key={n.uuid} className="card p-4">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <div className="h-9 w-9 rounded-lg bg-slate-100 dark:bg-slate-800 grid place-items-center text-slate-600 shrink-0">
                  {CHANNEL_ICON[n.channel] || <Send className="h-4 w-4" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500">
                    {n.template_name && (
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        {n.template_name}
                      </span>
                    )}
                    {!n.template_name && (
                      <span className="italic text-slate-500">Message libre</span>
                    )}
                    <span>·</span>
                    <span className="font-mono">{n.masked_recipient || n.recipient}</span>
                    {n.provider && (
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${PROVIDER_BADGE[n.provider] || 'bg-slate-100'}`}>
                        {n.provider}
                      </span>
                    )}
                  </div>
                  <p className="text-sm mt-1 line-clamp-3 whitespace-pre-wrap">{n.body}</p>
                  <div className="text-[10px] text-slate-400 mt-1 flex flex-wrap gap-x-3">
                    <span>📅 {formatDateTime(n.created_at)}</span>
                    {n.sent_at && <span>✓ Envoyé {formatDateTime(n.sent_at)}</span>}
                    {n.delivered_at && <span>📬 Délivré {formatDateTime(n.delivered_at)}</span>}
                    {n.failed_at && <span className="text-rose-500">⚠ Échec {formatDateTime(n.failed_at)}</span>}
                    {n.sent_by_email && <span>👤 {n.sent_by_email}</span>}
                    {n.retry_count > 0 && <span>↻ {n.retry_count} essai{n.retry_count > 1 ? 's' : ''}</span>}
                  </div>
                  {n.error_message && (
                    <div className="mt-2 text-xs text-rose-700 bg-rose-50 dark:bg-rose-950/30 rounded px-2 py-1 inline-flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" /> {n.error_message}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${meta.class}`}>
                  {meta.icon} {meta.label}
                </span>
                {n.status === 'failed' && (
                  <button
                    onClick={() => retry(n.id)}
                    className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:underline"
                    title="Relancer"
                  >
                    <RefreshCw className="h-3 w-3" /> Relancer
                  </button>
                )}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
