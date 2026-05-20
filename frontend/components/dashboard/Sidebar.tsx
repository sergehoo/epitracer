'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity, AlertTriangle, Building2, FormInput, LayoutDashboard, Map, MapPin,
  ShieldCheck, Siren, Stethoscope, Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/surveillance', label: 'Surveillance', icon: Activity },
  { href: '/points-entree', label: 'Points d\'entrée', icon: MapPin },
  { href: '/districts', label: 'Districts', icon: Building2 },
  { href: '/alertes', label: 'Alertes', icon: Siren },
  { href: '/cartographie', label: 'Cartographie', icon: Map },
  { href: '/maladies', label: 'Maladies', icon: Stethoscope },
  { href: '/formulaires', label: 'Formulaires', icon: FormInput },
  { href: '/utilisateurs', label: 'Utilisateurs', icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden lg:flex w-64 shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex-col">
      <div className="h-16 flex items-center gap-2 px-5 border-b border-slate-200 dark:border-slate-800">
        <div className="h-9 w-9 rounded-xl bg-emerald-600 grid place-items-center text-white shadow-glow">
          <ShieldCheck className="h-4 w-4" />
        </div>
        <Link href="/dashboard" className="font-display font-bold">EpiTravel <span className="text-xs font-medium text-slate-500">/ admin</span></Link>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname?.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition',
                active
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900',
              )}
            >
              <Icon className="h-4 w-4" /> {label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-500">
        v0.1.0 · MINSAN · INHP
      </div>
    </aside>
  );
}
