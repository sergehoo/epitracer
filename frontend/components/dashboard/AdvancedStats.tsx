'use client';

import { Activity, ArrowDown, ArrowUp, TrendingUp } from 'lucide-react';

export interface FunnelStep { step: string; count: number }
export interface HourBucket { hour: number; count: number }

/** Funnel — entonnoir arrivées → pass → suivi → check-in → clôture */
export function FunnelChart({ data }: { data: FunnelStep[] }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <article className="card p-6">
      <h3 className="font-display text-lg font-black flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-ciOrange" /> Entonnoir voyageurs
      </h3>
      <p className="text-xs text-slate-500 mt-1">
        Du passage frontière jusqu'à la clôture du suivi 21j.
      </p>
      <ul className="mt-4 space-y-2.5">
        {data.map((s, i) => {
          const width = (s.count / max) * 100;
          const dropRate = i > 0 && data[i - 1].count > 0
            ? Math.round((1 - s.count / data[i - 1].count) * 100)
            : null;
          return (
            <li key={s.step}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                  {s.step}
                </span>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-ciDark dark:text-emerald-200">
                    {s.count.toLocaleString('fr-FR')}
                  </span>
                  {dropRate !== null && dropRate > 0 && (
                    <span className="text-[10px] text-slate-400">
                      -{dropRate}%
                    </span>
                  )}
                </div>
              </div>
              <div className="h-3 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-ciOrange to-ciGreen rounded-full"
                  style={{ width: `${width}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </article>
  );
}

/** Heatmap horaire — arrivées par heure (24 buckets) */
export function HourlyHeatmap({ data }: { data: HourBucket[] }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <article className="card p-6">
      <h3 className="font-display text-lg font-black flex items-center gap-2">
        <Activity className="h-5 w-5 text-ciGreen" /> Arrivées par heure
      </h3>
      <p className="text-xs text-slate-500 mt-1">
        Répartition sur 24h — utile pour dimensionner les équipes aux frontières.
      </p>
      <div className="mt-4 grid grid-cols-12 gap-1">
        {data.map((h) => {
          const intensity = h.count / max;
          // Palette CI : transparent → orange → vert
          const color = intensity === 0
            ? '#f1f5f9'
            : intensity < 0.4
              ? `rgba(247, 127, 0, ${0.25 + intensity})`
              : `rgba(0, 155, 90, ${0.5 + intensity * 0.5})`;
          return (
            <div
              key={h.hour}
              className="flex flex-col items-center"
              title={`${String(h.hour).padStart(2, '0')}h00 — ${h.count} arrivée(s)`}
            >
              <div
                className="w-full h-12 rounded transition-all hover:scale-110 cursor-help"
                style={{ backgroundColor: color }}
              />
              <span className="text-[9px] mt-1 text-slate-500 font-mono">
                {String(h.hour).padStart(2, '0')}
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-500">
        <span>0</span>
        <div className="flex-1 h-1.5 rounded bg-gradient-to-r from-slate-100 via-orange-300 to-emerald-500" />
        <span>max {max}</span>
      </div>
    </article>
  );
}

/** Jauge — taux d'observance check-in */
export function ComplianceGauge({
  pct, withRecent, totalActive,
}: { pct: number; withRecent: number; totalActive: number }) {
  // Détermine la couleur selon le seuil
  const color = pct >= 80 ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30'
    : pct >= 50 ? 'text-amber-600 bg-amber-50 dark:bg-amber-950/30'
    : 'text-rose-600 bg-rose-50 dark:bg-rose-950/30';
  const stroke = pct >= 80 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444';

  // Anneau SVG
  const R = 56;
  const C = 2 * Math.PI * R;
  const dash = (pct / 100) * C;

  return (
    <article className={`card p-6 ${color}`}>
      <h3 className="font-display text-lg font-black">Observance check-in</h3>
      <p className="text-xs opacity-80 mt-1">
        Voyageurs en suivi actif avec un check-in dans les 48 dernières heures.
      </p>
      <div className="mt-4 flex items-center gap-5">
        <svg width="140" height="140" viewBox="0 0 140 140" className="shrink-0">
          <circle cx="70" cy="70" r={R} fill="none"
                  stroke="currentColor" strokeOpacity="0.15" strokeWidth="14" />
          <circle cx="70" cy="70" r={R} fill="none"
                  stroke={stroke} strokeWidth="14" strokeLinecap="round"
                  strokeDasharray={`${dash} ${C}`}
                  transform="rotate(-90 70 70)" />
          <text x="70" y="68" textAnchor="middle"
                fontSize="28" fontWeight="800" fill={stroke}>
            {pct}%
          </text>
          <text x="70" y="86" textAnchor="middle"
                fontSize="10" fill="#64748B">
            observance
          </text>
        </svg>
        <div className="space-y-2 text-sm">
          <div>
            <div className="text-xs opacity-80">Check-in à jour</div>
            <div className="font-bold text-lg">{withRecent.toLocaleString('fr-FR')}</div>
          </div>
          <div>
            <div className="text-xs opacity-80">Suivis actifs</div>
            <div className="font-bold text-lg">{totalActive.toLocaleString('fr-FR')}</div>
          </div>
        </div>
      </div>
    </article>
  );
}

/** Card de comparaison période vs période précédente */
export function ComparisonCard({
  label, current, previous, trendPct, icon,
}: { label: string; current: number; previous: number; trendPct: number; icon?: React.ReactNode }) {
  const up = trendPct >= 0;
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between text-xs text-slate-500 uppercase tracking-wide">
        <span>{label}</span>
        {icon && <span>{icon}</span>}
      </div>
      <div className="mt-2 font-display text-3xl font-black text-ciDark dark:text-emerald-200">
        {current.toLocaleString('fr-FR')}
      </div>
      <div className="mt-1.5 flex items-center gap-1.5">
        <span className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
          up ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
        }`}>
          {up ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
          {Math.abs(trendPct)}%
        </span>
        <span className="text-[10px] text-slate-500">
          vs {previous.toLocaleString('fr-FR')} période précédente
        </span>
      </div>
    </div>
  );
}
