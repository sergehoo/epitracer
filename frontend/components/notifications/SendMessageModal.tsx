'use client';

/**
 * SendMessageModal — Modal réutilisable d'envoi de SMS / WhatsApp.
 *
 * Utilisable depuis :
 *   - /voyageurs/[public_id]
 *   - /suivi-voyageurs
 *   - /alertes/[uuid]
 *
 * Workflow :
 *   1. Choisir canal (SMS / WhatsApp)
 *   2. Choisir type : message libre OU template prédéfini
 *   3. Si template : sélectionner + variables auto-remplies (first_name, etc.)
 *   4. Aperçu en temps réel
 *   5. Détection automatique du provider (preview-routing) — affiché à l'agent
 *   6. Confirmer l'envoi
 *
 * Règle métier :
 *   - Si le numéro est ivoirien (+225) → Orange CI (forcé côté backend)
 *   - Sinon → Twilio
 *   - L'agent NE PEUT PAS contourner cette règle.
 */

import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import {
  Send, X, MessageCircle, Smartphone, FileText, Pencil,
  Loader2, Check, AlertCircle, Wifi, WifiOff, ChevronRight,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

interface NotificationTemplate {
  id: number;
  code: string;
  name: string;
  description: string;
  subject: string;
  body: string;
  channels: string[];
  variables_schema?: Record<string, string>;
  is_active: boolean;
}

interface RoutingPreview {
  normalized: string;
  country_code: string;
  provider: string;
  is_ivoirian: boolean;
}

export interface SendMessageTarget {
  /** ID Traveler (peut être null si on envoie à un n° libre) */
  traveler_id?: number | null;
  /** public_id du voyageur (affichage uniquement) */
  traveler_public_id?: string;
  /** Nom complet pour affichage modal */
  traveler_name?: string;
  /** N° de téléphone pré-rempli (whatsapp_phone ou phone_mobile) */
  phone?: string;
  /** Données pour le contexte template ({first_name}) */
  first_name?: string;
}

interface Props {
  target: SendMessageTarget;
  open: boolean;
  onClose: () => void;
  onSent?: (notificationId: number) => void;
}

const CHANNELS = [
  { value: 'sms', label: 'SMS', icon: <Smartphone className="h-4 w-4" /> },
  { value: 'whatsapp', label: 'WhatsApp', icon: <MessageCircle className="h-4 w-4" /> },
];

const PROVIDER_LABEL: Record<string, { label: string; color: string }> = {
  orange_ci: { label: 'Orange Côte d\'Ivoire', color: 'bg-orange-100 text-orange-800 border-orange-300' },
  twilio: { label: 'Twilio (international)', color: 'bg-rose-100 text-rose-800 border-rose-300' },
  meta_whatsapp: { label: 'Meta WhatsApp', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  system: { label: 'Stub (mode dev)', color: 'bg-slate-100 text-slate-700 border-slate-300' },
};

export function SendMessageModal({ target, open, onClose, onSent }: Props) {
  const [channel, setChannel] = useState<'sms' | 'whatsapp'>('sms');
  const [mode, setMode] = useState<'free' | 'template'>('template');
  const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
  const [selectedTpl, setSelectedTpl] = useState<NotificationTemplate | null>(null);
  const [body, setBody] = useState('');
  const [phone, setPhone] = useState(target.phone || '');
  const [routing, setRouting] = useState<RoutingPreview | null>(null);
  const [routingError, setRoutingError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  // Charge les templates au mount
  useEffect(() => {
    if (!open) return;
    api.get('/notifications/templates/?is_active=true&page_size=50')
      .then((r) => setTemplates(r.data.results || r.data))
      .catch(() => setTemplates([]));
  }, [open]);

  // Reset state à chaque ouverture
  useEffect(() => {
    if (open) {
      setPhone(target.phone || '');
      setBody('');
      setSelectedTpl(null);
      setMode('template');
      setChannel('sms');
      setRouting(null);
      setRoutingError(null);
    }
  }, [open, target.phone]);

  // Détection provider à chaque changement de téléphone ou canal
  useEffect(() => {
    if (!phone || !open) return;
    const t = setTimeout(() => {
      api.post('/notifications/preview-routing/', { phone, channel })
        .then((r) => { setRouting(r.data); setRoutingError(null); })
        .catch((e: any) => {
          setRouting(null);
          setRoutingError(extractApiError(e));
        });
    }, 300);
    return () => clearTimeout(t);
  }, [phone, channel, open]);

  // Templates filtrés selon le canal
  const channelTemplates = useMemo(
    () => templates.filter((t) => (t.channels || []).includes(channel)),
    [templates, channel],
  );

  // Rendu de l'aperçu (interpole les variables si template)
  const previewBody = useMemo(() => {
    if (mode === 'free') return body;
    if (!selectedTpl) return '';
    // Variables disponibles depuis target
    const ctx: Record<string, string> = {
      first_name: target.first_name || target.traveler_name?.split(' ')[0] || 'Voyageur',
      checkin_link: 'https://destinationci.com/voyageur/suivi',
      location_link: 'https://destinationci.com/voyageur/suivi#geo',
      message: body || '[votre message ici]',
    };
    return selectedTpl.body.replace(/\{(\w+)\}/g, (_, k: string) => ctx[k] ?? `{${k}}`);
  }, [mode, body, selectedTpl, target]);

  // Char count
  const charCount = previewBody.length;
  const smsSegments = Math.max(1, Math.ceil(charCount / 160));

  const submit = async () => {
    if (!phone.trim()) {
      toast.error('Numéro de téléphone requis.');
      return;
    }
    if (mode === 'free' && !body.trim()) {
      toast.error('Message vide.');
      return;
    }
    if (mode === 'template' && !selectedTpl) {
      toast.error('Sélectionnez un modèle ou choisissez « Message libre ».');
      return;
    }

    setSending(true);
    try {
      const payload: any = {
        channel,
        recipient: phone.trim(),
      };
      if (target.traveler_id) payload.traveler = target.traveler_id;

      if (mode === 'template' && selectedTpl) {
        payload.template_code = selectedTpl.code;
        payload.context = {
          first_name: target.first_name || target.traveler_name?.split(' ')[0] || '',
          checkin_link: 'https://destinationci.com/voyageur/suivi',
          location_link: 'https://destinationci.com/voyageur/suivi#geo',
          message: body || '',
        };
      } else {
        payload.body = body;
      }

      const r = await api.post('/notifications/send/', payload);
      const notifId = r.data?.id;
      toast.success(`Message en file d'envoi (#${notifId})`);
      onSent?.(notifId);
      onClose();
    } catch (e: any) {
      toast.error(extractApiError(e));
    } finally {
      setSending(false);
    }
  };

  if (!open) return null;

  const providerInfo = routing ? PROVIDER_LABEL[routing.provider] : null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl mt-8 mb-8">
        {/* En-tête */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h2 className="font-display text-lg font-bold flex items-center gap-2">
              <Send className="h-5 w-5 text-emerald-600" /> Envoyer un message
            </h2>
            {target.traveler_name && (
              <p className="text-xs text-slate-500 mt-0.5">
                Destinataire : <strong>{target.traveler_name}</strong>
                {target.traveler_public_id && (
                  <span className="font-mono ml-2 text-slate-400">{target.traveler_public_id}</span>
                )}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-xl"
            aria-label="Fermer"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Canal */}
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
              Canal
            </div>
            <div className="flex gap-2">
              {CHANNELS.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setChannel(c.value as any)}
                  className={`flex-1 inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold border transition ${
                    channel === c.value
                      ? 'bg-emerald-600 text-white border-emerald-600'
                      : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  {c.icon} {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Téléphone */}
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
              Numéro destinataire
            </div>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+225XXXXXXXXXX"
              className="input-base font-mono"
            />
            {/* Affichage provider auto-détecté */}
            {routing && providerInfo && (
              <div className={`mt-2 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold border ${providerInfo.color}`}>
                <Wifi className="h-3 w-3" />
                <span>Provider auto : <strong>{providerInfo.label}</strong></span>
                <span className="text-[10px] font-mono opacity-70">{routing.normalized}</span>
              </div>
            )}
            {routingError && (
              <div className="mt-2 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                <WifiOff className="h-3 w-3" /> {routingError}
              </div>
            )}
          </div>

          {/* Type message */}
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
              Type
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMode('template')}
                className={`flex-1 inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold border transition ${
                  mode === 'template'
                    ? 'bg-ciOrange text-white border-ciOrange'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                <FileText className="h-4 w-4" /> Modèle prédéfini
              </button>
              <button
                type="button"
                onClick={() => { setMode('free'); setSelectedTpl(null); }}
                className={`flex-1 inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold border transition ${
                  mode === 'free'
                    ? 'bg-ciOrange text-white border-ciOrange'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                <Pencil className="h-4 w-4" /> Message libre
              </button>
            </div>
          </div>

          {/* Sélection template OU édition libre */}
          {mode === 'template' ? (
            <div>
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
                Modèle ({channelTemplates.length} disponible{channelTemplates.length > 1 ? 's' : ''})
              </div>
              {channelTemplates.length === 0 ? (
                <div className="text-sm text-slate-400 py-4 text-center border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                  Aucun modèle disponible pour ce canal. Passez en « Message libre ».
                </div>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {channelTemplates.map((t) => (
                    <button
                      key={t.code}
                      type="button"
                      onClick={() => setSelectedTpl(t)}
                      className={`w-full text-left rounded-lg px-3 py-2 text-sm border transition ${
                        selectedTpl?.code === t.code
                          ? 'border-ciOrange bg-orange-50 dark:bg-orange-950/30'
                          : 'border-slate-200 dark:border-slate-700 hover:border-ciOrange/40'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-medium">{t.name}</div>
                        <ChevronRight className="h-3 w-3 text-slate-400" />
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">{t.code}</div>
                    </button>
                  ))}
                </div>
              )}

              {/* Champ "message" libre quand template MANUAL_ADMIN_NOTICE est sélectionné */}
              {selectedTpl?.code === 'MANUAL_ADMIN_NOTICE' && (
                <div className="mt-3">
                  <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
                    Votre message (sera inséré dans le template)
                  </div>
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={3}
                    placeholder="Texte que vous souhaitez transmettre..."
                    className="input-base resize-none"
                  />
                </div>
              )}
            </div>
          ) : (
            <div>
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
                Votre message
              </div>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={5}
                placeholder="Composez votre message..."
                className="input-base resize-none"
                maxLength={1530}
              />
            </div>
          )}

          {/* Aperçu */}
          {previewBody && (
            <div>
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1 flex items-center justify-between">
                <span>Aperçu du message</span>
                <span className="font-mono text-[10px] text-slate-400">
                  {charCount} caractères · {smsSegments} SMS
                </span>
              </div>
              <div className="rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 p-4 text-sm whitespace-pre-wrap leading-relaxed">
                {previewBody}
              </div>
              {smsSegments > 4 && (
                <div className="mt-2 inline-flex items-center gap-1 text-xs text-amber-700">
                  <AlertCircle className="h-3 w-3" /> Message long ({smsSegments} segments SMS) — coût accru.
                </div>
              )}
            </div>
          )}

          {/* Footer actions */}
          <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button onClick={onClose} className="btn-secondary">Annuler</button>
            <button
              onClick={submit}
              disabled={sending || !previewBody || !phone}
              className="btn-primary inline-flex items-center gap-2"
            >
              {sending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Envoi...</>
              ) : (
                <><Send className="h-4 w-4" /> Confirmer l'envoi</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
