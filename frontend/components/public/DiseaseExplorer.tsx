'use client';

import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { DiseaseCard } from './DiseaseCard';
import { ALERT_LEVEL_ORDER, ALERT_LEVEL_STYLE } from '@/lib/portal';
import type { PublicDisease } from '@/types/portal';

/** Recherche et filtres sur les fiches maladies publiées (liste fournie par le serveur). */
export function DiseaseExplorer({ diseases }: { diseases: PublicDisease[] }) {
  const [q, setQ] = useState('');
  const [onlyActive, setOnlyActive] = useState(false);
  const [level, setLevel] = useState('');
  const [transmission, setTransmission] = useState('');

  const transmissions = useMemo(
    () => Array.from(new Set(diseases.flatMap((d) => d.transmission))).sort(),
    [diseases],
  );

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return diseases.filter((d) =>
      (!needle || `${d.name} ${d.short_name} ${d.description}`.toLowerCase().includes(needle))
      && (!onlyActive || d.under_surveillance)
      && (!level || d.public_alert_level === level)
      && (!transmission || d.transmission.includes(transmission)));
  }, [diseases, q, onlyActive, level, transmission]);

  return (
    <div>
      <form
        role="search"
        onSubmit={(e) => e.preventDefault()}
        className="flex flex-col gap-3 rounded-3xl border border-slate-100 bg-white p-4 shadow-sm md:flex-row md:items-center"
      >
        <label className="relative flex-1">
          <span className="sr-only">Rechercher une maladie</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Rechercher : nom, symptôme, mode de transmission…"
            className="input pl-9"
          />
        </label>
        <label className="text-sm">
          <span className="sr-only">Niveau d&apos;alerte</span>
          <select className="select" value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">Tous niveaux d&apos;alerte</option>
            {ALERT_LEVEL_ORDER.map((l) => <option key={l} value={l}>{ALERT_LEVEL_STYLE[l].label}</option>)}
          </select>
        </label>
        <label className="text-sm">
          <span className="sr-only">Mode de transmission</span>
          <select className="select" value={transmission} onChange={(e) => setTransmission(e.target.value)}>
            <option value="">Toutes transmissions</option>
            {transmissions.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label className="inline-flex items-center gap-2 whitespace-nowrap text-sm font-semibold text-slate-700">
          <input type="checkbox" checked={onlyActive} onChange={(e) => setOnlyActive(e.target.checked)} />
          Sous surveillance uniquement
        </label>
      </form>

      <p className="mt-4 text-sm text-slate-500" aria-live="polite">
        {visible.length} fiche{visible.length > 1 ? 's' : ''}
      </p>

      {visible.length > 0 ? (
        <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((d) => <DiseaseCard key={d.slug} disease={d} headingLevel={2} />)}
        </div>
      ) : (
        <p className="mt-4 rounded-2xl border border-slate-100 bg-white p-6 text-slate-600">
          {diseases.length === 0
            ? "Aucune fiche n'est publiée pour le moment. Les autorités sanitaires mettent ces informations à jour au fil de la situation."
            : 'Aucune fiche ne correspond à votre recherche.'}
        </p>
      )}
    </div>
  );
}
