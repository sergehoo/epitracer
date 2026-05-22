'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Sidebar } from '@/components/dashboard/Sidebar';
import { Topbar } from '@/components/dashboard/Topbar';
import { MobileScanFab } from '@/components/dashboard/MobileScanFab';
import { getAccess } from '@/lib/api';
import { useRealtimeAlerts } from '@/lib/useRealtimeAlerts';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Branchement WebSocket temps réel — affiche un toast à chaque nouvelle
  // HealthAlert reçue (cliquable vers /alertes). Best-effort, ne casse
  // pas l'app si le WS est indispo.
  useRealtimeAlerts();

  useEffect(() => {
    const t = getAccess();
    if (!t) { router.replace('/auth/login'); return; }
    setReady(true);
  }, [router]);

  // Ferme automatiquement le drawer mobile quand l'utilisateur change de page
  // (sécurité : si le clic sur un lien Sidebar ne déclenche pas onMobileClose,
  // le pathname change quand même → on referme ici).
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  // Bloque le scroll body quand le drawer mobile est ouvert
  useEffect(() => {
    if (mobileNavOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [mobileNavOpen]);

  if (!ready) return <div className="min-h-screen grid place-items-center text-slate-400">Chargement…</div>;

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-slate-950">
      <Sidebar
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          title="EpiTrace — Administration"
          onMenuClick={() => setMobileNavOpen(true)}
        />
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 lg:p-8">
          {children}
        </div>
      </div>

      {/* Bouton flottant Scanner QR (mobile uniquement, caché sur /verifier) */}
      <MobileScanFab />
    </div>
  );
}
