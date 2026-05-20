import Link from 'next/link';
import { ShieldCheck } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { adminUrl, publicUrl } from '@/lib/hosts';

export function InhpHeader({ variant = 'public' }: { variant?: 'public' | 'dashboard' }) {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 dark:border-slate-800 bg-white/85 dark:bg-slate-950/80 backdrop-blur">
      <div className="container flex h-16 items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-glow">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="font-display text-base font-bold tracking-tight">EpiTravel</div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              MINSAN · INHP · République de Côte d'Ivoire
            </div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1 text-sm">
          {variant === 'public' ? (
            <>
              <Link href="/" className="btn-ghost">Accueil</Link>
              <Link href="/voyageur" className="btn-ghost">Enregistrement</Link>
              <Link href="/pass" className="btn-ghost">Mon Pass</Link>
              <Link href="/verifier" className="btn-ghost">Vérifier un QR</Link>
              <Link href="/assistance" className="btn-ghost">Assistance</Link>
            </>
          ) : (
            <>
              <Link href="/dashboard" className="btn-ghost">Dashboard</Link>
              <Link href="/surveillance" className="btn-ghost">Surveillance</Link>
              <Link href="/alertes" className="btn-ghost">Alertes</Link>
              <Link href="/cartographie" className="btn-ghost">Cartographie</Link>
            </>
          )}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          {variant === 'public' ? (
            <a href={adminUrl('/auth/login')} className="btn-outline">Espace agent</a>
          ) : (
            <a href={publicUrl('/')} className="btn-outline">Portail public</a>
          )}
        </div>
      </div>
    </header>
  );
}
