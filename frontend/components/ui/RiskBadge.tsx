import type { RiskLevel } from '@/types/ebola';
import { cn, RISK_LABELS } from '@/lib/utils';
import { ShieldAlert, ShieldCheck, ShieldQuestion, Siren } from 'lucide-react';

const STYLES: Record<RiskLevel, string> = {
  low: 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:ring-emerald-900',
  moderate: 'bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:ring-amber-900',
  high: 'bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:ring-rose-900',
  critical: 'bg-red-900 text-white ring-red-700',
};

const ICONS: Record<RiskLevel, JSX.Element> = {
  low: <ShieldCheck className="h-3.5 w-3.5" />,
  moderate: <ShieldQuestion className="h-3.5 w-3.5" />,
  high: <ShieldAlert className="h-3.5 w-3.5" />,
  critical: <Siren className="h-3.5 w-3.5" />,
};

export function RiskBadge({ level, score, className }: { level: RiskLevel; score?: number; className?: string }) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset',
      STYLES[level], className,
    )}>
      {ICONS[level]}
      {RISK_LABELS[level] || level}
      {score !== undefined && <span className="ml-1 opacity-70">· {score}/100</span>}
    </span>
  );
}
