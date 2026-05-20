import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(d?: string | Date | null) {
  if (!d) return '—';
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric',
    }).format(new Date(d));
  } catch {
    return String(d);
  }
}

export function formatDateTime(d?: string | Date | null) {
  if (!d) return '—';
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }).format(new Date(d));
  } catch {
    return String(d);
  }
}

export const RISK_LABELS: Record<string, string> = {
  low: 'Faible',
  moderate: 'Modéré',
  high: 'Élevé',
  critical: 'Critique',
};

export const STATUS_LABELS: Record<string, string> = {
  cleared: 'Autorisé',
  monitoring: 'Surveillance',
  quarantine: 'Quarantaine',
  suspect: 'Suspect',
  confirmed: 'Confirmé',
  recovered: 'Rétabli',
  deceased: 'Décédé',
  new: 'Nouvelle',
  surveillance: 'Surveillance',
  closed: 'Clôturée',
  active: 'Actif',
  expired: 'Expiré',
  revoked: 'Révoqué',
};
