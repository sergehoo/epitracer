'use client';

/**
 * LocationPanel — Phase 9F.
 *
 * Affiche la dernière position du voyageur + l'historique sur demande
 * (modal de raison RGPD obligatoire avant la consultation du détail).
 *
 * Pour la carte, on tente un import dynamique de react-leaflet — si la
 * librairie échoue (ou si on est dans un contexte SSR), on retombe sur un
 * affichage des coordonnées + un lien Google Maps.
 *
 * Props :
 *   - travelerId : id ou public_id du voyageur
 *   - lastPing : { latitude, longitude, captured_at } (peut être null)
 *   - geolocationAlertAt : date ISO d'une alerte récente (<48h => bandeau rouge)
 */

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  MapPin, AlertTriangle, Clock, ExternalLink, Loader2, History, X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

interface LastPing {
  latitude?: number;
  longitude?: number;
  lat?: number;
  lon?: number;
  captured_at?: string;
}

interface HistoryPing {
  id: number;
  latitude: number;
  longitude: number;
  accuracy_m: number | null;
  event_type: string;
  captured_at: string;
  consent_version?: string;
}

interface Props {
  travelerId: string;
  lastPing: LastPing | null;
  geolocationAlertAt: string | null;
}

// react-leaflet est ESM-only — import dynamique côté client uniquement.
const MapContainer = dynamic(
  () => import('react-leaflet').then((m) => m.MapContainer),
  { ssr: false },
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((m) => m.TileLayer),
  { ssr: false },
);
const Marker = dynamic(
  () => import('react-leaflet').then((m) => m.Marker),
  { ssr: false },
);
const Popup = dynamic(
  () => import('react-leaflet').then((m) => m.Popup),
  { ssr: false },
);

function pickLatLng(p: LastPing | null): { lat: number; lng: number } | null {
  if (!p) return null;
  const lat = p.latitude ?? p.lat;
  const lng = p.longitude ?? p.lon;
  if (typeof lat !== 'number' || typeof lng !== 'number') return null;
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;
  return { lat, lng };
}

function formatRelative(iso?: string | null): string {
  if (!iso) return '—';
  try {
    const ms = Date.now() - new Date(iso).getTime();
    if (ms < 0) return '—';
    const minutes = Math.floor(ms / 60_000);
    if (minutes < 60) return `Il y a ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
      const remainMin = minutes - hours * 60;
      return remainMin > 0 ? `Il y a ${hours}h ${remainMin}m` : `Il y a ${hours}h`;
    }
    const days = Math.floor(hours / 24);
    const remainH = hours - days * 24;
    return remainH > 0 ? `Il y a ${days}j ${remainH}h` : `Il y a ${days}j`;
  } catch {
    return iso;
  }
}

function haversineMeters(
  a: { lat: number; lng: number }, b: { lat: number; lng: number },
): number {
  const toRad = (n: number) => (n * Math.PI) / 180;
  const R = 6_371_000;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(s)));
}

export function LocationPanel({ travelerId, lastPing, geolocationAlertAt }: Props) {
  const latlng = useMemo(() => pickLatLng(lastPing), [lastPing]);

  // Bandeau d'alerte si geolocation_alert_raised_at < 48h
  const recentAlert = useMemo(() => {
    if (!geolocationAlertAt) return false;
    try {
      const ageH = (Date.now() - new Date(geolocationAlertAt).getTime()) / 3_600_000;
      return ageH < 48;
    } catch {
      return false;
    }
  }, [geolocationAlertAt]);

  // Historique : ouverture d'une modale "raison" avant fetch
  const [askReasonOpen, setAskReasonOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [pings, setPings] = useState<HistoryPing[] | null>(null);

  // Patch icônes Leaflet (problème connu en bundlers — chemins relatifs cassés).
  useEffect(() => {
    if (typeof window === 'undefined') return;
    (async () => {
      try {
        const L = await import('leaflet');
        // @ts-expect-error — _getIconUrl est privé
        delete L.Icon.Default.prototype._getIconUrl;
        L.Icon.Default.mergeOptions({
          iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
          iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
          shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        });
      } catch {
        /* leaflet absent : on retombera sur le fallback */
      }
    })();
  }, []);

  const fetchHistory = async () => {
    const r = (reason || '').trim();
    if (!r) {
      toast.error('Une raison est requise (RGPD).');
      return;
    }
    setHistoryLoading(true);
    try {
      const resp = await api.get<{ results: HistoryPing[] }>(
        `/admin/followups/${travelerId}/location-history/`,
        { params: { reason: r } },
      );
      setPings(resp.data?.results ?? []);
      setAskReasonOpen(false);
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setHistoryLoading(false);
    }
  };

  // Décore l'historique avec distance entre points consécutifs.
  const decoratedPings = useMemo(() => {
    if (!pings) return [];
    return pings.map((p, idx) => {
      const next = pings[idx + 1];
      let distance: number | null = null;
      if (next) {
        distance = haversineMeters(
          { lat: p.latitude, lng: p.longitude },
          { lat: next.latitude, lng: next.longitude },
        );
      }
      return { ...p, distance };
    });
  }, [pings]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-sky-600" />
            <h2 className="font-display text-lg font-black text-ciDark">Géolocalisation</h2>
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Dernière position connue + historique sécurisé (motif RGPD obligatoire).
          </div>
        </div>
        <button
          type="button"
          onClick={() => { setReason('Investigation suivi médical'); setAskReasonOpen(true); }}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
        >
          <History className="h-3.5 w-3.5" /> Voir l'historique
        </button>
      </header>

      {recentAlert && geolocationAlertAt && (
        <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            <strong>Géolocalisation absente</strong> — alerte déclenchée le{' '}
            {new Date(geolocationAlertAt).toLocaleString('fr-FR')}. Une équipe
            de district peut être envoyée pour vérification.
          </div>
        </div>
      )}

      {/* Carte ou fallback */}
      {latlng ? (
        <div className="rounded-xl overflow-hidden border border-slate-200">
          <div style={{ height: 260, width: '100%' }}>
            {/* @ts-expect-error — typage react-leaflet via dynamic */}
            <MapContainer
              center={[latlng.lat, latlng.lng]}
              zoom={13}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom={false}
            >
              {/* @ts-expect-error — typage react-leaflet via dynamic */}
              <TileLayer
                attribution="&copy; OpenStreetMap"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {/* @ts-expect-error — typage react-leaflet via dynamic */}
              <Marker position={[latlng.lat, latlng.lng]}>
                {/* @ts-expect-error — typage react-leaflet via dynamic */}
                <Popup>
                  Dernière position<br />
                  {formatRelative(lastPing?.captured_at)}
                </Popup>
              </Marker>
            </MapContainer>
          </div>
          <div className="px-3 py-2 bg-slate-50 text-[11px] text-slate-600 flex items-center justify-between flex-wrap gap-2">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" /> {formatRelative(lastPing?.captured_at)}
              {lastPing?.captured_at && (
                <span className="text-slate-400 ml-1">
                  ({new Date(lastPing.captured_at).toLocaleString('fr-FR')})
                </span>
              )}
            </span>
            <a
              href={`https://www.google.com/maps?q=${latlng.lat},${latlng.lng}`}
              target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-1 font-bold text-sky-700 hover:underline"
            >
              Ouvrir dans Google Maps <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
          <MapPin className="h-5 w-5 mx-auto text-slate-300 mb-1.5" />
          Aucune position géolocalisée disponible pour ce voyageur.
        </div>
      )}

      {/* Liste historique (après fetch) */}
      {pings !== null && (
        <div className="mt-5">
          <div className="text-xs uppercase font-bold tracking-wide text-slate-500 mb-2">
            Historique récent ({pings.length}) — 10 derniers pings
          </div>
          {pings.length === 0 ? (
            <div className="text-xs text-slate-400 py-2">
              Aucun ping enregistré sur la fenêtre consultée.
            </div>
          ) : (
            <ul className="space-y-1.5">
              {decoratedPings.slice(0, 10).map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-slate-50 text-[11px] text-slate-600"
                >
                  <span className="font-mono tabular-nums">
                    {p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}
                  </span>
                  <span className="text-slate-500">
                    {p.accuracy_m != null && (
                      <span className="mr-3">± {p.accuracy_m} m</span>
                    )}
                    {p.distance != null && (
                      <span className="mr-3 text-slate-400">
                        Δ {p.distance >= 1000 ? `${(p.distance / 1000).toFixed(1)} km` : `${p.distance} m`}
                      </span>
                    )}
                    {formatRelative(p.captured_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Modale "raison" */}
      {askReasonOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto"
          onClick={() => setAskReasonOpen(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl w-full max-w-md mt-20"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <h3 className="font-display text-base font-bold flex items-center gap-2">
                <History className="h-4 w-4 text-sky-600" /> Motif de consultation
              </h3>
              <button
                type="button"
                onClick={() => setAskReasonOpen(false)}
                aria-label="Fermer"
                className="text-slate-400 hover:text-slate-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 space-y-3">
              <p className="text-xs text-slate-500">
                Le motif est obligatoire (RGPD). Il sera enregistré dans le
                journal d'accès du voyageur.
              </p>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                maxLength={200}
                placeholder="Ex. Investigation alerte HA-1234"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-sky-500 focus:ring-sky-500 outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 px-5 py-4 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setAskReasonOpen(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={fetchHistory}
                disabled={historyLoading || !reason.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-sky-600 text-white px-4 py-2 text-sm font-bold hover:bg-sky-700 disabled:opacity-50"
              >
                {historyLoading ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Chargement…</>
                ) : (
                  'Charger l\'historique'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default LocationPanel;
