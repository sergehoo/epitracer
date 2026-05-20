'use client';

import { LogOut, Bell, ExternalLink } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { clearTokens } from '@/lib/api';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { publicUrl } from '@/lib/hosts';

export function Topbar({ title }: { title: string }) {
  const router = useRouter();
  const logout = () => {
    clearTokens();
    router.replace('/auth/login');
  };
  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex items-center justify-between px-6">
      <h1 className="font-display text-lg font-semibold">{title}</h1>
      <div className="flex items-center gap-2">
        <a href={publicUrl('/')} target="_blank" rel="noreferrer" className="btn-ghost text-sm" title="Portail public">
          <ExternalLink className="h-4 w-4" /> Portail public
        </a>
        <button className="btn-ghost" aria-label="Notifications"><Bell className="h-4 w-4" /></button>
        <ThemeToggle />
        <button onClick={logout} className="btn-outline text-sm">
          <LogOut className="h-4 w-4" /> Déconnexion
        </button>
      </div>
    </header>
  );
}
