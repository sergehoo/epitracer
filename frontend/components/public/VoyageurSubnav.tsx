'use client';

/**
 * Sous-navigation des pages de l'Espace Voyageur.
 *
 * Affiche un fil d'ariane + onglets pour naviguer facilement entre :
 *  - Accueil (retour à la landing /)
 *  - Mon pass (/pass ou /pass/<id> si on a l'ID)
 *  - Suivi quotidien (/voyageur/suivi)
 *  - Mes données (/voyageur/mes-donnees)
 *  - Politique (/voyageur/confidentialite)
 *
 * Si un `publicId` est passé en prop (souvent dispo via query / store),
 * les liens internes le propagent automatiquement pour éviter à
 * l'utilisateur de retaper son identifiant.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bell, HeartHandshake, Home, Lock, QrCode, ShieldCheck } from 'lucide-react';

interface Item {
  href: string;
  label: string;
  icon: React.ReactNode;
  match: (path: string | null) => boolean;
}

export function VoyageurSubnav({ publicId }: { publicId?: string }) {
  const pathname = usePathname();
  const idQuery = publicId ? `?id=${publicId}` : '';

  const items: Item[] = [
    {
      href: '/',
      label: 'Accueil',
      icon: <Home className="h-4 w-4" />,
      match: (p) => p === '/',
    },
    {
      href: publicId ? `/pass/${publicId}` : '/pass',
      label: 'Mon pass',
      icon: <QrCode className="h-4 w-4" />,
      match: (p) => Boolean(p && (p === '/pass' || p.startsWith('/pass/'))),
    },
    {
      href: `/voyageur/suivi${idQuery}`,
      label: 'Suivi',
      icon: <HeartHandshake className="h-4 w-4" />,
      match: (p) => p === '/voyageur/suivi',
    },
    {
      href: `/voyageur/mes-donnees${idQuery}`,
      label: 'Mes données',
      icon: <Lock className="h-4 w-4" />,
      match: (p) => p === '/voyageur/mes-donnees',
    },
    {
      href: '/voyageur/confidentialite',
      label: 'Politique',
      icon: <ShieldCheck className="h-4 w-4" />,
      match: (p) => p === '/voyageur/confidentialite',
    },
  ];

  return (
    <nav
      aria-label="Navigation espace voyageur"
      className="mb-6 -mx-2 overflow-x-auto"
    >
      <ul className="flex items-center gap-1 px-2 min-w-max">
        {items.map((it) => {
          const active = it.match(pathname);
          return (
            <li key={it.href}>
              <Link
                href={it.href}
                className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-xs sm:text-sm font-semibold whitespace-nowrap transition ${
                  active
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'bg-white text-slate-600 border border-slate-200 hover:border-ciOrange hover:text-ciOrange dark:bg-slate-900 dark:text-slate-300 dark:border-slate-800'
                }`}
              >
                {it.icon}
                {it.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
