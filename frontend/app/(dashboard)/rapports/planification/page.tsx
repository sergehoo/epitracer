'use client';

/**
 * /dashboard/rapports/planification — configurer le cron Celery Beat.
 *
 * Réservé NATIONAL_ADMIN (backend permission CanManageReportSchedule).
 * Affiche la planification active + formulaire d'édition (weekday, time,
 * timezone, includes). Les modifications sont prises en compte par Beat
 * au prochain reload (django_celery_beat DatabaseScheduler).
 */

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import {
  ArrowLeft, CalendarClock, CheckCircle2, Clock3, FileSpreadsheet,
  FileText, Info, Save, XCircle,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';


interface Schedule {
  id: number;
  uuid?: string;
  name: string;
  report_type: string;
  report_type_label: string;
  frequency: string;
  frequency_label: string;
  weekday: number;
  weekday_label: string;
  time: string;
  timezone: string;
  is_active: boolean;
  include_pdf: boolean;
  include_excel: boolean;
  created_by?: number | null;
  created_at?: string;
  updated_at?: string;
}

const WEEKDAY_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: 'Lundi' },
  { value: 2, label: 'Mardi' },
  { value: 3, label: 'Mercredi' },
  { value: 4, label: 'Jeudi' },
  { value: 5, label: 'Vendredi' },
  { value: 6, label: 'Samedi' },
  { value: 7, label: 'Dimanche' },
];

const TZ_OPTIONS = [
  'Africa/Abidjan',
  'Africa/Casablanca',
  'Europe/Paris',
  'UTC',
];


export default function SchedulePage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<number | null>(null);
  const [dirty, setDirty] = useState<Record<number, Partial<Schedule>>>({});

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<{ results?: Schedule[] } | Schedule[]>('/reports/schedule/');
      setSchedules(Array.isArray(data) ? data : (data.results ?? []));
    } catch (e) {
      setError(extractApiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const updateField = (id: number, patch: Partial<Schedule>) => {
    setDirty(prev => ({ ...prev, [id]: { ...(prev[id] ?? {}), ...patch } }));
  };

  const save = async (schedule: Schedule) => {
    const patch = dirty[schedule.id];
    if (!patch || Object.keys(patch).length === 0) {
      toast('Aucune modification à enregistrer.');
      return;
    }
    setSaving(schedule.id);
    try {
      await api.patch(`/reports/schedule/${schedule.id}/`, patch);
      toast.success('Planification mise à jour.');
      setDirty(prev => { const n = { ...prev }; delete n[schedule.id]; return n; });
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setSaving(null);
    }
  };

  const createDefault = async () => {
    try {
      await api.post('/reports/schedule/', {
        name: 'Rapport hebdomadaire INHP',
        report_type: 'weekly',
        frequency: 'weekly',
        weekday: 1,
        time: '08:00',
        timezone: 'Africa/Abidjan',
        is_active: true,
        include_pdf: true,
        include_excel: true,
      });
      toast.success('Planification par défaut créée.');
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    }
  };

  const weeklyActive = useMemo(
    () => schedules.find(s => s.report_type === 'weekly' && s.is_active),
    [schedules],
  );

  return (
    <div className="space-y-6">
      <header>
        <Link href="/rapports" className="text-xs text-slate-500 hover:text-ciOrange inline-flex items-center gap-1 mb-2">
          <ArrowLeft className="h-3 w-3" /> Retour au Centre de rapports
        </Link>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Rapports · Planification
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Configurer la planification
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Le rapport hebdomadaire est déclenché automatiquement par Celery Beat.
          Modifier le jour / l'heure / le fuseau ci-dessous — la nouvelle configuration
          est appliquée au prochain reload du scheduler (généralement moins d&apos;une minute).
        </p>
      </header>

      {/* Bandeau info schedule actif */}
      {!loading && weeklyActive && (
        <div className="card p-4 border-l-4 border-l-ciGreen bg-emerald-50/40 dark:bg-emerald-950/20">
          <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-200 font-bold">
            <CheckCircle2 className="h-4 w-4" />
            Prochain rapport : {WEEKDAY_OPTIONS.find(w => w.value === weeklyActive.weekday)?.label} à {weeklyActive.time} ({weeklyActive.timezone})
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            {weeklyActive.name} — génération de la semaine précédente (lundi 00h00 → dimanche 23h59).
          </div>
        </div>
      )}

      {!loading && schedules.length === 0 && (
        <div className="card p-6 bg-amber-50 border-amber-200 text-center">
          <XCircle className="h-8 w-8 text-amber-600 mx-auto mb-2" />
          <div className="font-bold text-amber-900 mb-2">Aucune planification configurée</div>
          <p className="text-xs text-amber-800 mb-4">
            Le Beat ne pourra pas déclencher de génération automatique tant qu'aucune
            planification active n'existe pour <code>report_type=weekly</code>.
          </p>
          <button
            onClick={createDefault}
            className="inline-flex items-center gap-1.5 rounded-xl bg-ciOrange text-white px-4 py-2 text-sm font-bold hover:bg-orange-600"
          >
            <CalendarClock className="h-4 w-4" /> Créer la planification par défaut
          </button>
        </div>
      )}

      {error && (
        <div className="card p-4 bg-rose-50 border-rose-200 text-rose-700 text-sm">
          {error}
        </div>
      )}

      {/* Liste des schedules (généralement 1 seul) */}
      {loading ? (
        <div className="card p-8 animate-pulse h-40" />
      ) : (
        <div className="space-y-4">
          {schedules.map(s => {
            const local = { ...s, ...(dirty[s.id] ?? {}) };
            const hasChanges = !!dirty[s.id];
            return (
              <article key={s.id} className="card p-6">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 mb-4">
                  <div>
                    <h3 className="font-display text-lg font-black text-ciDark dark:text-emerald-100">
                      {s.name}
                    </h3>
                    <div className="text-xs text-slate-500 mt-1">
                      Type : <span className="font-bold">{s.report_type_label}</span> ·
                      Fréquence : <span className="font-bold">{s.frequency_label}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {s.is_active ? (
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 text-[11px] font-bold">
                        <CheckCircle2 className="h-3 w-3" /> Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 text-slate-600 border border-slate-300 px-2 py-0.5 text-[11px] font-bold">
                        <XCircle className="h-3 w-3" /> Inactive
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid md:grid-cols-3 gap-4">
                  <Field label="Jour de la semaine">
                    <select
                      className="select"
                      value={local.weekday}
                      onChange={(e) => updateField(s.id, { weekday: parseInt(e.target.value, 10) })}
                    >
                      {WEEKDAY_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Heure locale">
                    <input
                      type="time"
                      className="input"
                      value={local.time}
                      onChange={(e) => updateField(s.id, { time: e.target.value })}
                    />
                  </Field>
                  <Field label="Fuseau horaire">
                    <select
                      className="select"
                      value={local.timezone}
                      onChange={(e) => updateField(s.id, { timezone: e.target.value })}
                    >
                      {TZ_OPTIONS.map(tz => (
                        <option key={tz} value={tz}>{tz}</option>
                      ))}
                    </select>
                  </Field>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-4">
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="accent-ciOrange"
                      checked={local.is_active}
                      onChange={(e) => updateField(s.id, { is_active: e.target.checked })}
                    />
                    <span className="text-sm font-semibold">Active</span>
                  </label>
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="accent-rose-600"
                      checked={local.include_pdf}
                      onChange={(e) => updateField(s.id, { include_pdf: e.target.checked })}
                    />
                    <FileText className="h-3.5 w-3.5 text-rose-600" />
                    <span className="text-sm">Inclure PDF</span>
                  </label>
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="accent-emerald-600"
                      checked={local.include_excel}
                      onChange={(e) => updateField(s.id, { include_excel: e.target.checked })}
                    />
                    <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
                    <span className="text-sm">Inclure Excel</span>
                  </label>
                </div>

                {hasChanges && (
                  <div className="mt-4 flex items-center justify-between rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
                    <span className="text-xs text-amber-900">
                      <Info className="h-3.5 w-3.5 inline mr-1" />
                      Modifications non enregistrées.
                    </span>
                    <button
                      onClick={() => save(s)}
                      disabled={saving === s.id}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-ciOrange text-white px-3 py-1.5 text-xs font-bold hover:bg-orange-600 disabled:opacity-50"
                    >
                      <Save className="h-3.5 w-3.5" /> {saving === s.id ? 'Enregistrement…' : 'Enregistrer'}
                    </button>
                  </div>
                )}

                <div className="mt-4 text-[10px] text-slate-400 flex items-center gap-2">
                  <Clock3 className="h-3 w-3" />
                  Dernière modif : {s.updated_at ? new Date(s.updated_at).toLocaleString('fr-FR') : '—'}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="card p-4 bg-sky-50 border-sky-200 text-sky-900 text-xs">
        <Info className="h-4 w-4 inline mr-1" />
        Les tâches Celery associées sont : <code>reports.dispatch_weekly_report</code>
        (lundi 08h par défaut), <code>reports.retry_failed_weekly_reports</code> (toutes
        les 15 min), <code>reports.cleanup_expired_report_files</code> (dimanche 04h).
        La modification ne change PAS le cron Beat inscrit dans <code>config/celery.py</code>
        — elle change le comportement de <code>dispatch_weekly_report</code> qui vérifie
        <code>AutomatedReportSchedule.is_active</code> avant de générer.
      </div>
    </div>
  );
}


function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">{label}</div>
      {children}
    </label>
  );
}
