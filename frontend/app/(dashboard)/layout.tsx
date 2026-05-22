'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Sidebar } from '@/components/dashboard/Sidebar';
import { Topbar } from '@/components/dashboard/Topbar';
import { BottomNav } from '@/components/dashboard/BottomNav';
import { getAccess } from '@/lib/api';
import { useRealtimeAlerts } from '@/lib/useRealtimeAlerts';
import { useEdgeSwipe } from '@/lib/useEdgeSwipe';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Branchement WebSocket temps réel — affiche un toast à chaque nouvelle
  // HealthAlert reçue (cliquable vers /alertes).
  useRealtimeAlerts();

  // Edge-swipe : swipe right depuis le bord gauche → ouvre drawer.
  // Swipe left sur drawer ouvert → ferme. Désactivé quand drawer déjà ouvert
  // (sauf swipe left qui ferme).
  useEdgeSwipe({
    onSwipeRight: () => !mobileNavOpen && setMobileNavOpen(true),
    onSwipeLeft: () => mobileNavOpen && setMobileNavOpen(false),
    enabled: true,
  });

  useEffect(() => {
    const t = getAccess();
    if (!t) { router.replace('/auth/login'); return; }
    setReady(true);
  }, [router]);

  // Ferme automatiquement le drawer mobile au changement de page
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
        {/* pb-24 mobile pour laisser de la place à la BottomNav (≈ 64px + safe-area) */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 lg:p-8 pb-24 lg:pb-8">
          {children}
        </div>
      </div>

      {/* Bottom navigation mobile : 5 onglets avec scanner central surélevé.
          Remplace l'ancien MobileScanFab. */}
      <BottomNav onMenuClick={() => setMobileNavOpen(true)} />
    </div>
  );
}
