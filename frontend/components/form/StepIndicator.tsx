'use client';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export const STEPS = [
  'Voyage',
  'Identité',
  'Historique',
  'Confinement',
  'Évaluation risque',
  'État de santé',
  'Déclaration',
] as const;

export function StepIndicator({ current, onJump }: { current: number; onJump?: (i: number) => void }) {
  return (
    <ol className="grid grid-cols-7 gap-1 sm:gap-2 mb-8">
      {STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={label} className="flex flex-col items-center text-center">
            <button
              type="button"
              disabled={!onJump || i > current}
              onClick={() => onJump?.(i)}
              className={cn(
                'h-10 w-10 sm:h-11 sm:w-11 rounded-full grid place-items-center text-sm font-bold border-2 transition',
                active && 'bg-emerald-600 border-emerald-600 text-white shadow-glow',
                done && 'bg-emerald-50 border-emerald-300 text-emerald-700 dark:bg-emerald-950/40',
                !done && !active && 'bg-slate-100 border-slate-200 text-slate-500 dark:bg-slate-900 dark:border-slate-800',
              )}
            >
              {done ? <Check className="h-4 w-4" /> : i + 1}
            </button>
            <span className={cn(
              'mt-2 text-[10px] sm:text-xs font-medium leading-tight max-w-[8ch]',
              active ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-500',
            )}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
