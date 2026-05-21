'use client';

import { useMemo } from 'react';
import { CheckCircle2, Circle, Clock4 } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Compagnon Sanitaire 21j — timeline visuelle du suivi
 * Innovation : affichage jour par jour avec progression dynamique.
 */
export function Companion21Days({
  surveillanceStart,
  surveillanceEnd,
}: {
  surveillanceStart?: string | null;
  surveillanceEnd?: string | null;
}) {
  const days = useMemo(() => {
    if (!surveillanceStart) return [];
    const start = new Date(surveillanceStart);
    return Array.from({ length: 21 }, (_, i) => {
      const d = new Date(start);
      d.setDate(d.getDate() + i);
      return d;
    });
  }, [surveillanceStart]);

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayIndex = days.findIndex(
    (d) => d.toDateString() === today.toDateString(),
  );
  const progress = days.length ? Math.min(((todayIndex + 1) / days.length) * 100, 100) : 0;

  return (
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

      {/* Calendrier jour par jour */}
      <div className="mt-5 grid grid-cols-7 gap-1.5">
        {days.map((d, i) => {
          const isPast = i < todayIndex;
          const isToday = i === todayIndex;
          return (
            <div
              key={i}
              className={cn(
                'rounded-lg p-2 text-center text-[10px] font-bold transition',
                isPast && 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40',
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
                {isPast ? <CheckCircle2 className="h-3 w-3" />
                  : isToday ? <Clock4 className="h-3 w-3" />
                  : <Circle className="h-3 w-3" />}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
        <Kpi label="Début" value={days[0]?.toLocaleDateString('fr-FR') || '—'} color="text-ciOrange" />
        <Kpi label="Aujourd'hui" value={today.toLocaleDateString('fr-FR')} color="text-ciDark dark:text-emerald-300" />
        <Kpi label="Fin prévue" value={days[20]?.toLocaleDateString('fr-FR') || '—'} color="text-ciGreen" />
      </div>

      <p className="mt-5 text-xs text-slate-500 leading-5">
        Pendant ces 21 jours, surveillez votre température chaque jour et signalez tout
        symptôme via le SAMU (185) ou Allô Santé (143).
      </p>
    </article>
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
