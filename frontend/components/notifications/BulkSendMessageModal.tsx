'use client';

/**
 * Modal d'envoi groupé de messages aux voyageurs sélectionnés.
 *
 * - Mode template (interpolation par destinataire) ou message libre
 * - Choix du canal SMS / WhatsApp
 * - Envoi séquentiel avec barre de progression
 * - Récap final (succès / échecs par ligne)
 */

import { Fragment, useEffect, useMemo, useState } from 'react';
import { BellRing, Bot, CheckCircle2, Mail, MessageCircle, Send, Smartphone, Users, X, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

export interface BulkTarget {
  traveler_id?: number | null;
  traveler_public_id?: string;
  full_name: string;
  /** Téléphone — utilisé pour SMS/WhatsApp */
  phone: string;
  /** Email — utilisé pour le canal Email */
  email?: string;
  first_name?: string;
}

type ChannelKey = 'sms' | 'whatsapp' | 'email' | 'push' | 'telegram';

interface NotificationTemplate {
  id: number;
  code: string;
  name: string;
  channels: string[];
  body_sms?: string;
  body_whatsapp?: string;
}

interface Props {
  open: boolean;
  targets: BulkTarget[];
  onClose: () => void;
  onSent?: (sent: number, failed: number) => void;
}

type SendStatus = 'pending' | 'sending' | 'ok' | 'failed';

interface Row {
  target: BulkTarget;
  status: SendStatus;
  error?: string;
  notificationId?: number;
}

export function BulkSendMessageModal({ open, targets, onClose, onSent }: Props) {
  const [channel, setChannel] = useState<ChannelKey>('sms');
  const [mode, setMode] = useState<'free' | 'template'>('template');
  const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
  const [selectedTplCode, setSelectedTplCode] = useState<string>('');
  const [body, setBody] = useState('');
  const [subject, setSubject] = useState('');
  const [rows, setRows] = useState<Row[]>([]);
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const isEmail = channel === 'email';
  const isPush = channel === 'push';
  const isTelegram = channel === 'telegram';
  // Push & Telegram : deux canaux "auto-résolus via traveler_id"
  const isTravelerBound = isPush || isTelegram;

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
      setBody('');
      setSubject('');
      setSelectedTplCode('');
      setMode('template');
      setChannel('sms');
      setSending(false);
      setDone(false);
      setRows(targets.map((t) => ({ target: t, status: 'pending' })));
    }
  }, [open, targets]);

  const channelTemplates = useMemo(
    () => templates.filter((t) => (t.channels || []).includes(channel)),
    [templates, channel],
  );

  // En mode email on compte les emails dispos ; sinon les téléphones.
  const validRecipients = isTravelerBound
    // Push in-app / Telegram : on considère "valide" tout traveler_id présent
    // — le backend fera le tri final selon les MobileDevice ou TelegramSubscription
    // effectivement enregistrés.
    ? targets.filter((t) => !!t.traveler_id).length
    : isEmail
    ? targets.filter((t) => !!t.email).length
    : targets.filter((t) => !!t.phone).length;
  const noRecipient = targets.length - validRecipients;
  // Conserve les anciens noms pour ne pas casser le JSX existant
  const validPhones = validRecipients;
  const noPhones = noRecipient;

  // ── Split lié/non-lié Telegram — récupéré au changement de canal ──
  const [tgStatus, setTgStatus] = useState<{
    linked: number; unlinked: number; total: number; linked_ids: number[];
    bot_configured: boolean;
  } | null>(null);
  const [tgInviteUnlinked, setTgInviteUnlinked] = useState(true);

  useEffect(() => {
    if (!isTelegram || !open) { setTgStatus(null); return; }
    const ids = targets.map((t) => t.traveler_id).filter(Boolean) as number[];
    if (ids.length === 0) { setTgStatus(null); return; }
    api.post('/notifications/telegram/link-status/', { traveler_ids: ids })
      .then((r) => setTgStatus(r.data))
      .catch(() => setTgStatus(null));
  }, [isTelegram, open, targets]);

  const send = async () => {
    if (mode === 'free' && !body.trim()) {
      toast.error('Message vide.');
      return;
    }
    if (mode === 'template' && !selectedTplCode) {
      toast.error('Sélectionnez un modèle ou choisissez « Message libre ».');
      return;
    }

    setSending(true);
    setDone(false);

    const updated = [...rows];
    let okCount = 0;
    let failCount = 0;

    // Pour Telegram : identifier les non-liés → ils recevront une invitation SMS
    // au lieu du vrai message Telegram (le vrai message ne leur arriverait pas
    // de toute façon car le bot ne peut pas initier une conv sans opt-in).
    const linkedTgSet = new Set(tgStatus?.linked_ids || []);
    const shouldInviteUnlinked = isTelegram && tgInviteUnlinked && tgStatus && tgStatus.unlinked > 0;

    for (let i = 0; i < updated.length; i++) {
      const r = updated[i];

      // Si Telegram + non-lié + fallback activé → SMS d'invitation à la place
      const isTgUnlinked =
        isTelegram && r.target.traveler_id && !linkedTgSet.has(r.target.traveler_id);
      const useInviteFallback = isTgUnlinked && shouldInviteUnlinked;

      // Canal effectif pour ce destinataire
      const effChannel = useInviteFallback ? 'sms' : channel;

      // Choisir le destinataire selon le canal effectif
      // Push / Telegram : le backend résout via traveler_id — pas besoin
      // d'un vrai recipient (on envoie le public_id comme placeholder).
      const recipient = useInviteFallback
        ? (r.target.phone || '').trim()
        : isTravelerBound
        ? (r.target.traveler_public_id || String(r.target.traveler_id ?? ''))
        : isEmail
        ? (r.target.email || '').trim()
        : (r.target.phone || '').trim();

      if (!recipient) {
        r.status = 'failed';
        r.error = useInviteFallback
          ? 'Non-lié Telegram : pas de téléphone pour SMS d\'invitation'
          : isTravelerBound
          ? 'Voyageur sans ID enregistré'
          : isEmail
          ? 'Pas d\'email'
          : 'Pas de téléphone';
        failCount++;
        setRows([...updated]);
        continue;
      }
      // Push / Telegram exigent aussi qu'un traveler_id (int) soit présent
      if (isTravelerBound && !r.target.traveler_id) {
        r.status = 'failed';
        r.error = isTelegram
          ? 'Telegram requiert un voyageur enregistré'
          : 'Push requiert un voyageur enregistré';
        failCount++;
        setRows([...updated]);
        continue;
      }
      // Skip silencieux si Telegram + non-lié + fallback désactivé
      if (isTgUnlinked && !shouldInviteUnlinked) {
        r.status = 'failed';
        r.error = 'Voyageur non-lié Telegram (fallback SMS désactivé)';
        failCount++;
        setRows([...updated]);
        continue;
      }

      r.status = 'sending';
      setRows([...updated]);

      try {
        const payload: any = {
          channel: effChannel,
          recipient,
        };
        if (r.target.traveler_id) payload.traveler = r.target.traveler_id;
        if (effChannel === 'email') payload.subject = subject.trim();

        if (useInviteFallback) {
          // Forcé sur le template TELEGRAM_INVITE_SMS
          payload.template_code = 'TELEGRAM_INVITE_SMS';
          payload.context = {
            first_name: r.target.first_name || r.target.full_name.split(' ')[0] || '',
          };
        } else if (mode === 'template' && selectedTplCode) {
          payload.template_code = selectedTplCode;
          payload.context = {
            first_name: r.target.first_name || r.target.full_name.split(' ')[0] || '',
            checkin_link: 'https://destinationci.com/voyageur/suivi',
            location_link: 'https://destinationci.com/voyageur/suivi#geo',
            message: body || '',
          };
        } else {
          payload.body = body;
        }

        const resp = await api.post('/notifications/send/', payload);
        r.status = 'ok';
        r.notificationId = resp.data?.id;
        // Note visuelle pour l'agent : distinguer envoi vrai vs invitation
        if (useInviteFallback) {
          r.error = '📧 SMS d\'invitation Telegram envoyé';
        }
        okCount++;
      } catch (e: any) {
        r.status = 'failed';
        r.error = extractApiError(e);
        failCount++;
      }
      setRows([...updated]);
      // Petit délai pour ménager le router SMS et laisser respirer l'UI
      await new Promise((res) => setTimeout(res, 250));
    }

    setSending(false);
    setDone(true);
    onSent?.(okCount, failCount);
    if (failCount === 0) {
      toast.success(`${okCount} message(s) envoyé(s)`);
    } else {
      toast(`${okCount} envoyés · ${failCount} échec(s)`, { icon: '⚠️' });
    }
  };

  if (!open) return null;

  const progress = rows.length === 0
    ? 0
    : Math.round((rows.filter((r) => r.status === 'ok' || r.status === 'failed').length / rows.length) * 100);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-3xl mt-8 mb-8">
        {/* En-tête */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-ciOrange" />
              <h2 className="font-display text-lg font-black">Envoi groupé</h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {targets.length} voyageur(s) sélectionné(s)
              {noPhones > 0 && (
                <span className="text-amber-600 dark:text-amber-400">
                  {' '}· {noPhones} sans téléphone (ignorés)
                </span>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={sending}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Canal */}
          <div>
            <label className="block text-xs uppercase tracking-widest text-slate-500 font-bold mb-2">
              Canal
            </label>
            <div className="inline-flex rounded-xl border border-slate-200 dark:border-slate-700 p-1">
              {[
                { value: 'sms', label: 'SMS', icon: <Smartphone className="h-4 w-4" /> },
                { value: 'whatsapp', label: 'WhatsApp', icon: <MessageCircle className="h-4 w-4" /> },
                { value: 'email', label: 'Email', icon: <Mail className="h-4 w-4" /> },
                { value: 'push', label: 'App mobile', icon: <BellRing className="h-4 w-4" /> },
                { value: 'telegram', label: 'Telegram', icon: <Bot className="h-4 w-4" /> },
              ].map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => !sending && setChannel(c.value as ChannelKey)}
                  className={`px-4 py-1.5 text-sm rounded-lg font-semibold transition inline-flex items-center gap-1.5 ${
                    channel === c.value
                      ? 'bg-emerald-600 text-white'
                      : 'text-slate-600 dark:text-slate-300'
                  }`}
                  disabled={sending}
                >
                  {c.icon}
                  {c.label}
                </button>
              ))}
            </div>
            {isEmail && (
              <div className="mt-2 text-xs text-slate-500">
                <Mail className="h-3 w-3 inline mr-1" />
                Les voyageurs sans email seront ignorés ({noPhones > 0 ? `${noPhones} sans email` : 'tous OK'}).
                Expéditeur PUBLIC <strong>Destination CI</strong> (imposé).
              </div>
            )}

            {/* Panneau Telegram : split lié/non-lié + fallback SMS invitation */}
            {isTelegram && (
              <div className="mt-3 rounded-xl border border-sky-200 bg-sky-50 dark:bg-sky-950/30 dark:border-sky-900 p-3 text-xs space-y-2">
                <div className="flex items-center gap-2 font-semibold text-sky-800 dark:text-sky-200">
                  <Bot className="h-3.5 w-3.5" />
                  Canal additionnel Telegram (opt-in, gratuit)
                </div>
                {!tgStatus ? (
                  <div className="text-slate-500">Analyse des voyageurs sélectionnés…</div>
                ) : !tgStatus.bot_configured ? (
                  <div className="text-rose-700">
                    ⚠ Bot Telegram non configuré côté backend. Envoi impossible.
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="rounded-lg bg-white dark:bg-slate-900 p-2 text-center">
                        <div className="text-lg font-black text-emerald-600">{tgStatus.linked}</div>
                        <div className="text-[10px] uppercase text-slate-500">Liés au bot</div>
                      </div>
                      <div className="rounded-lg bg-white dark:bg-slate-900 p-2 text-center">
                        <div className="text-lg font-black text-amber-600">{tgStatus.unlinked}</div>
                        <div className="text-[10px] uppercase text-slate-500">Non-liés</div>
                      </div>
                      <div className="rounded-lg bg-white dark:bg-slate-900 p-2 text-center">
                        <div className="text-lg font-black text-slate-700 dark:text-slate-200">{tgStatus.total}</div>
                        <div className="text-[10px] uppercase text-slate-500">Total sélection</div>
                      </div>
                    </div>
                    <div className="text-slate-600 dark:text-slate-400">
                      Le message Telegram sera livré aux <strong>{tgStatus.linked}</strong> voyageurs liés.
                      Les <strong>{tgStatus.unlinked}</strong> autres ne recevront rien via Telegram.
                    </div>
                    {tgStatus.unlinked > 0 && (
                      <label className="flex items-start gap-2 cursor-pointer pt-1 border-t border-sky-200 dark:border-sky-900">
                        <input
                          type="checkbox"
                          checked={tgInviteUnlinked}
                          onChange={(e) => setTgInviteUnlinked(e.target.checked)}
                          className="mt-0.5 accent-sky-600"
                        />
                        <span>
                          <strong>Inviter les {tgStatus.unlinked} non-liés par SMS</strong> (envoi
                          d'un SMS d'invitation avec leur lien personnel — 1 clic pour rejoindre le bot).
                          Utilise le template <code className="font-mono">TELEGRAM_INVITE_SMS</code>.
                        </span>
                      </label>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Objet du mail — visible uniquement si canal=email */}
          {isEmail && (
            <div>
              <label className="block text-xs uppercase tracking-widest text-slate-500 font-bold mb-2">
                Objet du mail
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Ex. Information importante — INHP Côte d'Ivoire"
                maxLength={200}
                disabled={sending}
                className="input-base"
              />
              <div className="mt-1 text-[10px] text-slate-400">
                Vide → l'objet du modèle sélectionné sera utilisé.
              </div>
            </div>
          )}

          {/* Mode template/libre */}
          <div>
            <label className="block text-xs uppercase tracking-widest text-slate-500 font-bold mb-2">
              Contenu
            </label>
            <div className="inline-flex rounded-xl border border-slate-200 dark:border-slate-700 p-1 mb-3">
              {[
                { value: 'template', label: 'Modèle' },
                { value: 'free', label: 'Message libre' },
              ].map((m) => (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => !sending && setMode(m.value as 'template' | 'free')}
                  className={`px-3 py-1.5 text-sm rounded-lg font-semibold transition ${
                    mode === m.value
                      ? 'bg-ciOrange text-white'
                      : 'text-slate-600 dark:text-slate-300'
                  }`}
                  disabled={sending}
                >
                  {m.label}
                </button>
              ))}
            </div>

            {mode === 'template' ? (
              <select
                className="select w-full"
                value={selectedTplCode}
                onChange={(e) => setSelectedTplCode(e.target.value)}
                disabled={sending}
              >
                <option value="">— Sélectionner un modèle —</option>
                {channelTemplates.map((t) => (
                  <option key={t.id} value={t.code}>{t.name}</option>
                ))}
              </select>
            ) : (
              <textarea
                className="textarea w-full"
                rows={4}
                placeholder="Tapez votre message (variables disponibles : {first_name}, {checkin_link})"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                disabled={sending}
              />
            )}
          </div>

          {/* Progression / résultats */}
          {(sending || done) && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs uppercase tracking-widest text-slate-500 font-bold">
                  {done ? 'Résultats' : 'Progression'}
                </span>
                <span className="text-xs font-bold text-slate-600 dark:text-slate-300">
                  {progress}%
                </span>
              </div>
              <div className="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden mb-3">
                <div
                  className="h-full bg-emerald-500 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="max-h-48 overflow-y-auto border border-slate-100 dark:border-slate-800 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
                {rows.map((r, idx) => (
                  <div key={idx} className="flex items-center gap-2 px-3 py-2 text-xs">
                    {r.status === 'pending' && (
                      <span className="h-3 w-3 rounded-full bg-slate-300" />
                    )}
                    {r.status === 'sending' && (
                      <span className="h-3 w-3 rounded-full bg-amber-400 animate-pulse" />
                    )}
                    {r.status === 'ok' && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    )}
                    {r.status === 'failed' && (
                      <XCircle className="h-3.5 w-3.5 text-rose-600" />
                    )}
                    <span className="font-semibold flex-1 truncate">
                      {r.target.full_name}
                    </span>
                    <span className="text-slate-500 truncate">
                      {r.target.phone || '—'}
                    </span>
                    {r.error && (
                      <span className="text-rose-600 truncate max-w-[180px]">{r.error}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-slate-800">
          <button
            type="button"
            onClick={onClose}
            disabled={sending}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900 disabled:opacity-50"
          >
            {done ? 'Fermer' : 'Annuler'}
          </button>
          {!done && (
            <button
              type="button"
              onClick={send}
              disabled={sending || validPhones === 0}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-4 w-4" />
              {sending ? 'Envoi en cours...' : `Envoyer à ${validPhones} voyageur(s)`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
