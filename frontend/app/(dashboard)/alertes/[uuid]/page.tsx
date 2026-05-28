'use client';

/**
 * /dashboard/alertes/[uuid] — détail enrichi d'une HealthAlert.
 *
 * Affiche :
 *   - Titre, description, sévérité, statut avec timeline visuelle
 *   - Voyageur cible (avec lien vers fiche)
 *   - Contexte épidémiologique (maladie, point d'entrée, zone)
 *   - Historique des doublons (metadata.repeat_reasons)
 *   - Actions admin (acquitter, investiguer, résoudre, fausse alerte)
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import {
  ArrowLeft, CheckCircle2, Clock, ExternalLink, FileText,
  ShieldAlert, Siren, XCircle, User, MapPin, Calendar,
  RefreshCw, AlertTriangle, History, Bell, Send,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { SendMessageModal, SendMessageTarget } from '@/components/notifications/SendMessageModal';

interface AlertDetail {
  id: number;
  uuid: string;
  code: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  disease?: number | null;
  disease_code?: string | null;
  entry_point?: number | null;
  entry_point_name?: string | null;
  zone?: number | null;
  target_ct?: string | null;
  target_id?: string | null;
  triggered_by?: number | null;
  acknowledged_by?: number | null;
  acknowledged_at?: string | null;
  created_at: string;
  updated_at: string;
  metadata?: {
    alert_type?: string;
    duplicate_count?: number;
    last_repeat_at?: string;
    repeat_reasons?: { at: string; reasons: string[]; from_alert_id?: number }[];
    merged_from?: number[];
  };
}

interface TravelerInfo {
  public_id: string;
  full_name?: string;
  last_name: string;
  first_name: string;
  phone_mobile?: string;
  email?: string;
  arrival_date?: string | null;
  entry_point?: number | null;
  current_health_status?: string;
}

interface ZoneInfo {
  code: string;
  name: string;
  level: string;
}

const SEV_BADGE: Record<string, string> = {
  critical: 'bg-rose-100 text-rose-800 border-rose-300',
  high:     'bg-orange-100 text-orange-800 border-orange-300',
  medium:   'bg-amber-100 text-amber-800 border-amber-300',
  low:      'bg-emerald-100 text-emerald-800 border-emerald-300',
  info:     'bg-sky-100 text-sky-800 border-sky-300',
};

// Valeurs canoniques minuscules (AlertStatus.choices côté backend).
const STATUS_LABEL: Record<string, string> = {
  open: 'Nouvelle', ack: 'Reconnue', investigating: 'En cours',
  resolved: 'Résolue', dismissed: 'Fausse alerte',
};

const TIMELINE_STEPS = [
  { value: 'open', label: 'Reçue', icon: <Bell className="h-4 w-4" /> },
  { value: 'ack', label: 'Reconnue', icon: <Clock className="h-4 w-4" /> },
  { value: 'investigating', label: 'Investigation', icon: <Siren className="h-4 w-4" /> },
  { value: 'resolved', label: 'Résolue', icon: <CheckCircle2 className="h-4 w-4" /> },
];

function statusIndex(s: string): number {
  const sl = (s || '').toLowerCase();
  const ix = TIMELINE_STEPS.findIndex((t) => t.value === sl);
  if (ix >= 0) return ix;
  if (sl === 'dismissed') return -2; // hors flux normal
  return 0;
}

export default function AlertDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params?.uuid || '';
  const [alert, setAlert] = useState<AlertDetail | null>(null);
  const [traveler, setTraveler] = useState<TravelerInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msgTarget, setMsgTarget] = useState<SendMessageTarget | null>(null);

  const load = useCallback(async () => {
    if (!uuid) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<AlertDetail>(`/surveillance/alerts/${uuid}/`);
      setAlert(data);

      // Charger le voyageur cible si présent
      if (data.target_ct?.includes('traveler') && data.target_id) {
        // target_id est le PK numérique, on essaie l'endpoint correspondant
        try {
          const t = await api.get(`/travelers/?id=${data.target_id}&page_size=1`);
          const list = t.data.results || t.data;
          if (list?.[0]) setTraveler(list[0]);
        } catch {}
      }
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

  const sev = (alert.severity || 'info').toLowerCase();
  const statusLower = (alert.status || '').toLowerCase();
  const isOpen = ['open', 'ack', 'investigating'].includes(statusLower);
  const currentStep = statusIndex(alert.status);
  const duplicate = alert.metadata?.duplicate_count || 0;
  const repeats = alert.metadata?.repeat_reasons || [];

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Retour */}
      <Link href="/alertes" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange">
        <ArrowLeft className="h-3 w-3" /> Retour aux alertes
      </Link>

      {/* En-tête */}
      <header className={`card p-6 ${
        sev === 'critical' ? 'border-rose-300 bg-rose-50/30 dark:bg-rose-950/20' :
        sev === 'high' ? 'border-orange-300 bg-orange-50/30 dark:bg-orange-950/20' : ''
      }`}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-4 min-w-0 flex-1">
            <div className={`h-14 w-14 rounded-2xl grid place-items-center shrink-0 border-2 ${SEV_BADGE[sev]}`}>
              {sev === 'critical' || sev === 'high' ? (
                <ShieldAlert className="h-7 w-7" />
              ) : (
                <Siren className="h-7 w-7" />
              )}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] uppercase tracking-widest text-rose-600 font-bold">
                  Alerte sanitaire
                </span>
                <span className="text-[10px] font-mono text-slate-400">{alert.code}</span>
                {duplicate > 0 && (
                  <span className="inline-flex items-center gap-1 bg-amber-100 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded text-[10px] font-bold">
                    <RefreshCw className="h-3 w-3" /> {duplicate} déclenchement{duplicate > 1 ? 's' : ''} répété{duplicate > 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <h1 className="font-display text-xl md:text-2xl font-black mt-1">{alert.title}</h1>
              <div className="text-xs text-slate-500 mt-2 flex flex-wrap gap-x-3 gap-y-1">
                <span><Calendar className="inline h-3 w-3 mr-1" />Créée {formatDateTime(alert.created_at)}</span>
                {alert.updated_at !== alert.created_at && (
                  <span>· MAJ {formatDateTime(alert.updated_at)}</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <span className={`px-3 py-1 rounded-lg border text-xs font-bold uppercase ${SEV_BADGE[sev]}`}>
              {sev}
            </span>
            <span className="text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 font-semibold">
              {STATUS_LABEL[statusLower] || alert.status}
            </span>
          </div>
        </div>

        {/* Timeline visuelle (cycle de vie) */}
        {currentStep >= -1 && (
          <div className="mt-6 flex items-center gap-1 overflow-x-auto">
            {TIMELINE_STEPS.map((step, ix) => {
              const reached = ix <= currentStep;
              const active = ix === currentStep;
              return (
                <div key={step.value} className="flex items-center gap-1 shrink-0">
                  <div
                    className={`h-9 w-9 rounded-full grid place-items-center text-xs font-bold transition ${
                      reached
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                    } ${active ? 'ring-2 ring-emerald-300 ring-offset-2' : ''}`}
                    title={step.label}
                  >
                    {step.icon}
                  </div>
                  <span className={`text-[10px] font-semibold hidden sm:inline ${reached ? 'text-emerald-700' : 'text-slate-400'}`}>
                    {step.label}
                  </span>
                  {ix < TIMELINE_STEPS.length - 1 && (
                    <div className={`h-0.5 w-6 sm:w-8 ${ix < currentStep ? 'bg-emerald-400' : 'bg-slate-200 dark:bg-slate-800'}`} />
                  )}
                </div>
              );
            })}
            {alert.status.toUpperCase() === 'DISMISSED' && (
              <div className="ml-3 flex items-center gap-1 text-slate-400">
                <XCircle className="h-4 w-4" />
                <span className="text-[10px] font-bold uppercase">Fausse alerte</span>
              </div>
            )}
          </div>
        )}
      </header>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Colonne principale (2/3) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Description */}
          {alert.description && (
            <section className="card p-5">
              <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-2 flex items-center gap-1">
                <FileText className="h-3 w-3" /> Motif déclencheur
              </div>
              <div className="text-sm whitespace-pre-wrap leading-6">{alert.description}</div>
            </section>
          )}

          {/* Voyageur cible */}
          {traveler ? (
            <section className="card p-5">
              <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3 flex items-center gap-1">
                <User className="h-3 w-3" /> Voyageur concerné
              </div>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <div className="font-display text-lg font-bold">
                    {traveler.last_name?.toUpperCase()} {traveler.first_name}
                  </div>
                  <div className="text-xs text-slate-500 font-mono mt-0.5">{traveler.public_id}</div>
                  <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
                    {traveler.phone_mobile && (
                      <div><b>📞 Téléphone :</b> {traveler.phone_mobile}</div>
                    )}
                    {traveler.email && (
                      <div><b>✉ Email :</b> {traveler.email}</div>
                    )}
                    {traveler.arrival_date && (
                      <div><b>✈ Arrivée :</b> {new Date(traveler.arrival_date).toLocaleDateString('fr-FR')}</div>
                    )}
                    {traveler.current_health_status && (
                      <div><b>État :</b> <span className="capitalize">{traveler.current_health_status}</span></div>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <Link
                    href={`/surveillance/${traveler.public_id}`}
                    className="inline-flex items-center gap-1 bg-emerald-600 text-white rounded-lg px-3 py-2 text-xs font-semibold hover:bg-emerald-700"
                  >
                    Fiche complète <ExternalLink className="h-3 w-3" />
                  </Link>
                  <button
                    type="button"
                    onClick={() => setMsgTarget({
                      traveler_public_id: traveler.public_id,
                      traveler_name: `${traveler.last_name} ${traveler.first_name}`,
                      phone: traveler.phone_mobile,
                      first_name: traveler.first_name,
                    })}
                    className="inline-flex items-center gap-1 bg-ciOrange text-white rounded-lg px-3 py-2 text-xs font-semibold hover:bg-orange-600"
                  >
                    <Send className="h-3 w-3" /> Envoyer un message
                  </button>
                </div>
              </div>
            </section>
          ) : alert.target_id ? (
            <section className="card p-5 border-amber-200 bg-amber-50/30">
              <div className="text-xs text-amber-700 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Voyageur cible référencé (PK #{alert.target_id}) mais introuvable —
                il a peut-être été anonymisé par la purge RGPD.
              </div>
            </section>
          ) : null}

          {/* Historique des doublons */}
          {repeats.length > 0 && (
            <section className="card p-5">
              <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3 flex items-center gap-1">
                <History className="h-3 w-3" /> Historique des déclenchements répétés
              </div>
              <p className="text-xs text-slate-500 mb-3">
                Cette alerte a été agrégée à {repeats.length} déclenchement{repeats.length > 1 ? 's' : ''} ultérieur{repeats.length > 1 ? 's' : ''}
                (fenêtre anti-spam 4h, même voyageur, même sévérité).
              </p>
              <ol className="space-y-2 border-l-2 border-slate-200 dark:border-slate-800 ml-2">
                {repeats.slice().reverse().map((r, i) => (
                  <li key={i} className="pl-4 relative">
                    <span className="absolute -left-[5px] top-1.5 h-2 w-2 rounded-full bg-amber-500" />
                    <div className="text-xs font-mono text-slate-500">
                      {formatDateTime(r.at)}
                    </div>
                    <div className="text-sm">
                      {r.reasons?.filter(Boolean).join(' · ') || '—'}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>

        {/* Colonne latérale (1/3) */}
        <div className="space-y-4">
          {/* Contexte */}
          <section className="card p-5">
            <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3">
              Contexte
            </div>
            <dl className="space-y-3 text-sm">
              <Row label="Maladie" value={alert.disease_code || '—'} />
              <Row label="Point d'entrée" value={alert.entry_point_name || '—'} />
              <Row label="Zone sanitaire" value={alert.zone ? `Zone #${alert.zone}` : '—'} />
              <Row label="Type" value={alert.metadata?.alert_type || '—'} />
              {alert.acknowledged_at && (
                <Row label="Acquittée le" value={formatDateTime(alert.acknowledged_at)} />
              )}
            </dl>
          </section>

          {/* Actions admin */}
          {isOpen && (
            <section className="card p-5">
              <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3">
                Actions
              </div>
              <div className="space-y-2">
                {statusLower === 'open' && (
                  <ActionBtn
                    label="Prendre en charge"
                    icon={<Clock className="h-3.5 w-3.5" />}
                    tone="amber"
                    onClick={() => updateStatus('ack')}
                    disabled={acting}
                  />
                )}
                {!['investigating', 'resolved', 'dismissed'].includes(statusLower) && (
                  <ActionBtn
                    label="Lancer investigation"
                    icon={<Siren className="h-3.5 w-3.5" />}
                    tone="sky"
                    onClick={() => updateStatus('investigating')}
                    disabled={acting}
                  />
                )}
                {statusLower !== 'resolved' && (
                  <ActionBtn
                    label="Marquer résolue"
                    icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    tone="emerald"
                    onClick={() => updateStatus('resolved')}
                    disabled={acting}
                  />
                )}
                {statusLower !== 'dismissed' && (
                  <ActionBtn
                    label="Fausse alerte"
                    icon={<XCircle className="h-3.5 w-3.5" />}
                    tone="slate"
                    onClick={() => updateStatus('dismissed')}
                    disabled={acting}
                  />
                )}
              </div>
            </section>
          )}

          {/* Statut clos */}
          {!isOpen && (
            <section className="card p-5 text-center">
              <div className={`mx-auto h-12 w-12 rounded-full grid place-items-center mb-2 ${
                statusLower === 'resolved' ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-500'
              }`}>
                {statusLower === 'resolved' ? <CheckCircle2 className="h-6 w-6" /> : <XCircle className="h-6 w-6" />}
              </div>
              <div className="font-bold text-sm">{STATUS_LABEL[statusLower] || alert.status}</div>
              {alert.acknowledged_at && (
                <div className="text-[10px] text-slate-500 mt-1">{formatDateTime(alert.acknowledged_at)}</div>
              )}
              <button
                onClick={() => updateStatus('open')}
                disabled={acting}
                className="mt-3 text-xs text-slate-500 hover:text-rose-600 hover:underline"
              >
                Réouvrir l'alerte
              </button>
            </section>
          )}
        </div>
      </div>

      {/* Modal envoi message */}
      {msgTarget && (
        <SendMessageModal
          open={!!msgTarget}
          target={msgTarget}
          onClose={() => setMsgTarget(null)}
        />
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold">{label}</dt>
      <dd className="text-sm font-medium mt-0.5 break-words">{value}</dd>
    </div>
  );
}

function ActionBtn({
  label, icon, onClick, disabled, tone = 'orange',
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  tone?: 'orange' | 'emerald' | 'slate' | 'sky' | 'amber';
}) {
  const styles: Record<string, string> = {
    orange: 'bg-ciOrange text-white hover:bg-orange-600',
    emerald: 'bg-emerald-600 text-white hover:bg-emerald-700',
    slate: 'bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-200',
    sky: 'bg-sky-600 text-white hover:bg-sky-700',
    amber: 'bg-amber-500 text-white hover:bg-amber-600',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold transition disabled:opacity-50 ${styles[tone]}`}
    >
      {icon} {label}
    </button>
  );
}
