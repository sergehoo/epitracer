'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { api, extractApiError } from '@/lib/api';

const MapView = dynamic(() => import('@/components/dashboard/MapView').then((m) => m.MapView), {
  ssr: false,
  loading: () => <div className="card p-10 animate-pulse h-[60vh]" />,
});

interface HeatPoint { lat: number; lng: number; status: string }

export default function CartoPage() {
  const [points, setPoints] = useState<HeatPoint[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get('/analytics/heatmap/')
      .then((r) => setPoints(r.data || []))
      .catch((e) => setErr(extractApiError(e)));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs uppercase tracking-widest text-emerald-700 dark:text-emerald-400 font-semibold">Cartographie</div>
        <h1 className="font-display text-3xl font-bold mt-1">Répartition des voyageurs</h1>
        <p className="text-sm text-slate-500 mt-1">Géolocalisation des lieux de confinement déclarés.</p>
      </div>
      {err && <div className="card p-6 text-rose-600">{err}</div>}
      <MapView points={points} />
    </div>
  );
}
