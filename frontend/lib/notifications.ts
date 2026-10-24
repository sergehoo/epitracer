/**
 * Types et libellés partagés du module Notifications (historique, détails,
 * indicateurs, disponibilité des fournisseurs).
 */

export interface NotificationItem {
  id: number;
  uuid: string;
  channel: string;
  template_code?: string | null;
  template_name?: string | null;
  traveler?: number | null;
  traveler_public_id?: string | null;
  traveler_name?: string | null;
  recipient: string;
  normalized_phone: string;
  masked_recipient: string;
  subject: string;
  body: string;
  message_type: string;
  status: string;
  provider: string;
  provider_message_id: string;
  /** Libellé lisible (jamais la réponse brute du fournisseur). */
  error_message: string;
  error_label?: string;
  error_code?: string;
  /** Réponse brute du fournisseur — servie aux administrateurs nationaux uniquement. */
  technical_error?: string | null;
  retry_count: number;
  max_retries?: number;
  sent_by_email?: string | null;
  queued_at?: string | null;
  sent_at?: string | null;
  delivered_at?: string | null;
  failed_at?: string | null;
  created_at: string;
  sms_segments?: number | null;
  metadata?: Record<string, unknown>;
}

export interface NotificationStats {
  total: number;
  sent: number;
  delivered: number;
  failed: number;
  pending: number;
  on_hold: number;
  cancelled: number;
  duplicates_avoided: number;
  sms: {
    messages: number;
    segments: number;
    by_provider: { provider: string; messages: number; segments: number }[];
  };
}

export interface ProviderStatus {
  provider: string;
  provider_label: string;
  state: 'available' | 'quota_exhausted' | 'unavailable' | 'budget_exceeded';
  state_label: string;
  is_suspended: boolean;
  reason_label: string;
  suspended_at: string | null;
  last_failure_at: string | null;
  blocked_attempts: number;
  held_count: number;
  resumed_at: string | null;
  resumed_by_email: string | null;
  technical_detail?: string | null;
}

export const NOTIF_STATUS: Record<string, { label: string; className: string }> = {
  draft: { label: 'Brouillon', className: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' },
  pending: { label: 'En attente', className: 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300' },
  queued: { label: 'En file', className: 'bg-sky-100 text-sky-800 dark:bg-sky-950/50 dark:text-sky-300' },
  on_hold: { label: 'Attente fournisseur', className: 'bg-orange-100 text-orange-800 dark:bg-orange-950/50 dark:text-orange-300' },
  sent: { label: 'Envoyé', className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300' },
  delivered: { label: 'Délivré', className: 'bg-emerald-200 text-emerald-900 dark:bg-emerald-900/60 dark:text-emerald-200' },
  read: { label: 'Lu', className: 'bg-emerald-200 text-emerald-900 dark:bg-emerald-900/60 dark:text-emerald-200' },
  failed: { label: 'Échec', className: 'bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-300' },
  cancelled: { label: 'Annulé', className: 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
};

export const NOTIF_CHANNEL: Record<string, string> = {
  sms: 'SMS',
  whatsapp: 'WhatsApp',
  email: 'Email',
  push: 'Push',
  telegram: 'Telegram',
  internal: 'Interne',
};

export const NOTIF_PROVIDER: Record<string, string> = {
  orange_ci: 'Orange CI',
  twilio: 'Twilio',
  meta_whatsapp: 'Meta WhatsApp',
  smtp: 'Email (SMTP)',
  fcm: 'Push (FCM)',
  telegram_bot: 'Telegram',
  system: 'Système',
};

export const NOTIF_TYPE: Record<string, string> = {
  automatic_reminder: 'Rappel automatique',
  manual_message: 'Message manuel',
  symptom_alert: 'Alerte symptômes',
  assistance: 'Assistance',
  followup_reminder: 'Rappel de suivi',
  followup_completed: 'Fin de suivi',
  admin_notice: 'Avis administrateur',
  location_request: 'Demande de position',
  ebola_prevention: 'Prévention Ebola',
  otp: 'Code de connexion (OTP)',
  other: 'Autre',
};
