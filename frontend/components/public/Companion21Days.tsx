'use client';

import { useMemo, useState } from 'react';
import { AlertCircle, CheckCircle2, Circle, Clock4, ThermometerSun, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CheckEntry } from '@/lib/companion';

/**
 * Compagnon Sanitaire 21j — timeline visuelle du suivi.
 *
 * Innovation : chaque jour est cliquable. Si un check-in a été enregistré
 * ce jour-là, un modal affiche le détail (température, symptômes, notes).
 *
 * Indicateurs visuels par jour :
 *  - passé sans symptôme → vert (CheckCircle2)
 *  - passé avec symptôme → orange (AlertCircle)
 *  - aujourd'hui → orange ciOrange (Clock4)
 *  - futur → gris (Circle)
 *  - pas de check-in déclaré → cercle vide
 */
export function Companion21Days({
  surveillanceStart,
  surveillanceEnd,
  checks,
}: {
  surveillanceStart?: string | null;
  surveillanceEnd?: string | null;
  checks?: CheckEntry[];
}) {
  const [selected, setSelected] = useState<CheckEntry | null>(null);

  const days = useMemo(() => {
    if (!surveillanceStart) return [];
    const start = new Date(surveillanceStart);
    return Array.from({ length: 21 }, (_, i) => {
      const d = new Date(start);
      d.setDate(d.getDate() + i);
      return d;
    });
  }, [surveillanceStart]);

  // Indexer les checks par date "YYYY-MM-DD" pour lookup O(1).
  const checksByDate = useMemo(() => {
    const map = new Map<string, CheckEntry>();
    (checks || []).forEach((c) => {
      if (c.check_date) map.set(c.check_date.slice(0, 10), c);
    });
    return map;
  }, [checks]);

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayIndex = days.findIndex(
    (d) => d.toDateString() === today.toDateString(),
  );
  const progress = days.length ? Math.min(((todayIndex + 1) / days.length) * 100, 100) : 0;

  return (
    <>
      <article className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-widest text-ciOrange font-black">
              Compagnon sanitaire
            </div>
            <h3 className="font-display text-xl font-black text-ciDark dark:text-emerald-200 mt-1">
              Mon suivi 21 jours
            </h3>
          </div>
          <div className="text-right">
            <div className="text-2xl font-black text-ciGreen">{Math.max(todayIndex + 1, 0)}/21</div>
            <div className="text-xs text-slate-500">jours écoulés</div>
          </div>
        </div>

        {/* Barre de progression tricolore */}
        <div className="mt-4 h-3 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-ciOrange via-ciGold to-ciGreen transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Calendrier jour par jour — chaque case est un bouton cliquable */}
        <div className="mt-5 grid grid-cols-7 gap-1.5">
          {days.map((d, i) => {
            const isPast = i < todayIndex;
            const isToday = i === todayIndex;
            const iso = d.toISOString().slice(0, 10);
            const entry = checksByDate.get(iso);
            const hadIssue = entry?.has_symptoms || entry?.needs_contact;

            return (
              <button
                type="button"
                key={i}
                onClick={() => entry && setSelected(entry)}
                disabled={!entry}
                title={entry ? 'Voir le détail du check-in' : ''}
                className={cn(
                  'rounded-lg p-2 text-center text-[10px] font-bold transition relative',
                  entry && 'cursor-pointer hover:ring-2 hover:ring-ciOrange/30',
                  isPast && !hadIssue && 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40',
                  isPast && hadIssue && 'bg-amber-100 text-amber-800 ring-1 ring-amber-200',
                  isToday && 'bg-ciOrange text-white shadow-glow ring-2 ring-ciOrange/40',
                  !isPast && !isToday && 'bg-slate-50 text-slate-400 dark:bg-slate-900',
                )}
              >
                <div className="text-[9px] uppercase opacity-70">J{i}</div>
                <div className="font-display text-sm font-black mt-0.5">{d.getDate()}</div>
                <div className="text-[8px] uppercase opacity-70 mt-0.5">
                  {d.toLocaleDateString('fr-FR', { month: 'short' })}
                </div>
                <div className="mt-1 flex justify-center">
                  {hadIssue ? <AlertCircle className="h-3 w-3" />
                    : isPast ? <CheckCircle2 className="h-3 w-3" />
                    : isToday ? <Clock4 className="h-3 w-3" />
                    : <Circle className="h-3 w-3" />}
                </div>
                {/* Petit marqueur pour indiquer qu'un check-in est cliquable */}
                {entry && (
                  <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900" />
                )}
              </button>
            );
          })}
        </div>

        <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
          <Kpi label="Début" value={days[0]?.toLocaleDateString('fr-FR') || '—'} color="text-ciOrange" />
          <Kpi label="Aujourd'hui" value={today.toLocaleDateString('fr-FR')} color="text-ciDark dark:text-emerald-300" />
          <Kpi label="Fin prévue" value={days[20]?.toLocaleDateString('fr-FR') || '—'} color="text-ciGreen" />
        </div>

        <p className="mt-5 text-xs text-slate-500 leading-5">
          Cliquez sur une date verte ou orange pour voir votre check-in du jour.
          En cas de symptôme, composez le 143 (Allô Santé) ou le 185 (SAMU).
        </p>
      </article>

      {/* Modal détail du check-in */}
      {selected && (
        <CheckinDetailModal entry={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}

function Kpi({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl bg-slate-50 dark:bg-slate-900 p-3">
      <div className="uppercase tracking-wide text-slate-500">{label}</div>
      <div className={cn('mt-1 font-black', color)}>{value}</div>
    </div>
  );
}

const FEELING_LABELS: Record<string, string> = {
  ok: 'Je vais bien',
  symptom: 'Symptôme signalé',
  assistance: 'Demande d\'assistance',
};

const SYMPTOM_LABELS: Record<string, string> = {
  fever: 'Fièvre',
  intense_fatigue: 'Fatigue intense',
  severe_headache: 'Maux de tête',
  muscle_joint_pain: 'Douleurs musculaires',
  sore_throat_or_abdominal: 'Mal de gorge / abdominal',
  diarrhea_nausea_vomiting: 'Diarrhée / nausées',
  unexplained_bleeding: 'Saignements',
};

function CheckinDetailModal({ entry, onClose }: { entry: CheckEntry; onClose: () => void }) {
  const date = new Date(entry.check_date).toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card max-w-md w-full p-6 relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Fermer"
          className="absolute top-3 right-3 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Check-in du jour J{entry.day_index}
        </div>
        <h3 className="font-display text-xl font-black mt-1 capitalize">{date}</h3>

        <dl className="mt-4 space-y-3 text-sm">
          {entry.feeling && (
            <Row label="Mon état" value={FEELING_LABELS[entry.feeling] || entry.feeling} />
          )}
          {entry.temperature_celsius != null && (
            <Row
              label="Température"
              value={`${entry.temperature_celsius}°C`}
              icon={<ThermometerSun className="h-4 w-4 text-amber-600" />}
            />
          )}
          {entry.positive_symptoms && entry.positive_symptoms.length > 0 && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Symptômes signalés</dt>
              <dd className="mt-2 flex flex-wrap gap-1.5">
                {entry.positive_symptoms.map((s) => (
                  <span key={s} className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-xs font-semibold">
                    {SYMPTOM_LABELS[s] || s}
                  </span>
                ))}
              </dd>
            </div>
          )}
          {entry.notes && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Notes</dt>
              <dd className="mt-1 text-sm whitespace-pre-wrap">{entry.notes}</dd>
            </div>
          )}
          {entry.needs_contact && (
            <div className="rounded-xl bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
              Vous aviez demandé à être contacté par un agent ce jour-là.
            </div>
          )}
          {entry.alert_raised && (
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
              Une équipe sanitaire a été notifiée suite à ce signalement.
            </div>
          )}
        </dl>
      </div>
    </div>
  );
}

function Row({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-2 last:border-0">
      <dt className="text-xs uppercase tracking-wide text-slate-500 flex items-center gap-1">
        {icon}{label}
      </dt>
      <dd className="font-semibold">{value}</dd>
    </div>
  );
}
