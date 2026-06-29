'use client';

/**
 * CaseClassificationBadge — Badge réutilisable pour la classification clinique d'un cas.
 *
 * Codes attendus (alignés sur backend `CaseClassificationCode`) :
 *   not_suspect, under_surveillance, suspect, probable, confirmed,
 *   excluded, recovered, closed
 *
 * Usage :
 *   <CaseClassificationBadge classification="suspect" label="Cas suspect" />
 */

import { AlertTriangle, ShieldCheck, Search, Activity, FileCheck2, FileX } from 'lucide-react';

export type ClassificationCode =
  | 'not_suspect'
  | 'under_surveillance'
  | 'suspect'
  | 'probable'
  | 'confirmed'
  | 'excluded'
  | 'recovered'
  | 'closed'
  | string;

interface Props {
  classification: ClassificationCode;
  label?: string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
  className?: string;
}

const TONE_MAP: Record<string, {
  bg: string; text: string; border: string;
  Icon: React.ComponentType<{ className?: string }>;
  fallbackLabel: string;
}> = {
  not_suspect: {
    bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200',
    Icon: ShieldCheck, fallbackLabel: 'Non suspect',
  },
  under_surveillance: {
    bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200',
    Icon: Search, fallbackLabel: 'Sous surveillance',
  },
  suspect: {
    bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200',
    Icon: AlertTriangle, fallbackLabel: 'Suspect',
  },
  probable: {
    bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200',
    Icon: AlertTriangle, fallbackLabel: 'Probable',
  },
  confirmed: {
    bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200',
    Icon: Activity, fallbackLabel: 'Confirmé',
  },
  excluded: {
    bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200',
    Icon: FileX, fallbackLabel: 'Exclu',
  },
  recovered: {
    bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200',
    Icon: ShieldCheck, fallbackLabel: 'Rétabli',
  },
  closed: {
    bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200',
    Icon: FileCheck2, fallbackLabel: 'Clôturé',
  },
};

const DEFAULT_TONE = {
  bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200',
  Icon: Search, fallbackLabel: '',
};

export function CaseClassificationBadge({
  classification,
  label,
  size = 'sm',
  showIcon = true,
  className = '',
}: Props) {
  const tone = TONE_MAP[classification] ?? DEFAULT_TONE;
  const finalLabel = label || tone.fallbackLabel || classification;
  const sizeClass = size === 'md'
    ? 'px-2.5 py-1 text-sm'
    : 'px-2 py-1 text-xs';
  const { Icon } = tone;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md font-bold border ${tone.bg} ${tone.text} ${tone.border} ${sizeClass} ${className}`}
      title={finalLabel}
    >
      {showIcon && <Icon className={size === 'md' ? 'h-3.5 w-3.5' : 'h-3 w-3'} />}
      {finalLabel}
    </span>
  );
}

export default CaseClassificationBadge;
