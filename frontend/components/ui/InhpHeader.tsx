'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { adminUrl, publicUrl } from '@/lib/hosts';

const PUBLIC_NAV = [
  { href: '#accompagnement', label: 'Accompagnement' },
  { href: '#ebola', label: 'Prévention Ebola' },
  { href: '#fonctionnement', label: 'Comment ça marche' },
  { href: '#urgence', label: 'Assistance' },
  { href: '#faq', label: 'FAQ' },
];
const ADMIN_NAV = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/surveillance', label: 'Surveillance' },
  { href: '/alertes', label: 'Alertes' },
  { href: '/cartographie', label: 'Cartographie' },
];

export function InhpHeader({ variant = 'public' }: { variant?: 'public' | 'dashboard' }) {
  const [open, setOpen] = useState(false);
  const nav = variant === 'public' ? PUBLIC_NAV : ADMIN_NAV;

  if (variant === 'public') return <PublicHeader open={open} setOpen={setOpen} nav={nav} />;
  return <AdminHeader open={open} setOpen={setOpen} nav={nav} />;
}

/* =====================================================================
   HEADER PUBLIC — marque touristique "Destination Côte d'Ivoire"
   - Sans logos institutionnels (relayés dans le bandeau OfficialBanner)
   - Style touristique : soleil + palmier + dégradé orange/vert
   ===================================================================== */
function PublicHeader({
  open, setOpen, nav,
}: { open: boolean; setOpen: (b: boolean) => void; nav: { href: string; label: string }[] }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 glass border-b border-white/70 dark:border-emerald-950/60">
      <div className="bg-gradient-to-r from-ciOrange via-ciGold to-ciGreen text-white text-[10px] uppercase tracking-widest">
        <div className="max-w-7xl mx-auto px-6 py-1 flex items-center justify-between font-bold">
          <span>République de Côte d'Ivoire</span>
          <span className="hidden sm:inline italic opacity-90">Union · Discipline · Travail</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
        {/* Marque typographique — lettrage script orange + caractères droits verts */}
        <Link href="/" className="group flex flex-col leading-none select-none">
          <span
            className="font-script text-ciOrange leading-[0.85] -mb-1
                       text-[2.6rem] sm:text-[3.4rem]
                       drop-shadow-[0_2px_0_rgba(247,127,0,0.18)]
                       group-hover:scale-[1.02] origin-left transition-transform"
          >
            Destination
          </span>
          <span
            className="font-display font-extrabold uppercase tracking-[0.18em]
                       text-ciGreen text-base sm:text-xl"
          >
            Côte d'Ivoire
          </span>
          <span className="mt-1 text-[10px] sm:text-xs italic text-slate-500 dark:text-slate-400">
            Akwaba · Bienvenue · Welcome
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm font-bold text-slate-700 dark:text-slate-200">
          {nav.map((n) => (
            <a key={n.href} href={n.href} className="hover:text-ciOrange transition relative group">
              {n.label}
              <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-gradient-to-r from-ciOrange to-ciGreen scale-x-0 group-hover:scale-x-100 transition-transform origin-left" />
            </a>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-2">
          <ThemeToggle />
          <Link
            href="/pass"
            className="px-4 py-2.5 rounded-full bg-white border border-slate-200 font-bold text-ciDark hover:border-ciOrange transition text-sm"
          >
            Voir mon pass
          </Link>
          <Link
            href="/voyageur"
            className="px-4 py-2.5 rounded-full bg-gradient-to-r from-ciOrange to-orange-600 text-white font-bold shadow-xl shadow-orange-500/25 hover:shadow-orange-500/40 transition text-sm"
          >
            M'enregistrer
          </Link>
          <a
            href={adminUrl('/auth/login')}
            className="text-xs text-slate-500 hover:text-ciOrange"
          >
            Espace agent
          </a>
        </div>

        <button
          onClick={() => setOpen(!open)}
          aria-label="Menu"
          className="md:hidden h-10 w-10 grid place-items-center text-ciDark dark:text-emerald-200"
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {open && (
        <div className="md:hidden px-6 pb-5 space-y-3 bg-white dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800">
          {nav.map((n) => (
            <a key={n.href} href={n.href} onClick={() => setOpen(false)} className="block font-semibold py-2">
              {n.label}
            </a>
          ))}
          <Link href="/pass" className="block px-5 py-3 rounded-xl border border-slate-200 font-bold text-ciDark text-center">
            Voir mon pass
          </Link>
          <Link href="/voyageur" className="block px-5 py-3 rounded-xl bg-gradient-to-r from-ciOrange to-orange-600 text-white font-bold text-center">
            M'enregistrer
          </Link>
          <a href={adminUrl('/auth/login')} className="block text-center text-xs text-slate-500 pt-2">
            Espace agent
          </a>
        </div>
      )}
    </header>
  );
}

/* =====================================================================
   HEADER ADMIN — conserve l'identité institutionnelle EpiTrace + logos
   ===================================================================== */
function AdminHeader({
  open, setOpen, nav,
}: { open: boolean; setOpen: (b: boolean) => void; nav: { href: string; label: string }[] }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 glass border-b border-white/70 dark:border-emerald-950/60">
      <div className="bg-ciDark text-white text-[10px] uppercase tracking-widest">
        <div className="max-w-7xl mx-auto px-6 py-1 flex items-center justify-between">
          <span>République de Côte d'Ivoire — MSHPCMU · INHP</span>
          <span className="hidden sm:inline italic opacity-80">Union · Discipline · Travail</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2">
            <img src="/logo-min-sante-2.png" alt="MSHPCMU" className="h-11 w-11 object-contain" />
            <img src="/armoirie-ci-2.png" alt="Armoiries CI" className="h-11 w-11 object-contain" />
            <img src="/logo-INHP.png" alt="INHP" className="h-9 w-auto object-contain" />
          </div>
          <img
            src="/logo-min-sante-2.png"
            alt="MSHPCMU"
            className="sm:hidden h-10 w-10 object-contain"
          />
          <div className="leading-tight border-l border-slate-200 dark:border-slate-800 pl-3">
            <div className="font-display text-base sm:text-lg font-black text-ciDark dark:text-emerald-200">
              EpiTrace
            </div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400">
              MSHPCMU · INHP · administration
            </div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm font-bold text-slate-700 dark:text-slate-200">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} className="hover:text-ciOrange transition">
              {n.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-2">
          <ThemeToggle />
          <a
            href={publicUrl('/')}
            className="px-4 py-2.5 rounded-full bg-white border border-slate-200 font-bold text-ciDark hover:border-ciOrange transition text-sm"
          >
            Portail public
          </a>
        </div>

        <button
          onClick={() => setOpen(!open)}
          aria-label="Menu"
          className="md:hidden h-10 w-10 grid place-items-center text-ciDark dark:text-emerald-200"
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {open && (
        <div className="md:hidden px-6 pb-5 space-y-3 bg-white dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} onClick={() => setOpen(false)} className="block font-semibold py-2">
              {n.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
