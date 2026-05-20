'use client';

import 'leaflet/dist/leaflet.css';
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet';

interface HeatPoint { lat: number; lng: number; status: string }

const COLOR: Record<string, string> = {
  cleared: '#10B981',
  monitoring: '#0EA5E9',
  quarantine: '#F59E0B',
  suspect: '#EF4444',
  confirmed: '#7F1D1D',
  recovered: '#6366F1',
  deceased: '#111827',
};

export function MapView({ points }: { points: HeatPoint[] }) {
  const center: [number, number] = points.length
    ? [points[0].lat, points[0].lng]
    : [7.54, -5.55]; // centre Côte d'Ivoire

  return (
    <div className="card overflow-hidden h-[60vh]">
      <MapContainer center={center} zoom={6} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.map((p, i) => (
          <CircleMarker
            key={i}
            center={[p.lat, p.lng]}
            radius={5}
            pathOptions={{ color: COLOR[p.status] || '#6B7280', fillOpacity: 0.8, stroke: false }}
          >
            <Tooltip>{p.status}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
