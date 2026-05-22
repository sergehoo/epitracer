'use client';

/**
 * Itinéraire d'un voyageur — affichage des pings de localisation
 * sur une carte Leaflet + timeline.
 *
 * Accès restreint (RBAC côté API). Chaque consultation est journalisée
 * dans DataAccessLog côté serveur.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import { ArrowLeft, Clock, Compass, MapPin } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

const Map = dynamic(() => import('./map'), { ssr: false });

interface Ping {
  uuid: string;
  latitude: number;
  longitude: number;
  accuracy_m: number | null;
  event_type: string;
  source: string;
  captured_at: string;
}

interface LocationsPayload {
  traveler: { public_id: string; full_name: string };
  count: number;
  pings: Ping[];
}

const EVENT_LABELS: Record<string, string> = {
  daily_checkin: 'Check-in quotidien',
  symptom_report: 'Signalement de symptôme',
  assistance_request: 'Demande d\'assistance',
  manual_share: 'Partage volontaire',
  agent_visit: 'Visite d\'un agent terrain',
};

export default function ItinerairePage() {
  const params = useParams<{ publicId: string }>();
  const publicId = params?.publicId || '';
  const [data, setData] = useState<LocationsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState<string>('Consultation suivi');

  const load = useCallback(async () => {
    if (!publicId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<LocationsPayload>(
        `/admin/companion/travelers/${publicId}/locations/`,
        { params: { reason } },
      );
      setData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  }, [publicId, reason]);

  useEffect(() => { load(); }, [load]);

  const sortedPings = useMemo(
    () => [...(data?.pings || [])].sort((a, b) => a.captured_at.localeCompare(b.captured_at)),
    [data],
  );

  return (
    <div className="space-y-6">
      <header>
        <Link href="/suivi-voyageurs" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange">
          <ArrowLeft className="h-3 w-3" /> Retour au tableau
        </Link>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-2">
          Itinéraire — {data?.traveler.full_name || publicId}
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {data?.count ?? 0} positions enregistrées (consentement explicite du voyageur).
          Toute consultation est journalisée.
        </p>
      </header>

      {/* Motif de consultation (audit) */}
      <div className="card p-3 flex items-center gap-3 text-sm">
        <span className="text-slate-500">Motif de consultation :</span>
        <input
          className="input flex-1 max-w-md"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="ex : Investigation alerte HA-1234"
        />
        <button onClick={load} className="btn-paper text-xs" type="button">
          Actualiser
        </button>
      </div>

      {loading && <div className="card p-10 animate-pulse h-64" />}
      {!loading && error && <div className="card p-6 text-rose-600">{error}</div>}

      {!loading && data && data.count === 0 && (
        <div className="card p-10 text-center text-slate-500">
          Ce voyageur n'a partagé aucune position depuis le début de son suivi.
        </div>
      )}

      {!loading && data && data.count > 0 && (
        <div className="grid lg:grid-cols-[1fr,380px] gap-6">
          {/* Carte */}
          <div className="card overflow-hidden h-[600px] relative">
            <Map pings={sortedPings} />
          </div>

          {/* Timeline */}
          <aside className="card p-5 max-h-[600px] overflow-y-auto">
            <div className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-600" /> Chronologie
            </div>
            <ol className="space-y-3">
              {[...sortedPings].reverse().map((p, idx) => (
                <li key={p.uuid} className="border-l-2 border-emerald-300 pl-3 pb-3 relative">
                  <span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full bg-emerald-500" />
                  <div className="text-xs text-slate-500">{formatDateTime(p.captured_at)}</div>
                  <div className="text-sm font-semibold">{EVENT_LABELS[p.event_type] || p.event_type}</div>
                  <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                    <MapPin className="h-3 w-3" />
                    {p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}
                    {p.accuracy_m && <> · ±{Math.round(p.accuracy_m)}m</>}
                  </div>
                  {idx === 0 && (
                    <span className="inline-flex items-center gap-1 text-[10px] uppercase font-bold text-emerald-700 mt-1">
                      <Compass className="h-3 w-3" /> Dernière position connue
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </aside>
        </div>
      )}
    </div>
  );
}
