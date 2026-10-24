'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Menu, X } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { adminUrl, publicUrl } from '@/lib/hosts';
import { useLocale } from '@/lib/i18n';

/** Liens de navigation publics ; les ancres pointent vers les sections de l'accueil. */
const PUBLIC_NAV = [
  { href: '#services', key: 'services' },
  { href: '/maladies', key: 'diseases' },
  { href: '#fonctionnement', key: 'how' },
  { href: '/assistance', key: 'assistance' },
  { href: '#faq', key: 'faq' },
] as const;

/**
 * Résout un lien d'ancre (#section) en fonction de la page courante :
 * - sur "/" → "#section" (scroll local) ;
 * - ailleurs → "/#section" (navigue d'abord à l'accueil puis scrolle).
 */
function resolveAnchorHref(href: string, currentPath: string | null): string {
  if (!href.startsWith('#')) return href;
  if (currentPath === '/') return href;
  return `/${href}`; // ex : "#faq" → "/#faq"
}
const ADMIN_NAV = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/surveillance', label: 'Surveillance' },
  { href: '/alertes', label: 'Alertes' },
  { href: '/cartographie', label: 'Cartographie' },
];

export function InhpHeader({ variant = 'public' }: { variant?: 'public' | 'dashboard' }) {
  const [open, setOpen] = useState(false);
  if (variant === 'public') return <PublicHeader open={open} setOpen={setOpen} />;
  return <AdminHeader open={open} setOpen={setOpen} nav={ADMIN_NAV} />;
}

/** Bande tricolore orange · blanc · vert (drapeau ivoirien). */
export function TricolorBand({ className = 'h-1' }: { className?: string }) {
  return (
    <div className={`flex ${className}`} aria-hidden="true">
      <span className="flex-1 bg-ciOrange" />
      <span className="flex-1 bg-white" />
      <span className="flex-1 bg-ciGreen" />
    </div>
  );
}

/** Sélecteur de langue FR / EN (portail public). */
export function LanguageSwitch({ className = '' }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();
  return (
    <div role="group" aria-label={t.nav.language} className={`inline-flex rounded-full border border-slate-200 bg-white p-0.5 ${className}`}>
      {(['fr', 'en'] as const).map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLocale(l)}
          aria-pressed={locale === l}
          lang={l}
          className={`min-w-[2.5rem] rounded-full px-2.5 py-1 text-xs font-bold uppercase transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest ${
            locale === l ? 'bg-ciForest text-white' : 'text-slate-600 hover:text-ciForest'
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

/* =====================================================================
   HEADER PUBLIC — GovTech : bande tricolore, identité institutionnelle,
   navigation sticky compacte, FR/EN, CTA pass + enregistrement.
   ===================================================================== */
function PublicHeader({ open, setOpen }: { open: boolean; setOpen: (b: boolean) => void }) {
  const pathname = usePathname();
  const { t, locale } = useLocale();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  useEffect(() => { setOpen(false); }, [pathname, setOpen]);

  return (
    <header
      lang={locale}
      className={`fixed inset-x-0 top-0 z-50 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/85 transition-shadow ${
        scrolled ? 'shadow-[0_6px_24px_-12px_rgba(15,23,42,0.25)]' : 'border-b border-slate-200/70'
      }`}
    >
      <TricolorBand />
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2.5 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ciForest"
        >
          <Image src="/armoirie-ci-2.png" alt="" width={36} height={36} className="h-9 w-9 shrink-0 object-contain" priority />
          <Image src="/logo-min-sante-2.png" alt="" width={36} height={36} className="hidden h-9 w-9 shrink-0 object-contain sm:block" priority />
          <span className="min-w-0 border-l border-slate-200 pl-2.5 leading-tight">
            <span className="block truncate font-display text-base font-extrabold text-ciForest">
              EpiTrace <span className="font-semibold text-slate-500">CI</span>
            </span>
            <span className="hidden truncate text-[11px] text-slate-500 sm:block">
              {t.brand.tagline} · {t.brand.institutions}
            </span>
          </span>
        </Link>

        <nav aria-label={t.nav.main} className="hidden items-center gap-1 xl:flex">
          {PUBLIC_NAV.map((n) => {
            const href = resolveAnchorHref(n.href, pathname);
            const current = pathname !== '/' && pathname?.startsWith(n.href);
            return (
              <a
                key={n.key}
                href={href}
                aria-current={current ? 'page' : undefined}
                className={`whitespace-nowrap rounded-full px-3 py-2 text-sm font-semibold transition hover:bg-emerald-50 hover:text-ciForest focus-visible:outline focus-visible:outline-2 focus-visible:outline-ciForest ${
                  current ? 'text-ciForest' : 'text-slate-700'
                }`}
              >
                {t.nav[n.key]}
              </a>
            );
          })}
        </nav>

        <div className="hidden shrink-0 items-center gap-2 xl:flex">
          <LanguageSwitch />
          <Link
            href="/pass"
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-bold text-ciForest transition hover:border-ciForest focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest"
          >
            {t.nav.pass}
          </Link>
          <Link
            href="/voyageur"
            className="rounded-full bg-ciForest px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest"
          >
            {t.nav.register}
          </Link>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 xl:hidden">
          <LanguageSwitch />
          <button
            onClick={() => setOpen(!open)}
            aria-label={open ? t.nav.menuClose : t.nav.menuOpen}
            aria-expanded={open}
            aria-controls="public-mobile-menu"
            className="grid h-10 w-10 place-items-center rounded-full text-ciForest hover:bg-emerald-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ciForest"
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {open && (
        <div id="public-mobile-menu" className="max-h-[calc(100vh-4.25rem)] overflow-y-auto border-t border-slate-100 bg-white px-4 pb-6 pt-2 xl:hidden">
          <nav aria-label={t.nav.main} className="flex flex-col">
            {PUBLIC_NAV.map((n) => (
              <a
                key={n.key}
                href={resolveAnchorHref(n.href, pathname)}
                onClick={() => setOpen(false)}
                className="rounded-xl px-3 py-3 text-base font-semibold text-slate-800 hover:bg-emerald-50"
              >
                {t.nav[n.key]}
              </a>
            ))}
          </nav>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Link href="/pass" className="rounded-xl border border-slate-300 px-5 py-3 text-center font-bold text-ciForest">
              {t.nav.pass}
            </Link>
            <Link href="/voyageur" className="rounded-xl bg-ciForest px-5 py-3 text-center font-bold text-white">
              {t.nav.register}
            </Link>
          </div>
          <a href={adminUrl('/auth/login')} className="mt-4 block text-center text-xs text-slate-500 underline-offset-2 hover:underline">
            {t.nav.agent}
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
