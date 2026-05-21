'use client';

import 'leaflet/dist/leaflet.css';
import { useEffect, useMemo } from 'react';
import {
  CircleMarker, MapContainer, Marker, Popup, ScaleControl,
  TileLayer, Tooltip, useMap,
} from 'react-leaflet';
import L from 'leaflet';
import Link from 'next/link';

export interface HeatPoint {
  public_id?: string;
  lat: number;
  lng: number;
  status: string;
  full_name?: string;
  entry_point?: string | null;
  nationality?: string | null;
  risk_level?: string | null;
  risk_score?: number | null;
  city?: string | null;
  arrival_date?: string | null;
}

const STATUS_COLOR: Record<string, string> = {
  cleared: '#10B981',
  monitoring: '#0EA5E9',
  quarantine: '#F59E0B',
  suspect: '#EF4444',
  confirmed: '#7F1D1D',
  recovered: '#6366F1',
  deceased: '#111827',
};

const STATUS_LABEL: Record<string, string> = {
  cleared: 'Autorisé',
  monitoring: 'Surveillance',
  quarantine: 'Quarantaine',
  suspect: 'Cas suspect',
  confirmed: 'Cas confirmé',
  recovered: 'Rétabli',
  deceased: 'Décédé',
};

const RISK_LABEL: Record<string, string> = {
  low: 'Faible', moderate: 'Modéré', high: 'Élevé', critical: 'Critique',
};

const POINTS_ENTREE: { code: string; name: string; lat: number; lng: number }[] = [
  { code: 'ABJ', name: 'Aéroport FHB Abidjan', lat: 5.255, lng: -3.926 },
  { code: 'ABJ-PORT', name: 'Port autonome Abidjan', lat: 5.275, lng: -4.005 },
  { code: 'SP', name: 'Port San-Pédro', lat: 4.749, lng: -6.638 },
  { code: 'NOE', name: 'Frontière Noé', lat: 5.345, lng: -2.789 },
  { code: 'POG', name: 'Frontière Pôgô', lat: 10.108, lng: -5.819 },
];

function FitToPoints({ points }: { points: HeatPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lng]));
    map.fitBounds(bounds.pad(0.15), { maxZoom: 11 });
  }, [points, map]);
  return null;
}

export function MapView({
  points,
  showEntryPoints = true,
}: {
  points: HeatPoint[];
  showEntryPoints?: boolean;
}) {
  const center: [number, number] = useMemo(() => {
    if (points.length) return [points[0].lat, points[0].lng];
    return [7.54, -5.55]; // centre Côte d'Ivoire
  }, [points]);

  return (
    <MapContainer
      center={center}
      zoom={6}
      className="h-full w-full"
      scrollWheelZoom
      zoomControl
    >
      <TileLayer
        attribution='&copy; OpenStreetMap'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ScaleControl position="bottomleft" />

      {/* Points d'entrée (icônes statiques) */}
      {showEntryPoints &&
        POINTS_ENTREE.map((ep) => (
          <Marker
            key={ep.code}
            position={[ep.lat, ep.lng]}
            icon={L.divIcon({
              className: '',
              html: `<div style="background:#064E3B;color:#fff;font-size:10px;font-weight:800;border:2px solid #fff;border-radius:9999px;padding:2px 6px;box-shadow:0 4px 12px rgba(0,0,0,.25);white-space:nowrap;">📍 ${ep.code}</div>`,
              iconSize: [40, 20],
              iconAnchor: [20, 10],
            })}
          >
            <Tooltip>{ep.name}</Tooltip>
          </Marker>
        ))}

      {/* Voyageurs */}
      {points.map((p, i) => {
        const color = STATUS_COLOR[p.status] || '#6B7280';
        return (
          <CircleMarker
            key={p.public_id || i}
            center={[p.lat, p.lng]}
            radius={6}
            pathOptions={{
              color: '#ffffff',
              weight: 1.5,
              fillColor: color,
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              <div className="min-w-[200px]">
                <div className="text-xs uppercase tracking-wide text-slate-500 font-bold">
                  {STATUS_LABEL[p.status] || p.status}
                </div>
                <div className="font-bold text-slate-900 mt-0.5">
                  {p.full_name || 'Voyageur'}
                </div>
                {p.public_id && (
                  <div className="text-[11px] font-mono text-slate-400">{p.public_id}</div>
                )}
                <hr className="my-2 border-slate-200" />
                <ul className="space-y-0.5 text-xs">
                  {p.entry_point && (
                    <li><b>Point d'entrée :</b> {p.entry_point}</li>
                  )}
                  {p.nationality && (
                    <li><b>Nationalité :</b> {p.nationality}</li>
                  )}
                  {p.city && (
                    <li><b>Confinement :</b> {p.city}</li>
                  )}
                  {p.arrival_date && (
                    <li><b>Arrivée :</b> {new Date(p.arrival_date).toLocaleDateString('fr-FR')}</li>
                  )}
                  {p.risk_level && (
                    <li><b>Risque :</b> {RISK_LABEL[p.risk_level] || p.risk_level}
                      {typeof p.risk_score === 'number' ? ` (${p.risk_score}/100)` : ''}
                    </li>
                  )}
                </ul>
                {p.public_id && (
                  <Link
                    href={`/surveillance/${p.public_id}`}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-ciOrange hover:underline"
                  >
                    Ouvrir la fiche →
                  </Link>
                )}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      <FitToPoints points={points} />
    </MapContainer>
  );
}
