'use client';

/**
 * FollowupTimeline — Timeline verticale J1 → J21 (ou plus selon protocole).
 *
 * Consomme `GET /api/v1/admin/followups/{travelerId}/timeline/` qui retourne
 * un array enrichi `DailyCheck` (avec compteurs symptoms_count, sample_flag,
 * notification_flag, actions[]).
 *
 * Carte par jour repliable :
 *  - badge statut coloré
 *  - icônes d'événements (check-in, température, symptômes, prélèvement,
 *    notification, alerte)
 *  - détail : notes, decision, agent_responsible_name, actions performed
 *
 * Le bouton "Actions" du jour appelle `onOpenActions(dayId)` que le parent
 * peut intercepter (modale d'ajout d'action / lien vers symptôme rapide).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2, AlertTriangle, Activity, FlaskConical, Bell, MapPin,
  Loader2, RefreshCcw, ChevronDown, ChevronUp, Thermometer, Clock, UserCheck,
  Plus, Calendar,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

export interface TimelineDayAction {
  id: number;
  action_type: string;
  action_type_label: string;
  title: string;
  performed_at: string | null;
  performed_by_name: string;
}

export interface TimelineDay {
  id: number;
  day_index: number;
  check_date: string | null;
  status: string;
  has_symptoms: boolean;
  temperature_celsius: string | number | null;
  decision: string;
  agent_responsible: number | null;
  agent_responsible_name: string;
  location_shared: boolean;
  alert_raised: boolean;
  notes: string;
  symptoms_count: number;
  sample_requested_flag: boolean;
  notification_sent_flag: boolean;
  actions: TimelineDayAction[];
}

interface Props {
  travelerId: string;
  /** Callback déclenché par le bouton "Actions" d'une journée (parent ouvre modale ad hoc). */
  onOpenActions?: (dayId: number, day: TimelineDay) => void;
  /** Si fourni, expose la fonction refresh pour pilotage parent. */
  onLoaded?: (days: TimelineDay[]) => void;
  /** Permet de forcer un re-fetch depuis le parent. */
  refreshKey?: number;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  planned: { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', label: 'Planifié' },
  pending: { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200', label: 'En attente' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Complété' },
  missed: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'Manqué' },
  alert: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-300', label: 'Alerte' },
  visit_scheduled: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'Visite prévue' },
  sample_requested: { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200', label: 'Prélèvement demandé' },
  analysis_in_progress: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200', label: 'Analyse en cours' },
  escalated: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', label: 'Escaladé' },
  closed: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300', label: 'Clôturé' },
};

const DEFAULT_STYLE = {
  bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200', label: '',
};

function formatDate(d: string | null): string {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('fr-FR', {
      weekday: 'short', day: '2-digit', month: 'short',
    });
  } catch {
    return d;
  }
}

function formatDateTime(d: string | null): string {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleString('fr-FR', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return d;
  }
}

function FollowupDayCard({
  day,
  expanded,
  onToggle,
  onOpenActions,
}: {
  day: TimelineDay;
  expanded: boolean;
  onToggle: () => void;
  onOpenActions?: (dayId: number, day: TimelineDay) => void;
}) {
  const style = STATUS_STYLES[day.status] ?? DEFAULT_STYLE;
  const statusLabel = style.label || day.status;

  // Couleur de bordure si alerte
  const cardBorder = day.alert_raised
    ? 'border-rose-300 shadow-rose-100/40 shadow-md'
    : 'border-slate-200';

  // Température formatée
  const temp = day.temperature_celsius;
  const tempStr = temp !== null && temp !== undefined && temp !== ''
    ? `${typeof temp === 'string' ? parseFloat(temp).toFixed(1) : temp.toFixed(1)} °C`
    : null;
  const tempHigh = temp !== null && temp !== undefined && temp !== ''
    ? (typeof temp === 'string' ? parseFloat(temp) : temp) >= 38
    : false;

  return (
    <div className={`rounded-2xl border bg-white ${cardBorder} transition`}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full p-4 flex items-start gap-4 text-left hover:bg-slate-50/60 rounded-2xl"
      >
        {/* Numéro de jour */}
        <div className="shrink-0 w-14 text-center">
          <div className="font-display text-2xl font-black text-ciDark tabular-nums">
            J{day.day_index + 1}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {formatDate(day.check_date)}
          </div>
        </div>

        {/* Contenu principal */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className={`px-2 py-0.5 rounded-md text-xs font-bold border ${style.bg} ${style.text} ${style.border}`}>
              {statusLabel}
            </span>
            {day.alert_raised && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-rose-100 text-rose-700 border border-rose-200">
                <AlertTriangle className="h-3 w-3" /> Alerte
              </span>
            )}
            {day.has_symptoms && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                <Activity className="h-3 w-3" /> {day.symptoms_count > 0 ? `${day.symptoms_count} symptôme(s)` : 'Symptômes'}
              </span>
            )}
            {day.sample_requested_flag && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-sky-50 text-sky-700 border border-sky-200">
                <FlaskConical className="h-3 w-3" /> Prélèvement
              </span>
            )}
            {day.notification_sent_flag && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-violet-50 text-violet-700 border border-violet-200">
                <Bell className="h-3 w-3" /> Notification
              </span>
            )}
            {day.location_shared && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <MapPin className="h-3 w-3" /> Géoloc
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
            {day.status === 'completed' && (
              <span className="inline-flex items-center gap-1 text-emerald-700">
                <CheckCircle2 className="h-3.5 w-3.5" /> Check-in OK
              </span>
            )}
            {day.status === 'missed' && (
              <span className="inline-flex items-center gap-1 text-rose-700">
                <AlertTriangle className="h-3.5 w-3.5" /> Check-in manqué
              </span>
            )}
            {tempStr && (
              <span className={`inline-flex items-center gap-1 ${tempHigh ? 'text-rose-700 font-semibold' : ''}`}>
                <Thermometer className="h-3.5 w-3.5" /> {tempStr}
              </span>
            )}
            {day.agent_responsible_name && (
              <span className="inline-flex items-center gap-1">
                <UserCheck className="h-3.5 w-3.5" /> {day.agent_responsible_name}
              </span>
            )}
          </div>
        </div>

        {/* Toggle expand */}
        <div className="shrink-0 text-slate-400">
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
      </button>

      {/* Bloc déplié */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-100 space-y-3">
          {day.notes && (
            <div>
              <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">
                Notes
              </div>
              <p className="text-sm text-slate-700 whitespace-pre-wrap">{day.notes}</p>
            </div>
          )}
          {day.decision && (
            <div>
              <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">
                Décision
              </div>
              <p className="text-sm text-slate-700 whitespace-pre-wrap">{day.decision}</p>
            </div>
          )}

          {day.actions && day.actions.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1.5">
                Actions effectuées ({day.actions.length})
              </div>
              <ul className="space-y-1.5">
                {day.actions.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-start gap-2 text-xs bg-slate-50 rounded-lg px-2.5 py-1.5"
                  >
                    <Clock className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <div className="font-semibold text-slate-700">
                        {a.title || a.action_type_label}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {a.action_type_label}
                        {a.performed_by_name && ` · ${a.performed_by_name}`}
                        {a.performed_at && ` · ${formatDateTime(a.performed_at)}`}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            {onOpenActions && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onOpenActions(day.id, day); }}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold hover:bg-slate-50"
              >
                <Plus className="h-3.5 w-3.5" /> Actions
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function FollowupTimeline({
  travelerId,
  onOpenActions,
  onLoaded,
  refreshKey = 0,
}: Props) {
  const [days, setDays] = useState<TimelineDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const load = useCallback(() => {
    if (!travelerId) return;
    setLoading(true);
    setError(null);
    api.get(`/admin/followups/${travelerId}/timeline/`)
      .then((r) => {
        const list: TimelineDay[] = r.data?.results || r.data || [];
        setDays(list);
        onLoaded?.(list);
      })
      .catch((e) => {
        const msg = extractApiError(e);
        setError(msg);
      })
      .finally(() => setLoading(false));
    // onLoaded est intentionnellement omis pour éviter une boucle si le parent
    // ne mémoïse pas le callback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [travelerId]);

  useEffect(() => { load(); }, [load, refreshKey]);

  const toggle = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const summary = useMemo(() => {
    if (!days.length) return null;
    const completed = days.filter((d) => d.status === 'completed').length;
    const missed = days.filter((d) => d.status === 'missed').length;
    const alerts = days.filter((d) => d.alert_raised).length;
    return { completed, missed, alerts, total: days.length };
  }, [days]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-ciOrange" />
            <h2 className="font-display text-lg font-black text-ciDark">
              Timeline du suivi
            </h2>
          </div>
          {summary && (
            <div className="text-xs text-slate-500 mt-1">
              {summary.total} jour(s) · <span className="text-emerald-700 font-semibold">{summary.completed}</span> complétés
              {summary.missed > 0 && <> · <span className="text-rose-700 font-semibold">{summary.missed}</span> manqués</>}
              {summary.alerts > 0 && <> · <span className="text-rose-700 font-semibold">{summary.alerts}</span> alerte(s)</>}
            </div>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold hover:bg-slate-50 disabled:opacity-40"
        >
          <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </button>
      </header>

      {loading && days.length === 0 ? (
        <div className="py-10 grid place-items-center text-slate-400 text-sm">
          <Loader2 className="h-5 w-5 animate-spin mb-2" />
          Chargement de la timeline…
        </div>
      ) : error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <div className="font-bold mb-1">Impossible de charger la timeline</div>
          <p className="text-xs">{error}</p>
        </div>
      ) : days.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-sm">
          Aucun jour de suivi enregistré.
        </div>
      ) : (
        <div className="space-y-2.5">
          {days.map((d) => (
            <FollowupDayCard
              key={d.id}
              day={d}
              expanded={expandedIds.has(d.id)}
              onToggle={() => toggle(d.id)}
              onOpenActions={onOpenActions}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export default FollowupTimeline;
