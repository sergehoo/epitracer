'use client';

/**
 * /auth/login — Page de connexion EpiTrace
 *
 * Flow multi-étapes :
 *   1. Email + password
 *   2. Si MFA activée → code OTP 6 chiffres reçu par email
 *      (avec bouton "Renvoyer le code" + cooldown 60s)
 *   3. Si must_change_password → redirection forcée /auth/change-password
 *
 * États gérés :
 *   - Compte verrouillé (manuel ou auto)
 *   - Tentatives restantes avant verrouillage
 *   - Erreurs serveur en clair
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import {
  LogIn, ShieldCheck, Mail, KeyRound, ArrowLeft, RefreshCcw,
  AlertTriangle, Lock, Eye, EyeOff, CheckCircle2,
} from 'lucide-react';
import { api, setTokens, extractApiError } from '@/lib/api';

type Step = 'credentials' | 'mfa';

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('credentials');

  // Step 1 — email/password
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);

  // Step 2 — MFA
  const [mfa, setMfa] = useState('');
  const [emailMasked, setEmailMasked] = useState('');
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  // Status
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);

  // Cooldown timer pour le renvoi de code
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const { data } = await api.post('/auth/login/', {
        email,
        password,
        mfa_code: step === 'mfa' ? mfa : undefined,
      });
      // Login OK : stocke les tokens
      setTokens(data.access, data.refresh);

      if (data.must_change_password) {
        toast.success('Connexion réussie — veuillez changer votre mot de passe.');
        router.replace('/auth/change-password?forced=1');
        return;
      }
      toast.success('Connexion réussie');
      router.replace('/dashboard');
    } catch (e: any) {
      const details: any = e?.response?.data?.error?.details || e?.response?.data;

      // Compte verrouillé (auto ou manuel)
      const detailMsg = String(details?.detail || '');
      if (
        detailMsg.toLowerCase().includes('verrouill') ||
        details?.locked
      ) {
        setLocked(true);
        setErr(detailMsg || 'Compte verrouillé.');
        return;
      }

      // MFA requis (1ère étape réussie, code envoyé auto par le backend)
      if (details?.mfa_required) {
        setStep('mfa');
        if (details?.email_masked) setEmailMasked(details.email_masked);
        setResendCooldown(60);
        setErr(null);
        toast.success(`Un code a été envoyé à ${details?.email_masked || 'votre email'}.`);
        return;
      }

      // Code MFA incorrect avec tentatives restantes
      if (details?.attempts_remaining !== undefined) {
        setAttemptsRemaining(details.attempts_remaining);
      }

      setErr(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const resendCode = async () => {
    if (resendCooldown > 0) return;
    setBusy(true);
    try {
      await api.post('/auth/mfa/email/resend/', { email });
      toast.success('Nouveau code envoyé');
      setResendCooldown(60);
      setMfa('');
      setAttemptsRemaining(null);
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const backToCredentials = () => {
    setStep('credentials');
    setMfa('');
    setErr(null);
    setAttemptsRemaining(null);
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* ───────────────── Hero institutionnel ───────────────── */}
      <aside className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-emerald-900 via-emerald-700 to-emerald-800 text-white relative overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-ciOrange/30 rounded-full blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-ciGreen/30 rounded-full blur-3xl" />

        <Link href="/" className="flex items-center gap-3 relative">
          <img src="/logo-min-sante-2.png" alt="MSHPCMU" className="h-12 w-12 bg-white rounded-xl p-1 object-contain" />
          <img src="/armoirie-ci-2.png" alt="Armoiries CI" className="h-12 w-12 bg-white rounded-xl p-1 object-contain" />
          <img src="/logo-INHP.png" alt="INHP" className="h-10 w-auto bg-white rounded-xl p-1 object-contain" />
        </Link>

        <div className="relative">
          <div className="text-xs uppercase tracking-widest text-emerald-200 mb-2">
            République de Côte d'Ivoire — MSHPCMU · INHP
          </div>
          <h1 className="font-display text-4xl font-extrabold flex items-center gap-3">
            <ShieldCheck className="h-8 w-8 text-ciOrange" />
            Espace professionnel
          </h1>
          <p className="mt-3 opacity-90 max-w-md">
            Accès réservé aux agents du MSHPCMU, de l'INHP, des districts sanitaires
            et des points d'entrée frontaliers.
          </p>

          <div className="mt-8 space-y-2 text-sm opacity-90">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-ciOrange" />
              <span>Authentification à deux facteurs (code par email)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-ciOrange" />
              <span>Verrouillage automatique après 5 tentatives</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-ciOrange" />
              <span>Journalisation complète des accès</span>
            </div>
          </div>

          <p className="mt-6 text-sm opacity-80">
            En cas d'incident, contactez le support INHP au <strong>143</strong>.
          </p>
        </div>

        <div className="text-xs opacity-70 relative">
          © {new Date().getFullYear()} République de Côte d'Ivoire · MSHPCMU · INHP
        </div>
      </aside>

      {/* ───────────────── Formulaire ───────────────── */}
      <main className="flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md">

          {/* Logo mobile */}
          <Link href="/" className="lg:hidden flex items-center justify-center gap-2 mb-6">
            <img src="/logo-INHP.png" alt="INHP" className="h-10 w-auto object-contain" />
          </Link>

          {/* ─────────── Card connexion ─────────── */}
          <form onSubmit={submit} className="card p-8 space-y-5 shadow-lg">

            {/* ─── Étape 1 : email/password ─── */}
            {step === 'credentials' && (
              <>
                <div>
                  <h2 className="font-display text-2xl font-bold">Connexion</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Utilisez vos identifiants professionnels.
                  </p>
                </div>

                <div>
                  <label className="field-label">
                    <Mail className="h-3 w-3 inline mr-1" />
                    Email professionnel
                  </label>
                  <input
                    className="input"
                    type="email"
                    required
                    autoComplete="username"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={locked}
                  />
                </div>

                <div>
                  <label className="field-label">
                    <KeyRound className="h-3 w-3 inline mr-1" />
                    Mot de passe
                  </label>
                  <div className="relative">
                    <input
                      className="input pr-10"
                      type={showPwd ? 'text' : 'password'}
                      required
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={locked}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd((v) => !v)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                      tabIndex={-1}
                    >
                      {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* ─── Étape 2 : code MFA ─── */}
            {step === 'mfa' && (
              <>
                <button
                  type="button"
                  onClick={backToCredentials}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange"
                >
                  <ArrowLeft className="h-3 w-3" /> Retour
                </button>

                <div>
                  <h2 className="font-display text-2xl font-bold flex items-center gap-2">
                    <ShieldCheck className="h-6 w-6 text-ciOrange" />
                    Vérification
                  </h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Un code à 6 chiffres a été envoyé à{' '}
                    <strong className="font-mono">{emailMasked || email}</strong>.
                    Saisissez-le ci-dessous pour finaliser la connexion.
                  </p>
                </div>

                <div>
                  <label className="field-label">Code de vérification</label>
                  <input
                    className="input text-center font-mono text-2xl tracking-[0.5em] py-3"
                    inputMode="numeric"
                    pattern="\d{6}"
                    maxLength={6}
                    autoComplete="one-time-code"
                    placeholder="••••••"
                    required
                    value={mfa}
                    onChange={(e) => setMfa(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    autoFocus
                  />
                  {attemptsRemaining !== null && attemptsRemaining > 0 && (
                    <p className="text-xs text-amber-600 mt-2">
                      ⚠ {attemptsRemaining} tentative(s) restante(s) avant régénération.
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={resendCode}
                  disabled={resendCooldown > 0 || busy}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-ciOrange disabled:opacity-50"
                >
                  <RefreshCcw className="h-3 w-3" />
                  {resendCooldown > 0
                    ? `Renvoyer le code dans ${resendCooldown}s`
                    : 'Renvoyer le code'}
                </button>
              </>
            )}

            {/* ─── Erreur ─── */}
            {err && (
              <div className={`rounded-lg border p-3 flex items-start gap-2 text-sm ${
                locked
                  ? 'bg-rose-50 border-rose-200 text-rose-700'
                  : 'bg-amber-50 border-amber-200 text-amber-800'
              }`}>
                {locked ? (
                  <Lock className="h-4 w-4 mt-0.5 shrink-0" />
                ) : (
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                )}
                <span>{err}</span>
              </div>
            )}

            {/* ─── Bouton submit ─── */}
            <button
              type="submit"
              disabled={busy || locked || (step === 'mfa' && mfa.length !== 6)}
              className="btn-primary w-full"
            >
              <LogIn className="h-4 w-4" />
              {busy
                ? 'Connexion…'
                : step === 'credentials'
                  ? 'Continuer'
                  : 'Valider et se connecter'}
            </button>

            {/* ─── Liens ─── */}
            {step === 'credentials' && (
              <div className="flex items-center justify-between text-xs">
                <Link href="/auth/forgot-password" className="text-ciOrange hover:underline font-semibold">
                  Mot de passe oublié ?
                </Link>
                <Link href="/" className="text-slate-500 hover:underline">
                  Retour au portail
                </Link>
              </div>
            )}
          </form>

          {/* Bloc sécurité info */}
          <div className="mt-6 text-center text-xs text-slate-500 space-y-1">
            <p>🔒 Connexion sécurisée — toutes les communications sont chiffrées (TLS 1.3).</p>
            <p>
              Besoin d'aide ? Écrivez à{' '}
              <a href="mailto:inhp@veillesanitaire.com" className="text-ciOrange hover:underline">
                inhp@veillesanitaire.com
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
