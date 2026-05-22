'use client';

import { LogOut, Bell, ExternalLink, Menu } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { clearTokens } from '@/lib/api';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { publicUrl } from '@/lib/hosts';

export function Topbar({
  title,
  onMenuClick,
}: {
  title: string;
  onMenuClick?: () => void;
}) {
  const router = useRouter();
  const logout = () => {
    clearTokens();
    router.replace('/auth/login');
  };

  return (
    <header className="h-14 sm:h-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex items-center justify-between gap-2 px-3 sm:px-6 shrink-0">
      {/* Gauche : hamburger mobile + titre */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <button
          onClick={onMenuClick}
          aria-label="Ouvrir le menu"
          className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 shrink-0"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h1 className="font-display text-base sm:text-lg font-semibold truncate">{title}</h1>
      </div>

      {/* Droite : actions (compactes sur mobile) */}
      <div className="flex items-center gap-1 sm:gap-2 shrink-0">
        <a
          href={publicUrl('/')}
          target="_blank"
          rel="noreferrer"
          title="Portail public"
          aria-label="Portail public"
          className="inline-flex h-9 w-9 sm:w-auto sm:px-3 items-center justify-center gap-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-sm transition"
        >
          <ExternalLink className="h-4 w-4" />
          <span className="hidden sm:inline">Portail public</span>
        </a>
        <button
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <ThemeToggle />
        <button
          onClick={logout}
          title="Déconnexion"
          aria-label="Déconnexion"
          className="inline-flex h-9 w-9 sm:w-auto sm:px-3 items-center justify-center gap-2 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-sm transition"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Déconnexion</span>
        </button>
      </div>
    </header>
  );
}
