'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/dashboard/Sidebar';
import { Topbar } from '@/components/dashboard/Topbar';
import { getAccess } from '@/lib/api';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const t = getAccess();
    if (!t) { router.replace('/auth/login'); return; }
    setReady(true);
  }, [router]);

  if (!ready) return <div className="min-h-screen grid place-items-center text-slate-400">Chargement…</div>;

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-slate-950">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title="EpiTrace — Administration" />
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">{children}</div>
      </div>
    </div>
  );
}
