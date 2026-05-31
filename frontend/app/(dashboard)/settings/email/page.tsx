'use client';

/**
 * /dashboard/settings/email — Réglages email Super Admin
 *
 * Sections :
 *   1. Profils d'expéditeur (lecture seule — édition via Django admin)
 *   2. Test SMTP par profil (envoi live d'un email de validation)
 *   3. Liste + édition des templates email
 *   4. Éditeur HTML inline avec aperçu iframe
 */

import { FormEvent, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Mail, Shield, Users, AtSign, Send, RefreshCcw, AlertTriangle,
  CheckCircle2, Edit3, Save, X, Eye, ArrowLeft, Settings, Info,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

interface SenderProfile {
  id: number;
  code: 'public' | 'internal';
  name: string;
  from_address: string;
  from_name: string;
  reply_to: string;
  usage_scope: string;
  is_active: boolean;
  formatted_from: string;
}

interface EmailTemplate {
  id: number;
  code: string;
  name: string;
  email_type: string;
  subject: string;
  body_html: string;
  body_text: string;
  sender_profile?: number | null;
  sender_profile_code?: string | null;
  variables_schema: Record<string, string>;
  is_active: boolean;
}

export default function EmailSettingsPage() {
  const [me, setMe] = useState<any>(null);
  const [profiles, setProfiles] = useState<SenderProfile[]>([]);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<EmailTemplate | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [m, sp, tpl] = await Promise.all([
        api.get('/auth/me/'),
        api.get('/notifications/email-senders/?page_size=10'),
        api.get('/notifications/email-templates/?page_size=200'),
      ]);
      setMe(m.data);
      setProfiles(sp.data.results || sp.data);
      setTemplates(tpl.data.results || tpl.data);
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Détection rôle Super Admin (NATIONAL_ADMIN)
  const isSuperAdmin = (me?.roles || []).some(
    (r: any) => r.code === 'NATIONAL_ADMIN' || r.code === 'MINISTRY',
  );

  return (
    <div className="space-y-6 max-w-6xl">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/parametres"
            className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange mb-2"
          >
            <ArrowLeft className="h-3 w-3" /> Retour aux paramètres
          </Link>
          <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Super Admin · Configuration email
          </span>
          <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
            Réglages email
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
            Configuration des deux expéditeurs et édition des templates.
            Les profils SMTP eux-mêmes (hôte, mot de passe) sont gérés via
            les variables d'environnement.
          </p>
        </div>
        <button
          onClick={loadAll}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </button>
      </header>

      {!isSuperAdmin && !loading && (
        <div className="card p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <p>
            Cette page est réservée au <strong>Super Administrateur National</strong>.
            Vous pouvez la consulter mais certaines actions (test SMTP, édition de
            template) peuvent être refusées par le serveur.
          </p>
        </div>
      )}

      {/* ============ Profils d'expéditeur ============ */}
      <section className="card p-5">
        <header className="flex items-center gap-2 mb-3 text-emerald-700 dark:text-emerald-300">
          <Mail className="h-5 w-5" />
          <h2 className="font-display font-bold text-ciDark dark:text-emerald-100">
            Profils d'expéditeur
          </h2>
        </header>
        <div className="grid md:grid-cols-2 gap-4">
          {profiles.map((p) => (
            <article
              key={p.id}
              className={`rounded-2xl border p-4 ${
                p.code === 'public'
                  ? 'bg-gradient-to-br from-orange-50/40 to-emerald-50/30 border-orange-200/60'
                  : 'bg-gradient-to-br from-indigo-50/40 to-blue-50/30 border-indigo-200/60'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className={`h-10 w-10 rounded-xl grid place-items-center ${
                  p.code === 'public'
                    ? 'bg-ciOrange/10 text-ciOrange'
                    : 'bg-indigo-100 text-indigo-700'
                }`}>
                  {p.code === 'public' ? <Users className="h-5 w-5" /> : <Shield className="h-5 w-5" />}
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  p.is_active
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-rose-100 text-rose-700'
                }`}>
                  {p.is_active ? 'Actif' : 'Inactif'}
                </span>
              </div>
              <h3 className="font-display font-black text-ciDark mt-3">
                {p.code === 'public' ? 'PUBLIC — Voyageurs' : 'INTERNAL — Administration'}
              </h3>
              <p className="text-xs text-slate-500 mt-1">{p.name}</p>
              <dl className="mt-3 space-y-1.5 text-xs">
                <div>
                  <dt className="inline text-slate-500 mr-1">From :</dt>
                  <dd className="inline font-mono font-semibold">{p.formatted_from}</dd>
                </div>
                <div>
                  <dt className="inline text-slate-500 mr-1">Reply-To :</dt>
                  <dd className="inline font-mono">{p.reply_to || '—'}</dd>
                </div>
                <div>
                  <dt className="inline text-slate-500 mr-1">Usage :</dt>
                  <dd className="inline">{p.usage_scope}</dd>
                </div>
              </dl>
              <SmtpTestForm profileCode={p.code} disabled={!isSuperAdmin} />
            </article>
          ))}
        </div>
        <p className="text-[11px] text-slate-400 mt-3 italic">
          Pour modifier l'adresse ou le mot de passe SMTP, éditer le <code>.env</code> du
          serveur puis redémarrer les containers. Le routage <em>type → profil</em> est
          figé dans le code (cf. <code>email_models.py</code>).
        </p>
      </section>

      {/* ============ Templates ============ */}
      <section className="card p-5">
        <header className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
            <Settings className="h-5 w-5" />
            <h2 className="font-display font-bold text-ciDark dark:text-emerald-100">
              Templates email ({templates.length})
            </h2>
          </div>
        </header>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
              <tr className="text-left text-xs uppercase text-slate-500">
                <th className="px-3 py-2">Code</th>
                <th className="px-3 py-2">Nom</th>
                <th className="px-3 py-2">Type / Expéditeur</th>
                <th className="px-3 py-2">Sujet</th>
                <th className="px-3 py-2 text-center">Actif</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && (
                <tr><td colSpan={6} className="p-8 text-center text-xs text-slate-400">Chargement…</td></tr>
              )}
              {!loading && templates.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-xs text-slate-400">
                    Aucun template. Lance <code>python manage.py migrate notifications</code>
                    pour seeder les templates par défaut.
                  </td>
                </tr>
              )}
              {templates.map((t) => {
                const isInternal = t.sender_profile_code === 'internal';
                return (
                  <tr key={t.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="px-3 py-2 align-top">
                      <code className="text-xs font-mono">{t.code}</code>
                    </td>
                    <td className="px-3 py-2 align-top text-xs font-semibold">{t.name}</td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex items-center gap-1.5 text-xs">
                        {isInternal
                          ? <Shield className="h-3.5 w-3.5 text-indigo-600" />
                          : <Users className="h-3.5 w-3.5 text-ciOrange" />}
                        {t.email_type}
                      </div>
                    </td>
                    <td className="px-3 py-2 align-top text-xs text-slate-600 max-w-xs truncate"
                        title={t.subject}>
                      {t.subject}
                    </td>
                    <td className="px-3 py-2 align-top text-center">
                      <span className={`inline-block w-2 h-2 rounded-full ${
                        t.is_active ? 'bg-emerald-500' : 'bg-slate-300'
                      }`} />
                    </td>
                    <td className="px-3 py-2 align-top text-right">
                      <button
                        onClick={() => setEditing(t)}
                        className="inline-flex items-center gap-1 rounded-md bg-ciOrange/10 hover:bg-ciOrange/20 text-ciOrange px-2 py-1 text-[11px] font-bold"
                      >
                        <Edit3 className="h-3 w-3" />
                        Éditer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <div className="card p-4 bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 flex items-start gap-2">
        <Info className="h-4 w-4 mt-0.5 shrink-0" />
        <p>
          Les modifications du sujet et du corps des templates s'appliquent à TOUS les
          envois futurs sans redémarrage. Les variables disponibles sont indiquées
          dans <code>variables_schema</code> et substituent <code>{'{var}'}</code> automatiquement.
        </p>
      </div>

      {editing && (
        <TemplateEditorModal
          template={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); loadAll(); }}
        />
      )}
    </div>
  );
}

/* ============================================================ */
/*                   FORM TEST SMTP                              */
/* ============================================================ */

function SmtpTestForm({ profileCode, disabled }: { profileCode: 'public' | 'internal'; disabled?: boolean }) {
  const [recipient, setRecipient] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    setSending(true);
    setResult(null);
    try {
      const r = await api.post('/notifications/email-test/', {
        profile: profileCode,
        recipient: recipient.trim(),
      });
      const ok = r.data?.ok;
      setResult({
        ok: !!ok,
        message: ok
          ? `Envoyé via ${r.data.from} (host ${r.data.host}:${r.data.port}).`
          : `Erreur : ${r.data.error || 'inconnue'}`,
      });
      if (ok) {
        toast.success(`Test ${profileCode.toUpperCase()} envoyé`);
      } else {
        toast.error(`Test ${profileCode.toUpperCase()} échoué`);
      }
    } catch (err) {
      setResult({ ok: false, message: extractApiError(err) });
      toast.error(extractApiError(err));
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={send} className="mt-4 space-y-2">
      <label className="block text-[11px] uppercase tracking-wide text-slate-500 font-bold">
        Test SMTP — destinataire
      </label>
      <div className="flex gap-2">
        <input
          type="email"
          required
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          placeholder="ton.email@example.com"
          disabled={disabled}
          className="flex-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-xs disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={sending || !recipient || disabled}
          className="inline-flex items-center gap-1 rounded-lg bg-ciDark text-white px-3 py-1.5 text-xs font-bold hover:bg-emerald-900 disabled:opacity-50"
        >
          <Send className="h-3 w-3" />
          {sending ? '…' : 'Envoyer test'}
        </button>
      </div>
      {result && (
        <div
          className={`flex items-start gap-1.5 text-[11px] p-2 rounded-md ${
            result.ok
              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300'
              : 'bg-rose-50 text-rose-700 dark:bg-rose-900/20 dark:text-rose-300'
          }`}
        >
          {result.ok ? <CheckCircle2 className="h-3 w-3 mt-0.5 shrink-0" />
                     : <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />}
          <span>{result.message}</span>
        </div>
      )}
    </form>
  );
}

/* ============================================================ */
/*                  MODAL ÉDITION TEMPLATE                       */
/* ============================================================ */

function TemplateEditorModal({
  template, onClose, onSaved,
}: {
  template: EmailTemplate;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [subject, setSubject] = useState(template.subject);
  const [bodyHtml, setBodyHtml] = useState(template.body_html);
  const [bodyText, setBodyText] = useState(template.body_text);
  const [isActive, setIsActive] = useState(template.is_active);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<'edit' | 'preview'>('edit');

  const save = async () => {
    setSaving(true);
    try {
      await api.patch(`/notifications/email-templates/${template.id}/`, {
        subject,
        body_html: bodyHtml,
        body_text: bodyText,
        is_active: isActive,
      });
      toast.success('Template enregistré');
      onSaved();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setSaving(false);
    }
  };

  // Aperçu avec valeurs d'exemple basées sur variables_schema
  const previewContext: Record<string, string> = {};
  Object.keys(template.variables_schema || {}).forEach((k) => {
    previewContext[k] = `[exemple ${k}]`;
  });
  const previewHtml = bodyHtml.replace(/\{(\w+)\}/g, (_, k) => previewContext[k] || `{${k}}`);
  const previewSubject = subject.replace(/\{(\w+)\}/g, (_, k) => previewContext[k] || `{${k}}`);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-start justify-between gap-2">
          <div className="flex-1">
            <h2 className="font-display text-lg font-black text-ciDark dark:text-emerald-100">
              Éditer le template
            </h2>
            <div className="text-xs text-slate-500 mt-0.5">
              <code className="font-mono">{template.code}</code> ·
              {' '}{template.email_type} ·
              {' '}{template.sender_profile_code === 'internal' ? 'INTERNAL' : 'PUBLIC'}
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <label className="flex items-center gap-1 text-xs">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded"
              />
              Actif
            </label>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl px-2">
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>

        {/* Tabs */}
        <div className="px-4 pt-3 border-b border-slate-200 dark:border-slate-700 flex gap-3">
          <button
            onClick={() => setTab('edit')}
            className={`text-xs font-bold pb-2 border-b-2 ${
              tab === 'edit'
                ? 'border-ciOrange text-ciOrange'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Edit3 className="h-3.5 w-3.5 inline mr-1" /> Édition
          </button>
          <button
            onClick={() => setTab('preview')}
            className={`text-xs font-bold pb-2 border-b-2 ${
              tab === 'preview'
                ? 'border-ciOrange text-ciOrange'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Eye className="h-3.5 w-3.5 inline mr-1" /> Aperçu
          </button>
        </div>

        <div className="overflow-auto p-4 flex-1 space-y-4">
          {tab === 'edit' && (
            <>
              <div>
                <label className="block text-xs uppercase font-bold text-slate-500 mb-1">Sujet</label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs uppercase font-bold text-slate-500 mb-1">
                  Corps HTML
                </label>
                <textarea
                  value={bodyHtml}
                  onChange={(e) => setBodyHtml(e.target.value)}
                  rows={16}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 font-mono text-xs"
                />
              </div>
              <div>
                <label className="block text-xs uppercase font-bold text-slate-500 mb-1">
                  Corps texte (fallback)
                </label>
                <textarea
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  rows={6}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 font-mono text-xs"
                />
              </div>
              {Object.keys(template.variables_schema || {}).length > 0 && (
                <div className="text-xs text-slate-500 bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                  <strong className="text-slate-700 dark:text-slate-200">Variables disponibles :</strong>
                  {' '}
                  {Object.keys(template.variables_schema).map((k) => (
                    <code key={k} className="font-mono text-ciOrange mx-1">{`{${k}}`}</code>
                  ))}
                </div>
              )}
            </>
          )}

          {tab === 'preview' && (
            <div className="space-y-2">
              <div className="rounded-lg bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs">
                <strong>Sujet :</strong> {previewSubject}
              </div>
              <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <iframe
                  title="Aperçu template"
                  srcDoc={previewHtml}
                  className="w-full min-h-[500px] bg-white"
                  sandbox=""
                />
              </div>
              <p className="text-[11px] text-slate-400 italic">
                Les variables sont remplacées par <code>[exemple var]</code> pour cet aperçu.
              </p>
            </div>
          )}
        </div>

        <footer className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs text-slate-600 hover:bg-slate-50"
          >
            Annuler
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ciOrange text-white px-4 py-2 text-xs font-bold hover:bg-orange-600 disabled:opacity-50"
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? 'Sauvegarde…' : 'Enregistrer'}
          </button>
        </footer>
      </div>
    </div>
  );
}
