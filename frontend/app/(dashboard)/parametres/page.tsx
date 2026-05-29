'use client';

/**
 * /dashboard/parametres — Profil utilisateur + paramètres administratifs.
 *
 * Sections :
 *  1. Profil      → identité, MFA, dernière connexion
 *  2. Rôles       → rôles affectés + organisations + descriptions
 *  3. Sécurité    → changement du mot de passe (current → new + confirm)
 *  4. Apparence   → thème clair/sombre/système
 *  5. Système     → URL API, env, clé publique VAPID
 */

import { FormEvent, useEffect, useState } from 'react';
import {
  Bell, CheckCircle2, Eye, EyeOff, Globe2, Info, KeyRound, Lock,
  Mail, Moon, Palette, Phone, Server, Shield, ShieldCheck, Sun,
  User, UserCheck, Briefcase, Calendar, AlertTriangle,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { toast } from 'react-hot-toast';
import { api, API_URL, extractApiError } from '@/lib/api';

interface VapidResp { public_key: string }

interface UserRole {
  code: string;
  name: string;
  organization?: string | null;
}

interface MeData {
  id: number;
  uuid: string;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  phone?: string;
  job_title?: string;
  is_active?: boolean;
  is_locked?: boolean;
  mfa_enabled?: boolean;
  date_joined?: string;
  last_login?: string | null;
  roles?: UserRole[];
}

export default function ParametresPage() {
  const { theme, setTheme, systemTheme } = useTheme();
  const [vapid, setVapid] = useState<string>('');
  const [me, setMe] = useState<MeData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<VapidResp>('/public/push/public-key/')
      .then((r) => setVapid(r.data.public_key))
      .catch(() => undefined);
    api.get<MeData>('/auth/me/')
      .then((r) => setMe(r.data))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const effectiveTheme = theme === 'system' ? systemTheme : theme;
  const displayName =
    me?.full_name ||
    [me?.first_name, me?.last_name].filter(Boolean).join(' ') ||
    me?.email ||
    '—';

  return (
    <div className="space-y-6 max-w-5xl">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Réglages
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Mon profil & paramètres
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Consultez vos informations, votre rôle, et gérez votre mot de passe.
        </p>
      </header>

      {/* ============ Profil ============ */}
      <Section icon={<User className="h-5 w-5" />} title="Mon profil">
        {loading ? (
          <p className="text-xs text-slate-400">Chargement…</p>
        ) : (
          <>
            <div className="flex items-start gap-4">
              <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-ciOrange to-ciGreen text-white grid place-items-center font-display font-black text-2xl shrink-0">
                {(me?.first_name?.[0] || me?.email?.[0] || '?').toUpperCase()}
              </div>
              <div className="flex-1">
                <div className="font-display text-lg font-black text-ciDark dark:text-emerald-100">
                  {displayName}
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-slate-500">
                  <span className="inline-flex items-center gap-1"><Mail className="h-3 w-3" />{me?.email}</span>
                  {me?.phone && (
                    <span className="inline-flex items-center gap-1"><Phone className="h-3 w-3" />{me.phone}</span>
                  )}
                  {me?.job_title && (
                    <span className="inline-flex items-center gap-1"><Briefcase className="h-3 w-3" />{me.job_title}</span>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <StatusPill
                ok={me?.is_active}
                okLabel="Compte actif"
                koLabel="Compte désactivé"
                icon={me?.is_active ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
              />
              <StatusPill
                ok={!me?.is_locked}
                okLabel="Non verrouillé"
                koLabel="Verrouillé"
                icon={me?.is_locked ? <Lock className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
              />
              <StatusPill
                ok={me?.mfa_enabled}
                okLabel="MFA activée"
                koLabel="MFA désactivée"
                neutral={!me?.mfa_enabled}
                icon={<ShieldCheck className="h-3.5 w-3.5" />}
              />
              <div className="px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[11px] font-semibold inline-flex items-center gap-1.5 self-start">
                <Calendar className="h-3.5 w-3.5" />
                {me?.last_login
                  ? `Dernière connexion : ${new Date(me.last_login).toLocaleString('fr-FR', {
                      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}`
                  : 'Jamais connecté'}
              </div>
            </div>
          </>
        )}
      </Section>

      {/* ============ Rôles & permissions ============ */}
      <Section icon={<Shield className="h-5 w-5" />} title="Mes rôles & permissions">
        {loading ? (
          <p className="text-xs text-slate-400">Chargement…</p>
        ) : !me?.roles || me.roles.length === 0 ? (
          <div className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 rounded-lg p-3 inline-flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              Aucun rôle n'est actuellement affecté à votre compte. Contactez
              votre administrateur national pour obtenir vos droits d'accès.
            </span>
          </div>
        ) : (
          <div className="space-y-2">
            {me.roles.map((r) => (
              <article
                key={r.code + (r.organization || '')}
                className="rounded-2xl border border-slate-200 dark:border-slate-700 p-4 flex flex-wrap items-start gap-3 bg-gradient-to-br from-emerald-50/40 to-orange-50/30 dark:from-emerald-900/10 dark:to-orange-900/10"
              >
                <div className="h-10 w-10 rounded-xl bg-ciOrange/10 text-ciOrange grid place-items-center shrink-0">
                  <UserCheck className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-ciDark dark:text-emerald-100">{r.name}</span>
                    <code className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
                      {r.code}
                    </code>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
                    {ROLE_DESCRIPTIONS[r.code] || 'Rôle système EpiTrace.'}
                  </p>
                  {r.organization && (
                    <div className="mt-2 inline-flex items-center gap-1 text-[11px] text-slate-500">
                      <Briefcase className="h-3 w-3" />
                      Affecté à : <span className="font-semibold">{r.organization}</span>
                    </div>
                  )}
                </div>
              </article>
            ))}
            <p className="text-[11px] text-slate-400 mt-2 italic">
              Les permissions exactes sont déterminées par votre administrateur national.
              Pour modifier vos rôles, contactez-le.
            </p>
          </div>
        )}
      </Section>

      {/* ============ Sécurité : mot de passe ============ */}
      <Section icon={<KeyRound className="h-5 w-5" />} title="Changer mon mot de passe">
        <PasswordChangeForm />
      </Section>

      {/* ============ Apparence ============ */}
      <Section icon={<Palette className="h-5 w-5" />} title="Apparence">
        <div className="flex flex-wrap gap-2">
          <ThemeOption value="light" current={theme} onChange={setTheme} icon={<Sun className="h-4 w-4" />} label="Clair" />
          <ThemeOption value="dark" current={theme} onChange={setTheme} icon={<Moon className="h-4 w-4" />} label="Sombre" />
          <ThemeOption value="system" current={theme} onChange={setTheme} icon={<Globe2 className="h-4 w-4" />} label="Système" />
        </div>
        <p className="text-xs text-slate-500 mt-3">
          Thème courant : <strong>{effectiveTheme || 'inconnu'}</strong>.
          Le mode "Système" suit automatiquement les préférences de votre OS.
        </p>
      </Section>

      {/* ============ Notifications ============ */}
      <Section icon={<Bell className="h-5 w-5" />} title="Notifications">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Les agents reçoivent les alertes critiques en temps réel dans l'interface admin
          (WebSocket) et par email pour les événements majeurs. Configuration centrale
          assurée par l'administrateur national.
        </p>
      </Section>

      {/* ============ Système & API ============ */}
      <Section icon={<Server className="h-5 w-5" />} title="Système & API">
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="URL API" value={API_URL || '—'} mono />
          <Field label="Environnement" value={process.env.NODE_ENV || 'production'} />
        </div>
      </Section>

      {/* ============ VAPID (Web Push) ============ */}
      {vapid && (
        <Section icon={<KeyRound className="h-5 w-5" />} title="Clé publique Web Push (VAPID)">
          <p className="text-sm text-slate-600 dark:text-slate-300 mb-3">
            Clé exposée à la PWA voyageur pour s'abonner aux notifications push.
            Information publique — peut être partagée librement.
          </p>
          <div className="card p-3 bg-slate-50 dark:bg-slate-900 font-mono text-[11px] break-all">
            {vapid}
          </div>
        </Section>
      )}

      <div className="card p-4 bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 flex items-start gap-2">
        <Info className="h-4 w-4 mt-0.5 shrink-0" />
        <p>
          Pour la gestion utilisateurs, RBAC, intégrations Twilio/Orange CI, ou les
          réglages avancés, utilisez la page <strong>Utilisateurs</strong> ou
          l'interface Django Admin sécurisée.
        </p>
      </div>
    </div>
  );
}

/* ============================================================ */
/*                  FORMULAIRE CHANGEMENT MDP                    */
/* ============================================================ */

function PasswordChangeForm() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const strength = passwordStrength(next);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      toast.error('Les deux nouveaux mots de passe ne correspondent pas.');
      return;
    }
    if (next.length < 8) {
      toast.error('Le nouveau mot de passe doit faire au moins 8 caractères.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/auth/change-password/', {
        current_password: current,
        new_password: next,
      });
      toast.success('Mot de passe modifié avec succès. À utiliser à votre prochaine connexion.');
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4 max-w-lg">
      <PwdField
        label="Mot de passe actuel"
        value={current}
        onChange={setCurrent}
        show={showCurrent}
        toggle={() => setShowCurrent((v) => !v)}
        autoComplete="current-password"
      />
      <PwdField
        label="Nouveau mot de passe"
        value={next}
        onChange={setNext}
        show={showNew}
        toggle={() => setShowNew((v) => !v)}
        autoComplete="new-password"
        helper={
          <div className="space-y-1">
            <div className="flex gap-1 h-1.5">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className={`flex-1 rounded-full transition-colors ${
                    i < strength.level
                      ? strength.level <= 1
                        ? 'bg-rose-400'
                        : strength.level === 2
                        ? 'bg-amber-400'
                        : strength.level === 3
                        ? 'bg-lime-500'
                        : 'bg-emerald-500'
                      : 'bg-slate-200 dark:bg-slate-700'
                  }`}
                />
              ))}
            </div>
            <p className={`text-[11px] ${strength.color}`}>
              {strength.label}
              {strength.hint && <span className="text-slate-400"> — {strength.hint}</span>}
            </p>
          </div>
        }
      />
      <PwdField
        label="Confirmer le nouveau mot de passe"
        value={confirm}
        onChange={setConfirm}
        show={showNew}
        toggle={() => setShowNew((v) => !v)}
        autoComplete="new-password"
        helper={
          confirm && next !== confirm ? (
            <p className="text-[11px] text-rose-600">Les mots de passe ne correspondent pas.</p>
          ) : confirm && next === confirm ? (
            <p className="text-[11px] text-emerald-600 inline-flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Confirmation OK
            </p>
          ) : null
        }
      />
      <button
        type="submit"
        disabled={submitting || !current || !next || next !== confirm}
        className="inline-flex items-center gap-2 rounded-lg bg-ciOrange text-white px-4 py-2 text-sm font-bold hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <KeyRound className="h-4 w-4" />
        {submitting ? 'Modification…' : 'Modifier le mot de passe'}
      </button>
      <p className="text-[11px] text-slate-400 leading-relaxed">
        Politique : minimum 8 caractères, ne pas réutiliser un mot de passe trop courant
        ni similaire à votre identité. La modification déconnectera vos autres sessions actives.
      </p>
    </form>
  );
}

function PwdField({
  label, value, onChange, show, toggle, autoComplete, helper,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  show: boolean;
  toggle: () => void;
  autoComplete?: string;
  helper?: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-widest text-slate-500 font-bold mb-1">
        {label}
      </label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm pr-10 focus:outline-none focus:ring-2 focus:ring-ciOrange/30 focus:border-ciOrange"
        />
        <button
          type="button"
          onClick={toggle}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          tabIndex={-1}
          aria-label={show ? 'Masquer' : 'Afficher'}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {helper && <div className="mt-1.5">{helper}</div>}
    </div>
  );
}

/* ============================================================ */
/*                       HELPERS / TYPES                         */
/* ============================================================ */

function passwordStrength(pw: string): { level: number; label: string; color: string; hint?: string } {
  if (!pw) return { level: 0, label: 'Saisissez un mot de passe', color: 'text-slate-400' };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { level: 1, label: 'Faible', color: 'text-rose-600', hint: 'Ajoutez majuscules, chiffres et symboles' };
  if (score === 2) return { level: 2, label: 'Moyen', color: 'text-amber-600', hint: 'Augmentez la longueur' };
  if (score === 3) return { level: 3, label: 'Bon', color: 'text-lime-600' };
  return { level: 4, label: 'Excellent', color: 'text-emerald-600' };
}

const ROLE_DESCRIPTIONS: Record<string, string> = {
  NATIONAL_ADMIN: "Administrateur national. Accès complet à la plateforme : gestion utilisateurs, configuration RBAC, paramètres système, audit complet.",
  MINISTRY: "Ministère de la Santé (MSHPCMU). Pilotage stratégique, vision nationale, tableaux de bord agrégés.",
  INHP: "Institut National d'Hygiène Publique. Surveillance épidémiologique opérationnelle, gestion des alertes, validation des cas.",
  EPIDEMIOLOGIST: "Épidémiologiste. Analyse des données, scoring, investigations, rapports.",
  HEALTH_AGENT: "Agent de santé. Saisie des contrôles, scan des pass voyageurs aux points d'entrée, fiches de surveillance.",
  POE_AGENT: "Agent de point d'entrée. Scan QR, vérification d'identité, orientation des voyageurs entrants.",
  DOCTOR: "Médecin. Consultations, diagnostic, prescriptions, validation médicale.",
  FOLLOWUP_AGENT: "Agent de suivi 21 jours. Check-ins quotidiens, messagerie voyageurs, escalade des cas symptomatiques.",
  LAB_AGENT: "Agent de laboratoire. Saisie des résultats biologiques, certificats.",
  ANALYST: "Analyste / data. Lecture seule, exports, statistiques, reports.",
  AUDITOR: "Auditeur. Lecture seule du journal d'audit, contrôle a posteriori.",
};

/* ============================================================ */
/*                      COMPOSANTS UI                            */
/* ============================================================ */

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <section className="card p-5">
      <header className="flex items-center gap-2 mb-4 text-emerald-700 dark:text-emerald-300">
        {icon}
        <h2 className="font-display font-bold text-ciDark dark:text-emerald-100">{title}</h2>
      </header>
      {children}
    </section>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-1">{label}</div>
      <div className={`text-sm ${mono ? 'font-mono' : ''}`}>{value}</div>
    </div>
  );
}

function ThemeOption({
  value, current, onChange, icon, label,
}: {
  value: string; current?: string;
  onChange: (v: string) => void;
  icon: React.ReactNode; label: string;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onChange(value)}
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border transition ${
        active
          ? 'bg-emerald-600 text-white border-emerald-600 shadow'
          : 'bg-white border-slate-200 hover:border-emerald-500'
      }`}
    >
      {icon}
      <span className="text-sm font-semibold">{label}</span>
    </button>
  );
}

function StatusPill({
  ok, okLabel, koLabel, icon, neutral,
}: {
  ok?: boolean;
  okLabel: string;
  koLabel: string;
  icon: React.ReactNode;
  neutral?: boolean;
}) {
  const cls = neutral
    ? 'bg-slate-100 dark:bg-slate-800 text-slate-500'
    : ok
    ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
    : 'bg-rose-100 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300';
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold ${cls} self-start`}>
      {icon}
      {ok ? okLabel : koLabel}
    </span>
  );
}
