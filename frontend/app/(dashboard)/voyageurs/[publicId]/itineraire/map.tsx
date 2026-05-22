'use client';

/**
 * Carte Leaflet pour l'itinéraire d'un voyageur.
 *
 * Sépare le composant Leaflet du parent pour permettre le chargement
 * dynamique (`ssr: false`) — Leaflet n'est pas SSR-compatible.
 */

import { useEffect, useMemo } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';

interface Ping {
  uuid: string;
  latitude: number;
  longitude: number;
  accuracy_m: number | null;
  event_type: string;
  source: string;
  captured_at: string;
}

const EVENT_COLOR: Record<string, string> = {
  daily_checkin: '#10b981',
  symptom_report: '#f59e0b',
  assistance_request: '#e11d48',
  manual_share: '#3b82f6',
  agent_visit: '#8b5cf6',
};

function colorIcon(color: string) {
  // Marker SVG ronde colorée (sans dépendance à un asset externe)
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="9" fill="${color}" stroke="white" stroke-width="3"/>
  </svg>`;
  return L.divIcon({
    className: '',
    html: svg,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

function FitToBounds({ pings }: { pings: Ping[] }) {
  const map = useMap();
  useEffect(() => {
    if (pings.length === 0) return;
    const bounds = L.latLngBounds(pings.map((p) => [p.latitude, p.longitude] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }, [pings, map]);
  return null;
}

export default function ItineraireMap({ pings }: { pings: Ping[] }) {
  const path = useMemo(
    () => pings.map((p) => [p.latitude, p.longitude] as [number, number]),
    [pings],
  );
  const center: [number, number] = pings.length
    ? [pings[pings.length - 1].latitude, pings[pings.length - 1].longitude]
    : [5.345, -4.024]; // Abidjan par défaut

  return (
    <MapContainer
      center={center}
      zoom={12}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToBounds pings={pings} />

      {/* Tracé chronologique */}
      {path.length > 1 && (
        <Polyline positions={path} pathOptions={{ color: '#10b981', weight: 3, opacity: 0.6 }} />
      )}

      {/* Markers par ping */}
      {pings.map((p, idx) => {
        const isLast = idx === pings.length - 1;
        const color = isLast ? '#e11d48' : EVENT_COLOR[p.event_type] || '#64748b';
        return (
          <Marker key={p.uuid} position={[p.latitude, p.longitude]} icon={colorIcon(color)}>
            <Popup>
              <div className="text-xs">
                <strong>{new Date(p.captured_at).toLocaleString('fr-FR')}</strong>
                <div className="mt-1">{p.event_type}</div>
                <div className="text-slate-500">
                  {p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}
                </div>
                {p.accuracy_m && (
                  <div className="text-slate-500">Précision : ±{Math.round(p.accuracy_m)} m</div>
                )}
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
