'use client';

/**
 * /auth/forgot-password — Demande de réinitialisation de mot de passe
 * Saisie email → backend envoie un lien tokenisé via inhp@veillesanitaire.com
 */

import { useState } from 'react';
import Link from 'next/link';
import { Mail, ArrowLeft, CheckCircle2, Send } from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await api.post('/auth/password-reset/request/', { email });
      setSent(true);
    } catch (e) {
      setErr(extractApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-8">
      <div className="w-full max-w-md">
        <Link
          href="/auth/login"
          className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange mb-4"
        >
          <ArrowLeft className="h-3 w-3" /> Retour à la connexion
        </Link>

        <div className="card p-8 shadow-lg">
          {!sent ? (
            <form onSubmit={submit} className="space-y-5">
              <div>
                <h2 className="font-display text-2xl font-bold">Mot de passe oublié</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Saisissez votre email professionnel. Si un compte existe, un lien
                  sécurisé vous sera envoyé pour réinitialiser votre mot de passe.
                </p>
              </div>

              <div>
                <label className="field-label">
                  <Mail className="h-3 w-3 inline mr-1" />
                  Email professionnel
                </label>
                <input
                  type="email"
                  required
                  className="input"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              {err && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                  {err}
                </div>
              )}

              <button
                type="submit"
                disabled={busy || !email}
                className="btn-primary w-full"
              >
                <Send className="h-4 w-4" />
                {busy ? 'Envoi…' : 'Envoyer le lien de réinitialisation'}
              </button>

              <p className="text-xs text-slate-500 text-center">
                Le lien expire dans 24 heures et ne peut être utilisé qu'une fois.
              </p>
            </form>
          ) : (
            <div className="text-center space-y-4">
              <div className="h-16 w-16 mx-auto rounded-full bg-emerald-100 grid place-items-center">
                <CheckCircle2 className="h-8 w-8 text-emerald-600" />
              </div>
              <h2 className="font-display text-2xl font-bold">Email envoyé</h2>
              <p className="text-sm text-slate-600">
                Si un compte est associé à <strong>{email}</strong>, vous recevrez
                un lien de réinitialisation dans quelques instants.
              </p>
              <div className="text-xs text-slate-500 bg-slate-50 rounded-lg p-3 text-left">
                <p>📧 Vérifiez votre boîte de réception (et vos spams).</p>
                <p className="mt-1">⏱ Le lien est valable 24 heures.</p>
                <p className="mt-1">🔒 Usage unique — un nouveau lien sera nécessaire au-delà.</p>
              </div>
              <Link
                href="/auth/login"
                className="btn-outline w-full"
              >
                Retour à la connexion
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
