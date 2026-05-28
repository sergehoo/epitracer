'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity, Building2, BarChart3, Bell, ChevronLeft, FileText, FormInput,
  HeartPulse, LayoutDashboard, Map, MapPin, MessageSquare, Network, QrCode,
  Settings, ShieldAlert, Siren, Stethoscope, Users, X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/lib/sidebarStore';

const NAV = [
  { href: '/dashboard',         label: 'Dashboard',         icon: LayoutDashboard },
  { href: '/surveillance',      label: 'Surveillance',      icon: Activity },
  { href: '/suivi-voyageurs',   label: 'Suivi voyageurs',   icon: HeartPulse },
  { href: '/checkins',          label: 'Check-ins',         icon: Bell },
  { href: '/verifier',          label: 'Vérifier un pass',  icon: QrCode },
  { href: '/relations',         label: 'Relations',         icon: Network },
  { href: '/points-entree',     label: "Points d'entrée",   icon: MapPin },
  { href: '/districts',         label: 'Districts',         icon: Building2 },
  { href: '/alertes',           label: 'Alertes',           icon: Siren },
  { href: '/notifications',     label: 'Notifications',     icon: MessageSquare },
  { href: '/cartographie',      label: 'Cartographie',      icon: Map },
  { href: '/maladies',          label: 'Maladies',          icon: Stethoscope },
  { href: '/formulaires',       label: 'Formulaires',       icon: FormInput },
  { href: '/utilisateurs',      label: 'Utilisateurs',      icon: Users },
  { href: '/visites',           label: 'Visites',           icon: BarChart3 },
  { href: '/rapports',          label: 'Rapports',          icon: FileText },
  { href: '/audit-logs',        label: 'Audit logs',        icon: ShieldAlert },
  { href: '/parametres',        label: 'Paramètres',        icon: Settings },
];

/**
 * Sidebar — supporte 2 modes :
 *  - Desktop (≥ lg) : sidebar fixe, collapse togglable via le bouton du pied.
 *  - Mobile (< lg)  : drawer overlay piloté par `mobileOpen` / `onMobileClose`
 *                     (déclenché depuis la Topbar hamburger).
 */
export function Sidebar({
  mobileOpen = false,
  onMobileClose,
}: {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}) {
  const pathname = usePathname();
  const { collapsed, toggle } = useSidebar();

  const closeOnNav = () => {
    if (mobileOpen) onMobileClose?.();
  };

  return (
    <>
      {/* Overlay mobile (fond sombre cliquable pour fermer) */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          // Position : drawer fixe sur mobile, intégré au flux en desktop
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 transition-transform duration-200 ease-out',
          // Largeur mobile = 280px fixe
          'w-[280px]',
          // Animation drawer
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          // Desktop : passe en flex normal, largeur selon collapsed
          'lg:static lg:translate-x-0 lg:transition-[width] lg:flex lg:shrink-0',
          collapsed ? 'lg:w-[72px]' : 'lg:w-64',
        )}
      >
        {/* En-tête logos + brand + bouton close mobile */}
        <div
          className={cn(
            'flex items-center border-b border-slate-200 dark:border-slate-800 py-3 shrink-0',
            collapsed ? 'lg:justify-center lg:px-3' : 'gap-2 px-4',
          )}
        >
          {collapsed ? (
            <Link href="/dashboard" title="EpiTrace · MSHPCMU · INHP" onClick={closeOnNav} className="lg:block hidden">
              <img src="/logo-min-sante-2.png" alt="MSHPCMU" className="h-9 w-9 object-contain" />
            </Link>
          ) : null}
          {/* Logo + brand en mode déployé OU mobile */}
          <div className={cn('flex items-center gap-2 flex-1', collapsed ? 'lg:hidden' : '')}>
            <img src="/logo-min-sante-2.png" alt="MSHPCMU" className="h-9 w-9 object-contain" />
            <Link href="/dashboard" onClick={closeOnNav} className="leading-tight">
              <div className="font-display font-black text-sm text-ciDark dark:text-emerald-200">
                EpiTrace CI
              </div>
              <div className="text-[10px] text-slate-500">MSHPCMU · INHP / admin</div>
            </Link>
          </div>
          {/* Bouton fermer (mobile uniquement) */}
          <button
            onClick={onMobileClose}
            className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Fermer le menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-2 space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname?.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={closeOnNav}
                title={collapsed ? label : undefined}
                className={cn(
                  'group flex items-center rounded-xl text-sm font-medium transition',
                  collapsed
                    ? 'lg:h-11 lg:w-11 lg:mx-auto lg:justify-center gap-3 px-3 py-2'
                    : 'gap-3 px-3 py-2',
                  active
                    ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-200/60 dark:ring-emerald-900/60'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900',
                )}
              >
                <Icon className={cn('h-4 w-4 shrink-0', active && 'text-emerald-600 dark:text-emerald-300')} />
                {/* Label : toujours visible mobile, conditionnel desktop */}
                <span className={cn('truncate', collapsed && 'lg:hidden')}>{label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Pied : bouton de bascule (desktop uniquement) + version */}
        <div className="border-t border-slate-200 dark:border-slate-800 p-2 space-y-2 shrink-0">
          <button
            onClick={toggle}
            aria-label={collapsed ? 'Déployer la barre' : 'Réduire la barre'}
            title={collapsed ? 'Déployer' : 'Réduire'}
            className="hidden lg:inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-ciDark hover:border-ciOrange/50 dark:hover:text-emerald-300 transition py-2"
          >
            <ChevronLeft className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')} />
            {!collapsed && <span className="text-xs font-semibold">Réduire</span>}
          </button>
          <div className={cn('text-[10px] text-slate-400 text-center', collapsed && 'lg:hidden')}>
            v0.1.0 · MSHPCMU · INHP
          </div>
        </div>
      </aside>
    </>
  );
}
