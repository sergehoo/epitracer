'use client';

/**
 * /auth/change-password — Changement de mot de passe (utilisateur connecté)
 *
 * Mode normal : depuis le profil.
 * Mode forcé : ?forced=1 → page bloquante affichée après login si
 *   must_change_password=true côté serveur (ex: 1ère connexion).
 */

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  KeyRound, Eye, EyeOff, AlertTriangle, CheckCircle2, ShieldCheck, LogOut,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { api, clearTokens, extractApiError } from '@/lib/api';

export default function ChangePasswordPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500">Chargement…</div>}>
      <ChangePasswordInner />
    </Suspense>
  );
}

function ChangePasswordInner() {
  const router = useRouter();
  const params = useSearchParams();
  const forced = params.get('forced') === '1';

  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [busy, setBusy] = useState(false);

  const strength = passwordStrength(next);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next !== confirm) { toast.error('Les deux mots de passe ne correspondent pas.'); return; }
    if (next.length < 8) { toast.error('Minimum 8 caractères.'); return; }
    setBusy(true);
    try {
      await api.post('/auth/change-password/', {
        current_password: current,
        new_password: next,
      });
      toast.success('Mot de passe modifié — utilisez-le à la prochaine connexion.');
      // On déconnecte par sécurité (autres sessions invalidées côté serveur idéalement)
      clearTokens();
      router.replace('/auth/login');
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    clearTokens();
    router.replace('/auth/login');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-8">
      <div className="w-full max-w-md">
        <form onSubmit={submit} className="card p-8 space-y-5 shadow-lg">
          <div>
            <h2 className="font-display text-2xl font-bold flex items-center gap-2">
              <KeyRound className="h-6 w-6 text-ciOrange" />
              Changement de mot de passe
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {forced
                ? 'Pour des raisons de sécurité, vous devez définir un nouveau mot de passe avant d\'accéder à la console.'
                : 'Choisissez un nouveau mot de passe sécurisé.'}
            </p>
          </div>

          {forced && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 flex items-start gap-2">
              <ShieldCheck className="h-4 w-4 mt-0.5 shrink-0" />
              <p>
                <strong>Changement obligatoire :</strong> votre mot de passe actuel
                est temporaire (premier login ou réinitialisation par l'administrateur).
              </p>
            </div>
          )}

          <PwdField
            label="Mot de passe actuel"
            value={current} onChange={setCurrent}
            show={showCurrent} toggle={() => setShowCurrent((v) => !v)}
            autoComplete="current-password"
          />

          <PwdField
            label="Nouveau mot de passe"
            value={next} onChange={setNext}
            show={showNew} toggle={() => setShowNew((v) => !v)}
            autoComplete="new-password"
          />

          <div>
            <div className="flex gap-1 h-1.5">
              {[0,1,2,3].map((i) => (
                <div key={i} className={`flex-1 rounded-full transition-colors ${
                  i < strength.level
                    ? strength.level <= 1 ? 'bg-rose-400'
                      : strength.level === 2 ? 'bg-amber-400'
                      : strength.level === 3 ? 'bg-lime-500'
                      : 'bg-emerald-500'
                    : 'bg-slate-200'
                }`} />
              ))}
            </div>
            <p className={`text-xs mt-1 ${strength.color}`}>
              Force : {strength.label}
              {strength.hint && <span className="text-slate-400"> — {strength.hint}</span>}
            </p>
          </div>

          <PwdField
            label="Confirmer le nouveau mot de passe"
            value={confirm} onChange={setConfirm}
            show={showNew} toggle={() => setShowNew((v) => !v)}
            autoComplete="new-password"
          />

          <button
            type="submit"
            disabled={busy || !current || !next || next !== confirm}
            className="btn-primary w-full"
          >
            {busy ? 'Enregistrement…' : 'Enregistrer'}
          </button>

          {forced ? (
            <button
              type="button"
              onClick={logout}
              className="w-full text-xs text-slate-500 hover:text-rose-600 inline-flex items-center justify-center gap-1"
            >
              <LogOut className="h-3 w-3" /> Annuler et se déconnecter
            </button>
          ) : (
            <Link href="/dashboard" className="block text-xs text-center text-slate-500 hover:text-ciOrange">
              ← Retour au dashboard
            </Link>
          )}
        </form>
      </div>
    </div>
  );
}

function PwdField({
  label, value, onChange, show, toggle, autoComplete,
}: {
  label: string; value: string;
  onChange: (v: string) => void;
  show: boolean; toggle: () => void;
  autoComplete?: string;
}) {
  return (
    <div>
      <label className="field-label">{label}</label>
      <div className="relative">
        <input
          className="input pr-10"
          type={show ? 'text' : 'password'}
          required
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          onClick={toggle}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
          tabIndex={-1}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function passwordStrength(pw: string): { level: number; label: string; color: string; hint?: string } {
  if (!pw) return { level: 0, label: 'aucune', color: 'text-slate-400' };
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) s++;
  if (s <= 1) return { level: 1, label: 'faible', color: 'text-rose-600', hint: 'ajoutez majuscules + chiffres + symboles' };
  if (s === 2) return { level: 2, label: 'moyen', color: 'text-amber-600', hint: 'allongez à 12+ caractères' };
  if (s === 3) return { level: 3, label: 'bon', color: 'text-lime-600' };
  return { level: 4, label: 'excellent', color: 'text-emerald-600' };
}
