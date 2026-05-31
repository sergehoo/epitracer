'use client';

/**
 * /auth/reset-password?token=xxx — Confirmation reset password
 * Lien arrivé par email INTERNAL. Saisie du nouveau mot de passe.
 */

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  KeyRound, Eye, EyeOff, CheckCircle2, ArrowLeft, AlertTriangle,
} from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500">Chargement…</div>}>
      <ResetPasswordInner />
    </Suspense>
  );
}

function ResetPasswordInner() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get('token') || '';

  const [pwd, setPwd] = useState('');
  const [pwd2, setPwd2] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const strength = passwordStrength(pwd);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    if (pwd !== pwd2) { setErr('Les deux mots de passe ne correspondent pas.'); return; }
    if (pwd.length < 8) { setErr('Le mot de passe doit faire au moins 8 caractères.'); return; }
    setBusy(true);
    try {
      await api.post('/auth/password-reset/confirm/', { token, new_password: pwd });
      setDone(true);
      setTimeout(() => router.replace('/auth/login'), 2500);
    } catch (e) {
      setErr(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md card p-8 text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-rose-500 mx-auto" />
          <h2 className="font-display text-xl font-bold">Lien invalide</h2>
          <p className="text-sm text-slate-600">
            Le lien de réinitialisation est incomplet ou invalide. Demandez un
            nouveau lien depuis la page de mot de passe oublié.
          </p>
          <Link href="/auth/forgot-password" className="btn-primary w-full">
            Demander un nouveau lien
          </Link>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md card p-8 text-center space-y-4">
          <div className="h-16 w-16 mx-auto rounded-full bg-emerald-100 grid place-items-center">
            <CheckCircle2 className="h-8 w-8 text-emerald-600" />
          </div>
          <h2 className="font-display text-2xl font-bold">Mot de passe réinitialisé</h2>
          <p className="text-sm text-slate-600">
            Vous allez être redirigé vers la page de connexion…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-8">
      <div className="w-full max-w-md">
        <Link
          href="/auth/login"
          className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange mb-4"
        >
          <ArrowLeft className="h-3 w-3" /> Retour à la connexion
        </Link>

        <form onSubmit={submit} className="card p-8 space-y-5 shadow-lg">
          <div>
            <h2 className="font-display text-2xl font-bold flex items-center gap-2">
              <KeyRound className="h-6 w-6 text-ciOrange" />
              Nouveau mot de passe
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Choisissez un mot de passe fort. Min. 8 caractères, mélange de
              majuscules, minuscules, chiffres et symboles.
            </p>
          </div>

          <div>
            <label className="field-label">Nouveau mot de passe</label>
            <div className="relative">
              <input
                className="input pr-10"
                type={show ? 'text' : 'password'}
                required
                autoComplete="new-password"
                value={pwd}
                onChange={(e) => setPwd(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShow((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                tabIndex={-1}
              >
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <div className="mt-2">
              <div className="flex gap-1 h-1.5">
                {[0,1,2,3].map((i) => (
                  <div
                    key={i}
                    className={`flex-1 rounded-full transition-colors ${
                      i < strength.level
                        ? strength.level <= 1 ? 'bg-rose-400'
                          : strength.level === 2 ? 'bg-amber-400'
                          : strength.level === 3 ? 'bg-lime-500'
                          : 'bg-emerald-500'
                        : 'bg-slate-200'
                    }`}
                  />
                ))}
              </div>
              <p className={`text-xs mt-1 ${strength.color}`}>
                Force : {strength.label}
              </p>
            </div>
          </div>

          <div>
            <label className="field-label">Confirmation</label>
            <input
              className="input"
              type={show ? 'text' : 'password'}
              required
              autoComplete="new-password"
              value={pwd2}
              onChange={(e) => setPwd2(e.target.value)}
            />
            {pwd2 && pwd === pwd2 && (
              <p className="text-xs text-emerald-600 mt-1 inline-flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Mots de passe identiques
              </p>
            )}
          </div>

          {err && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {err}
            </div>
          )}

          <button
            type="submit"
            disabled={busy || !pwd || pwd !== pwd2}
            className="btn-primary w-full"
          >
            {busy ? 'Enregistrement…' : 'Enregistrer le nouveau mot de passe'}
          </button>
        </form>
      </div>
    </div>
  );
}

function passwordStrength(pw: string): { level: number; label: string; color: string } {
  if (!pw) return { level: 0, label: 'aucune', color: 'text-slate-400' };
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) s++;
  if (s <= 1) return { level: 1, label: 'faible', color: 'text-rose-600' };
  if (s === 2) return { level: 2, label: 'moyen', color: 'text-amber-600' };
  if (s === 3) return { level: 3, label: 'bon', color: 'text-lime-600' };
  return { level: 4, label: 'excellent', color: 'text-emerald-600' };
}
