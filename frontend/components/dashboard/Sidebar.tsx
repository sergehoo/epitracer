'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity, Building2, BarChart3, Bell, ChevronLeft, FileText, FormInput,
  HeartPulse, LayoutDashboard, Map, MapPin, Network, QrCode, Settings,
  ShieldAlert, Siren, Stethoscope, Users,
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
  { href: '/cartographie',      label: 'Cartographie',      icon: Map },
  { href: '/maladies',          label: 'Maladies',          icon: Stethoscope },
  { href: '/formulaires',       label: 'Formulaires',       icon: FormInput },
  { href: '/utilisateurs',      label: 'Utilisateurs',      icon: Users },
  { href: '/visites',           label: 'Visites',           icon: BarChart3 },
  { href: '/rapports',          label: 'Rapports',          icon: FileText },
  { href: '/audit-logs',        label: 'Audit logs',        icon: ShieldAlert },
  { href: '/parametres',        label: 'Paramètres',        icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, toggle } = useSidebar();

  return (
    <aside
      className={cn(
        'hidden lg:flex shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex-col transition-[width] duration-200 ease-out',
        collapsed ? 'w-[72px]' : 'w-64',
      )}
    >
      {/* En-tête logos + brand */}
      <div
        className={cn(
          'flex items-center border-b border-slate-200 dark:border-slate-800 py-3',
          collapsed ? 'justify-center px-3' : 'gap-2 px-4',
        )}
      >
        {collapsed ? (
          <Link href="/dashboard" title="EpiTrace · MSHPCMU · INHP">
            <img src="/logo-min-sante-2.png" alt="MSHPCMU" className="h-9 w-9 object-contain" />
          </Link>
        ) : (
          <>
            <img src="/logo-min-sante-2.png" alt="MSHPCMU" className="h-9 w-9 object-contain" />
            <img src="/armoirie-ci-2.png" alt="Armoiries CI" className="h-9 w-9 object-contain" />
            <img src="/logo-INHP.png" alt="INHP" className="h-7 w-auto object-contain" />
            <Link href="/dashboard" className="ml-1 leading-tight">
              <div className="font-display font-black text-sm text-ciDark dark:text-emerald-200">
                EpiTrace CI
              </div>
              <div className="text-[10px] text-slate-500">MSHPCMU · INHP / admin</div>
            </Link>
          </>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname?.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={cn(
                'group flex items-center rounded-xl text-sm font-medium transition',
                collapsed
                  ? 'h-11 w-11 mx-auto justify-center'
                  : 'gap-3 px-3 py-2',
                active
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-200/60 dark:ring-emerald-900/60'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900',
              )}
            >
              <Icon className={cn('h-4 w-4 shrink-0', active && 'text-emerald-600 dark:text-emerald-300')} />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Pied : bouton de bascule + version */}
      <div className="border-t border-slate-200 dark:border-slate-800 p-2 space-y-2">
        <button
          onClick={toggle}
          aria-label={collapsed ? 'Déployer la barre' : 'Réduire la barre'}
          title={collapsed ? 'Déployer' : 'Réduire'}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-ciDark hover:border-ciOrange/50 dark:hover:text-emerald-300 transition py-2"
        >
          <ChevronLeft className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')} />
          {!collapsed && <span className="text-xs font-semibold">Réduire</span>}
        </button>
        {!collapsed && (
          <div className="text-[10px] text-slate-400 text-center">
            v0.1.0 · MSHPCMU · INHP
          </div>
        )}
      </div>
    </aside>
  );
}
