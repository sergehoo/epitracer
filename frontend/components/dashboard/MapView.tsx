'use client';

import 'leaflet/dist/leaflet.css';
import { useEffect, useMemo } from 'react';
import {
  CircleMarker, GeoJSON, LayersControl, MapContainer, Marker, Popup,
  ScaleControl, TileLayer, Tooltip, useMap,
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

export interface ZoneFeature {
  type: 'Feature';
  id: string;
  geometry: { type: 'MultiPolygon'; coordinates: number[][][][] };
  properties: {
    code: string;
    name: string;
    level: string;
    level_display: string;
    risk_level: string;
    population?: number | null;
    parent_name?: string | null;
    parent_code?: string | null;
  };
}
export interface ZoneCollection {
  type: 'FeatureCollection';
  features: ZoneFeature[];
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
  low: 'Faible', moderate: 'Modéré', high: 'Élevé', critical: 'Critique', red: 'Zone rouge',
};

const RISK_COLOR: Record<string, string> = {
  low: '#10B981',
  moderate: '#F59E0B',
  high: '#EF4444',
  red: '#7F1D1D',
  critical: '#7F1D1D',
};

const LEVEL_BORDER: Record<string, string> = {
  pres: '#FF7F00',
  region: '#009E60',
  district: '#0EA5E9',
  commune: '#7C3AED',
  quartier: '#94A3B8',
};

const POINTS_ENTREE: { code: string; name: string; lat: number; lng: number }[] = [
  { code: 'ABJ', name: 'Aéroport FHB Abidjan', lat: 5.255, lng: -3.926 },
  { code: 'ABJ-PORT', name: 'Port autonome Abidjan', lat: 5.275, lng: -4.005 },
  { code: 'SP', name: 'Port San-Pédro', lat: 4.749, lng: -6.638 },
  { code: 'NOE', name: 'Frontière Noé', lat: 5.345, lng: -2.789 },
  { code: 'POG', name: 'Frontière Pôgô', lat: 10.108, lng: -5.819 },
];

// =========================================================================
// Helpers
// =========================================================================

function FitToPoints({ points, fallback }: { points: HeatPoint[]; fallback?: ZoneCollection | null }) {
  const map = useMap();
  useEffect(() => {
    if (points.length) {
      const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lng]));
      map.fitBounds(bounds.pad(0.15), { maxZoom: 11 });
      return;
    }
    // Fallback : fit sur les polygones de zones si dispo
    if (fallback && fallback.features.length) {
      try {
        const layer = L.geoJSON(fallback as any);
        const bounds = layer.getBounds();
        if (bounds.isValid()) map.fitBounds(bounds.pad(0.05), { maxZoom: 9 });
      } catch {}
    }
  }, [points, fallback, map]);
  return null;
}

function FocusOnZone({ zones, focusCode }: { zones: ZoneCollection | null; focusCode?: string | null }) {
  const map = useMap();
  useEffect(() => {
    if (!focusCode || !zones) return;
    const feat = zones.features.find((f) => f.properties.code === focusCode);
    if (!feat) return;
    try {
      const layer = L.geoJSON(feat as any);
      const bounds = layer.getBounds();
      if (bounds.isValid()) map.fitBounds(bounds.pad(0.1), { maxZoom: 12 });
    } catch {}
  }, [zones, focusCode, map]);
  return null;
}

// =========================================================================
// Composant principal
// =========================================================================

export function MapView({
  points,
  showEntryPoints = true,
  zones = null,
  zonesColorBy = 'risk',
  focusZoneCode = null,
}: {
  points: HeatPoint[];
  showEntryPoints?: boolean;
  /** GeoJSON FeatureCollection des HealthZones à afficher */
  zones?: ZoneCollection | null;
  /** Choropleth : 'risk' = couleur selon risk_level, 'level' = couleur selon niveau */
  zonesColorBy?: 'risk' | 'level';
  /** Si défini, zoom automatique sur cette zone */
  focusZoneCode?: string | null;
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
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="OpenStreetMap">
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Satellite (Esri)">
          <TileLayer
            attribution='&copy; Esri'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Terrain (Stamen)">
          <TileLayer
            attribution='&copy; Stadia Maps &copy; OpenStreetMap'
            url="https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png"
          />
        </LayersControl.BaseLayer>
      </LayersControl>

      <ScaleControl position="bottomleft" />

      {/* ===== LAYER ZONES SANITAIRES (polygones choropleth) ===== */}
      {zones && zones.features.length > 0 && (
        <GeoJSON
          key={`zones-${zones.count ?? zones.features.length}-${zonesColorBy}`}
          data={zones as any}
          style={(feature) => {
            const p = feature?.properties;
            const fill = zonesColorBy === 'level'
              ? (LEVEL_BORDER[p?.level] || '#94A3B8')
              : (RISK_COLOR[p?.risk_level] || '#94A3B8');
            const border = LEVEL_BORDER[p?.level] || '#475569';
            return {
              color: border,
              weight: p?.level === 'pres' ? 2.5 : p?.level === 'region' ? 2 : 1,
              opacity: 0.85,
              fillColor: fill,
              fillOpacity: 0.25,
            };
          }}
          onEachFeature={(feature, layer) => {
            const p = feature.properties;
            // Tooltip survol
            layer.bindTooltip(
              `<strong>${p.name}</strong><br/><span style="opacity:0.7">${p.level_display}</span>`,
              { sticky: true, direction: 'top' },
            );
            // Popup au clic
            const popup = `
              <div style="min-width:200px">
                <div style="text-transform:uppercase;letter-spacing:0.05em;font-size:10px;color:#64748B;font-weight:700;">
                  ${p.level_display}
                </div>
                <div style="font-weight:700;font-size:15px;margin-top:2px;">${p.name}</div>
                <div style="font-size:11px;color:#94A3B8;font-family:monospace;margin-top:2px;">${p.code}</div>
                <hr style="margin:8px 0;border-color:#E2E8F0;"/>
                <ul style="margin:0;padding:0;list-style:none;font-size:12px;line-height:1.5;">
                  ${p.parent_name ? `<li><strong>Parent:</strong> ${p.parent_name}</li>` : ''}
                  <li><strong>Risque:</strong> <span style="text-transform:capitalize">${p.risk_level}</span></li>
                  ${p.population ? `<li><strong>Population:</strong> ${p.population.toLocaleString('fr-FR')}</li>` : ''}
                </ul>
                <a href="/districts/${p.code}"
                   style="margin-top:8px;display:inline-block;font-weight:700;font-size:12px;color:#FF7F00;text-decoration:none;">
                  Détail & statistiques →
                </a>
              </div>
            `;
            layer.bindPopup(popup, { maxWidth: 280 });

            // Effet hover : épaissir le contour
            layer.on({
              mouseover: (e) => {
                const l = e.target as L.Path;
                l.setStyle({ weight: 4, fillOpacity: 0.45 });
              },
              mouseout: (e) => {
                const l = e.target as L.Path;
                const lvl = (feature.properties as any).level;
                l.setStyle({
                  weight: lvl === 'pres' ? 2.5 : lvl === 'region' ? 2 : 1,
                  fillOpacity: 0.25,
                });
              },
            });
          }}
        />
      )}

      {/* ===== POINTS D'ENTRÉE ===== */}
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

      {/* ===== VOYAGEURS (markers) ===== */}
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
                  {p.entry_point && (<li><b>Point d'entrée :</b> {p.entry_point}</li>)}
                  {p.nationality && (<li><b>Nationalité :</b> {p.nationality}</li>)}
                  {p.city && (<li><b>Confinement :</b> {p.city}</li>)}
                  {p.arrival_date && (<li><b>Arrivée :</b> {new Date(p.arrival_date).toLocaleDateString('fr-FR')}</li>)}
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

      <FitToPoints points={points} fallback={zones} />
      <FocusOnZone zones={zones} focusCode={focusZoneCode} />
    </MapContainer>
  );
}
