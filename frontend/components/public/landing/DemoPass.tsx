'use client';

import { motion } from 'framer-motion';
import { QrCode, ShieldCheck } from 'lucide-react';
import { useLocale } from '@/lib/i18n';

/** Motif décoratif de QR (non lisible, aucune donnée) — pass de démonstration. */
function DemoQr() {
  const size = 21;
  const cells: boolean[] = [];
  let seed = 7;
  for (let i = 0; i < size * size; i++) {
    seed = (seed * 9301 + 49297) % 233280;
    cells.push(seed / 233280 > 0.55);
  }
  const finder = (r: number, c: number) =>
    [[0, 0], [0, size - 7], [size - 7, 0]].some(([fr, fc]) => r >= fr && r < fr + 7 && c >= fc && c < fc + 7);
  const finderOn = (r: number, c: number) => {
    const [fr, fc] = [[0, 0], [0, size - 7], [size - 7, 0]].find(
      ([a, b]) => r >= a && r < a + 7 && c >= b && c < b + 7,
    )!;
    const y = r - fr;
    const x = c - fc;
    return y === 0 || y === 6 || x === 0 || x === 6 || (y >= 2 && y <= 4 && x >= 2 && x <= 4);
  };
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="h-full w-full" aria-hidden="true" shapeRendering="crispEdges">
      {cells.map((on, i) => {
        const r = Math.floor(i / size);
        const c = i % size;
        const filled = finder(r, c) ? finderOn(r, c) : on;
        return filled ? <rect key={i} x={c} y={r} width={1} height={1} fill="#0f172a" /> : null;
      })}
    </svg>
  );
}

/** Aperçu animé d'un pass FICTIF, clairement identifié « Démonstration ». */
export function DemoPass({ className = '' }: { className?: string }) {
  const { t } = useLocale();
  const d = t.demo;
  return (
    <motion.figure
      className={`relative w-[19rem] max-w-full rounded-3xl bg-white p-4 shadow-2xl ring-1 ring-slate-900/5 ${className}`}
      initial={{ opacity: 0, y: 24, rotate: -2 }}
      animate={{ opacity: 1, y: [0, -6, 0], rotate: -2 }}
      transition={{
        opacity: { duration: 0.5, delay: 0.3 },
        y: { duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 0.8 },
      }}
      aria-label={`${d.title} — ${d.badge}. ${d.disclaimer}`}
    >
      <span className="absolute -top-3 right-4 rounded-full bg-ciOrange px-3 py-1 text-[11px] font-black uppercase tracking-widest text-slate-900 shadow">
        {d.badge}
      </span>
      <div className="flex items-center gap-2 rounded-2xl bg-ciForest px-3 py-2 text-white">
        <ShieldCheck className="h-4 w-4" aria-hidden="true" />
        <span className="text-sm font-bold">{d.title}</span>
      </div>
      <div className="mt-3 grid grid-cols-[1fr,auto] items-center gap-3">
        <dl className="space-y-2 text-xs">
          <div>
            <dt className="text-slate-500">{d.name}</dt>
          </div>
          <div>
            <dt className="text-slate-500">{d.passLabel}</dt>
            <dd className="font-mono font-bold text-slate-900">PASS-DEMO-0000</dd>
          </div>
          <div>
            <dt className="text-slate-500">{d.statusLabel}</dt>
            <dd className="font-bold text-ciForest">{d.status}</dd>
          </div>
        </dl>
        <div className="h-24 w-24 rounded-xl border border-slate-200 p-1.5">
          <DemoQr />
        </div>
      </div>
      <figcaption className="mt-3 flex items-center gap-1.5 border-t border-dashed border-slate-200 pt-2 text-[11px] text-slate-600">
        <QrCode className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{d.qr} — <strong className="text-orange-800">{d.disclaimer}</strong></span>
      </figcaption>
    </motion.figure>
  );
}
