'use client';

/**
 * /dashboard/alertes/[uuid] — détail d'une HealthAlert + actions.
 *
 * Affiche : titre, description, sévérité, statut, dates, target lié
 * (voyageur si trouvé), et actions admin : assigner, changer le statut,
 * résoudre, ajouter une note.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import {
  ArrowLeft, CheckCircle2, Clock, ExternalLink, FileText,
  ShieldCheck, Siren, XCircle,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface AlertDetail {
  uuid: string;
  code: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  disease_code?: string | null;
  entry_point_name?: string | null;
  zone?: string | null;
  target_ct?: string | null;
  target_id?: string | null;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  created_at: string;
  updated_at: string;
}

const SEV_BADGE: Record<string, string> = {
  CRITICAL: 'bg-rose-100 text-rose-700 border-rose-200',
  critical: 'bg-rose-100 text-rose-700 border-rose-200',
  HIGH: 'bg-orange-100 text-orange-700 border-orange-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  LOW: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  low: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  INFO: 'bg-slate-100 text-slate-700 border-slate-200',
  info: 'bg-slate-100 text-slate-700 border-slate-200',
};

const STATUS_LABEL: Record<string, string> = {
  OPEN: 'Nouvelle', open: 'Nouvelle',
  ACK: 'Reconnue', ack: 'Reconnue',
  INVESTIGATING: 'En cours', investigating: 'En cours',
  RESOLVED: 'Résolue', resolved: 'Résolue',
  DISMISSED: 'Fausse alerte', dismissed: 'Fausse alerte',
};

export default function AlertDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params?.uuid || '';
  const [alert, setAlert] = useState<AlertDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  const load = useCallback(async () => {
    if (!uuid) return;
    setLoading(true);
    try {
      const { data } = await api.get<AlertDetail>(`/surveillance/alerts/${uuid}/`);
      setAlert(data);
    } catch (e) {
      setError(extractApiError(e));
    } finally {
      setLoading(false);
    }
  }, [uuid]);

  useEffect(() => { load(); }, [load]);

  const updateStatus = async (newStatus: string) => {
    if (!alert) return;
    setActing(true);
    try {
      await api.patch(`/surveillance/alerts/${alert.uuid}/`, { status: newStatus });
      toast.success(`Alerte → ${STATUS_LABEL[newStatus] || newStatus}`);
      await load();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setActing(false);
    }
  };

  if (loading) return <div className="card p-10 animate-pulse h-64" />;
  if (error) return <div className="card p-6 text-rose-600">{error}</div>;
  if (!alert) return <div className="card p-6 text-slate-500">Alerte introuvable.</div>;

  const sev = (alert.severity || '').toUpperCase();
  const isTravelerTarget = alert.target_ct === 'travelers.traveler' && alert.target_id;

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/alertes" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange">
        <ArrowLeft className="h-3 w-3" /> Retour aux alertes
      </Link>

      {/* En-tête */}
      <header className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="text-xs uppercase tracking-widest text-rose-600 font-bold">
              Alerte sanitaire · {alert.code}
            </span>
            <h1 className="font-display text-2xl md:text-3xl font-black mt-1">{alert.title}</h1>
            <div className="text-xs text-slate-500 mt-2">
              Créée le {formatDateTime(alert.created_at)}
              {alert.updated_at !== alert.created_at && (
                <> · MAJ {formatDateTime(alert.updated_at)}</>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <span className={`px-3 py-1 rounded-md border text-xs font-bold ${SEV_BADGE[sev] || SEV_BADGE.INFO}`}>
              {sev}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">
              {STATUS_LABEL[alert.status] || alert.status}
            </span>
          </div>
        </div>
      </header>

      {/* Description */}
      {alert.description && (
        <section className="card p-5">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-2 flex items-center gap-1">
            <FileText className="h-3 w-3" /> Description
          </div>
          <div className="text-sm whitespace-pre-wrap leading-6">{alert.description}</div>
        </section>
      )}

      {/* Contexte */}
      <section className="card p-5">
        <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3">
          Contexte
        </div>
        <dl className="grid sm:grid-cols-2 gap-3 text-sm">
          <Row label="Maladie" value={alert.disease_code || '—'} />
          <Row label="Point d'entrée" value={alert.entry_point_name || '—'} />
          <Row label="Zone" value={alert.zone || '—'} />
          <Row label="Code interne" value={alert.code} mono />
          {alert.acknowledged_by && (
            <Row label="Reconnue par" value={alert.acknowledged_by} />
          )}
          {alert.acknowledged_at && (
            <Row label="Reconnue le" value={formatDateTime(alert.acknowledged_at)} />
          )}
        </dl>

        {isTravelerTarget && (
          <Link
            href={`/voyageurs/${alert.target_id}/itineraire`}
            className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-ciOrange hover:underline"
          >
            Voir le dossier du voyageur lié <ExternalLink className="h-3 w-3" />
          </Link>
        )}
      </section>

      {/* Actions */}
      <section className="card p-5">
        <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3">
          Actions
        </div>
        <div className="flex flex-wrap gap-2">
          {alert.status === 'OPEN' && (
            <ActionBtn label="Prendre en charge" icon={<Clock className="h-3.5 w-3.5" />}
              onClick={() => updateStatus('ACK')} disabled={acting} />
          )}
          {alert.status !== 'INVESTIGATING' && alert.status !== 'RESOLVED' && alert.status !== 'DISMISSED' && (
            <ActionBtn label="Investiguer" icon={<Siren className="h-3.5 w-3.5" />}
              onClick={() => updateStatus('INVESTIGATING')} disabled={acting} />
          )}
          {alert.status !== 'RESOLVED' && (
            <ActionBtn label="Résoudre" icon={<CheckCircle2 className="h-3.5 w-3.5" />}
              tone="emerald" onClick={() => updateStatus('RESOLVED')} disabled={acting} />
          )}
          {alert.status !== 'DISMISSED' && (
            <ActionBtn label="Fausse alerte" icon={<XCircle className="h-3.5 w-3.5" />}
              tone="slate" onClick={() => updateStatus('DISMISSED')} disabled={acting} />
          )}
        </div>
      </section>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={`text-sm ${mono ? 'font-mono' : 'font-medium'} mt-0.5`}>{value}</dd>
    </div>
  );
}

function ActionBtn({
  label, icon, onClick, disabled, tone = 'orange',
}: {
  label: string; icon: React.ReactNode; onClick: () => void; disabled?: boolean;
  tone?: 'orange' | 'emerald' | 'slate';
}) {
  const styles: Record<string, string> = {
    orange: 'bg-ciOrange text-white hover:bg-orange-600',
    emerald: 'bg-emerald-600 text-white hover:bg-emerald-700',
    slate: 'bg-slate-200 text-slate-700 hover:bg-slate-300',
  };
  return (
    <button
      type="button" onClick={onClick} disabled={disabled}
      className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold transition disabled:opacity-50 ${styles[tone]}`}
    >
      {icon} {label}
    </button>
  );
}
