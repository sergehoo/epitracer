'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { QrCode } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * MobileScanFab — Bouton flottant d'accès rapide au scanner QR.
 *
 * Visible UNIQUEMENT sur mobile / tablette portrait (< lg). Caché sur
 * /verifier (où le scanner est déjà la page principale). Conçu pour les
 * agents sur le terrain qui veulent vérifier un pass voyageur sans
 * naviguer dans le menu.
 *
 * Position : bas-droite, au-dessus de la zone clavier safe-area iOS.
 */
export function MobileScanFab() {
  const pathname = usePathname();
  // Ne pas afficher sur la page scanner elle-même
  if (pathname?.startsWith('/verifier')) return null;

  return (
    <Link
      href="/verifier"
      aria-label="Scanner un pass voyageur"
      title="Scanner un pass"
      className={cn(
        // Mobile seulement
        'lg:hidden fixed z-30',
        // Position : bas-droite avec safe-area iOS
        'bottom-5 right-5',
        // Style FAB
        'inline-flex h-14 w-14 items-center justify-center rounded-full',
        'bg-ciOrange text-white shadow-lg shadow-orange-500/40',
        'hover:scale-105 active:scale-95 transition-transform',
        // Anneau pour visibilité fond sombre
        'ring-4 ring-white/80 dark:ring-slate-900/80',
      )}
      style={{
        // Respect du notch / barre d'accueil iOS
        bottom: 'max(1.25rem, env(safe-area-inset-bottom))',
        right: 'max(1.25rem, env(safe-area-inset-right))',
      }}
    >
      <QrCode className="h-6 w-6" strokeWidth={2.5} />
    </Link>
  );
}
