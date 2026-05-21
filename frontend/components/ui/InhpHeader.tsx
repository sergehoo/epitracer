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

  return (
    <header className="fixed inset-x-0 top-0 z-50 glass border-b border-white/70 dark:border-emerald-950/60">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl shadow-lg bg-white grid place-items-center overflow-hidden ring-1 ring-emerald-100">
            <img
              src="https://www.inhp.ci/storage/images/website/logo%20sans%20ecriture%20inhp.png"
              alt="INHP"
              className="w-10 h-10 object-contain"
            />
          </div>
          <div className="leading-tight">
            <div className="font-display text-xl font-black text-ciDark dark:text-emerald-200">EpiTravel CI</div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              Institut National d'Hygiène Publique
            </div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-7 text-sm font-bold text-slate-700 dark:text-slate-200">
          {nav.map((n) => (
            n.href.startsWith('#') || variant === 'dashboard' ? (
              <Link key={n.href} href={n.href} className="hover:text-ciOrange transition">{n.label}</Link>
            ) : (
              <a key={n.href} href={n.href} className="hover:text-ciOrange transition">{n.label}</a>
            )
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <ThemeToggle />
          {variant === 'public' ? (
            <>
              <Link href="/pass" className="px-5 py-3 rounded-full bg-white border border-slate-200 font-bold text-ciDark hover:border-ciOrange transition">
                Voir mon pass
              </Link>
              <Link href="/voyageur" className="px-5 py-3 rounded-full bg-ciDark text-white font-bold shadow-xl hover:bg-emerald-950 transition">
                M'enregistrer
              </Link>
              <a href={adminUrl('/auth/login')} className="text-xs text-slate-500 hover:text-ciOrange">
                Espace agent
              </a>
            </>
          ) : (
            <a href={publicUrl('/')} className="px-5 py-3 rounded-full bg-white border border-slate-200 font-bold text-ciDark hover:border-ciOrange transition">
              Portail public
            </a>
          )}
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
          {variant === 'public' && (
            <>
              <Link href="/pass" className="block px-5 py-3 rounded-xl border border-slate-200 font-bold text-ciDark text-center">Voir mon pass</Link>
              <Link href="/voyageur" className="block px-5 py-3 rounded-xl bg-ciDark text-white font-bold text-center">M'enregistrer</Link>
              <a href={adminUrl('/auth/login')} className="block text-center text-xs text-slate-500 pt-2">Espace agent</a>
            </>
          )}
        </div>
      )}
    </header>
  );
}
