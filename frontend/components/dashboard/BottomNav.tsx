'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, Bell, HeartPulse, Menu, QrCode } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * BottomNav — Barre de navigation mobile style application native.
 *
 * 5 zones :
 *   [Dashboard] [Voyageurs] [⭕ SCAN ⭕] [Alertes] [Menu]
 *
 * Le 3e onglet (Scan) est un FAB central surélevé en orange CI — il
 * remplace l'ancien MobileScanFab et donne un point d'accès dominant
 * au scanner QR pour les agents sur le terrain.
 *
 * L'onglet Menu ouvre le drawer de la Sidebar (callback `onMenuClick`).
 *
 * Visible uniquement < lg. Respecte la safe-area iOS (bord bas du notch).
 */
export function BottomNav({ onMenuClick }: { onMenuClick?: () => void }) {
  const pathname = usePathname();
  const isActive = (href: string) => pathname?.startsWith(href);

  return (
    <nav
      className={cn(
        'lg:hidden fixed inset-x-0 bottom-0 z-30',
        'bg-white/95 dark:bg-slate-950/95 backdrop-blur',
        'border-t border-slate-200 dark:border-slate-800',
        'flex items-stretch justify-around',
        'h-16',
      )}
      style={{
        paddingBottom: 'env(safe-area-inset-bottom)',
        // Augmente la hauteur sur appareils à safe-area (iPhone notch)
        height: 'calc(4rem + env(safe-area-inset-bottom))',
      }}
    >
      <NavItem
        href="/dashboard"
        label="Accueil"
        icon={<Activity className="h-5 w-5" />}
        active={isActive('/dashboard')}
      />
      <NavItem
        href="/suivi-voyageurs"
        label="Voyageurs"
        icon={<HeartPulse className="h-5 w-5" />}
        active={isActive('/suivi-voyageurs') || isActive('/voyageurs') || isActive('/checkins')}
      />

      {/* Bouton SCAN central — FAB intégré dans la nav, légèrement surélevé */}
      <Link
        href="/verifier"
        aria-label="Scanner un pass voyageur"
        className="relative flex flex-col items-center justify-end pb-1 pt-3 min-w-[64px]"
      >
        <span
          className={cn(
            'absolute -top-4 inline-flex h-14 w-14 items-center justify-center rounded-full',
            'shadow-lg transition-transform active:scale-95',
            isActive('/verifier')
              ? 'bg-emerald-600 text-white shadow-emerald-500/40'
              : 'bg-ciOrange text-white shadow-orange-500/40',
            'ring-4 ring-white dark:ring-slate-950',
          )}
        >
          <QrCode className="h-6 w-6" strokeWidth={2.5} />
        </span>
        <span className="text-[10px] font-semibold mt-9 text-slate-600 dark:text-slate-300">
          Scanner
        </span>
      </Link>

      <NavItem
        href="/alertes"
        label="Alertes"
        icon={<Bell className="h-5 w-5" />}
        active={isActive('/alertes')}
      />

      {/* Menu : bouton (pas un Link) qui ouvre la sidebar drawer */}
      <button
        type="button"
        onClick={onMenuClick}
        aria-label="Ouvrir le menu"
        className="flex flex-col items-center justify-center gap-0.5 min-w-[64px] text-slate-500 dark:text-slate-400 active:bg-slate-100 dark:active:bg-slate-900 transition"
      >
        <Menu className="h-5 w-5" />
        <span className="text-[10px] font-semibold">Menu</span>
      </button>
    </nav>
  );
}

function NavItem({
  href, label, icon, active,
}: {
  href: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        'flex flex-col items-center justify-center gap-0.5 min-w-[64px] transition',
        active
          ? 'text-emerald-600 dark:text-emerald-400'
          : 'text-slate-500 dark:text-slate-400 active:bg-slate-100 dark:active:bg-slate-900',
      )}
    >
      <span className={cn(active && 'scale-110 transition-transform')}>{icon}</span>
      <span className="text-[10px] font-semibold">{label}</span>
    </Link>
  );
}
