'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { LogIn, ShieldCheck } from 'lucide-react';
import { api, setTokens, extractApiError } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfa, setMfa] = useState('');
  const [needsMfa, setNeedsMfa] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setBusy(true);
    try {
      const { data } = await api.post('/auth/login/', {
        email, password, mfa_code: mfa || undefined,
      });
      setTokens(data.access, data.refresh);
      toast.success('Connexion réussie');
      router.replace('/dashboard');
    } catch (e: any) {
      const details: any = e?.response?.data?.error?.details;
      if (details?.mfa_required) {
        setNeedsMfa(true);
        setErr('Code MFA requis.');
      } else {
        setErr(extractApiError(e));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
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
          <p className="mt-6 text-sm opacity-80">
            En cas d'incident, contactez le support INHP au 27 21 25 35 10.
          </p>
        </div>
        <div className="text-xs opacity-70 relative">
          © {new Date().getFullYear()} République de Côte d'Ivoire · MSHPCMU · INHP
        </div>
      </aside>

      <main className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-md card p-8 space-y-5">
          <div>
            <h2 className="font-display text-2xl font-bold">Connexion</h2>
            <p className="text-sm text-slate-500 mt-1">Utilisez vos identifiants professionnels.</p>
          </div>

          <div>
            <label className="field-label">Email professionnel</label>
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>

          <div>
            <label className="field-label">Mot de passe</label>
            <input className="input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>

          {needsMfa && (
            <div>
              <label className="field-label">Code MFA (Google Authenticator)</label>
              <input className="input" inputMode="numeric" maxLength={6} value={mfa} onChange={(e) => setMfa(e.target.value)} />
            </div>
          )}

          {err && <p className="field-error">{err}</p>}

          <button disabled={busy} className="btn-primary w-full">
            <LogIn className="h-4 w-4" /> {busy ? 'Connexion…' : 'Se connecter'}
          </button>

          <p className="text-xs text-center text-slate-500">
            <Link href="/" className="underline">Retour au portail public</Link>
          </p>
        </form>
      </main>
    </div>
  );
}
