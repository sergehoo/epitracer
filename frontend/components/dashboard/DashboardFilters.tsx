'use client';

import { useEffect, useState } from 'react';
import { Calendar, Globe2, MapPin, ShieldAlert, X } from 'lucide-react';
import { api } from '@/lib/api';

export interface DashboardFilterState {
  period: number;
  risk: string;
  followup: string;
  country: string;
  entryPoint: string;
}

interface Props {
  value: DashboardFilterState;
  onChange: (next: DashboardFilterState) => void;
}

const PERIOD_OPTIONS = [
  { value: 7,   label: '7 j' },
  { value: 14,  label: '14 j' },
  { value: 30,  label: '30 j' },
  { value: 90,  label: '90 j' },
  { value: 180, label: '6 mois' },
  { value: 365, label: '1 an' },
];

const RISK_OPTIONS = [
  { value: '',         label: 'Tous risques' },
  { value: 'low',      label: 'Faible' },
  { value: 'moderate', label: 'Modéré' },
  { value: 'high',     label: 'Élevé' },
  { value: 'critical', label: 'Critique' },
];

const FOLLOWUP_OPTIONS = [
  { value: '',        label: 'Tous suivis' },
  { value: 'active',  label: 'Suivi actif' },
  { value: 'missed',  label: 'Check-in manqué (48h)' },
  { value: 'closed',  label: 'Suivi clôturé' },
];

interface EntryPoint { id: number; name: string; code: string }
interface Country { code: string; name: string }

export function DashboardFilters({ value, onChange }: Props) {
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);

  useEffect(() => {
    api.get('/geo/entry-points/?is_active=true&page_size=50')
      .then((r) => setEntryPoints(r.data.results || r.data || []))
      .catch(() => undefined);
    api.get('/geo/countries/?page_size=300')
      .then((r) => setCountries(r.data.results || r.data || []))
      .catch(() => undefined);
  }, []);

  const hasFilters = !!(value.risk || value.followup || value.country || value.entryPoint || value.period !== 30);

  return (
    <div className="card p-4 flex flex-wrap items-center gap-3">
      {/* Période */}
      <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 dark:border-slate-700 p-1">
        <Calendar className="h-3.5 w-3.5 ml-1 text-slate-500" />
        {PERIOD_OPTIONS.map((p) => (
          <button
            key={p.value}
            onClick={() => onChange({ ...value, period: p.value })}
            className={`px-2.5 py-1 text-xs rounded-lg font-bold transition ${
              value.period === p.value
                ? 'bg-ciDark text-white'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Niveau de risque */}
      <div className="inline-flex items-center gap-1">
        <ShieldAlert className="h-3.5 w-3.5 text-slate-500" />
        <select
          className="select max-w-[170px] text-sm"
          value={value.risk}
          onChange={(e) => onChange({ ...value, risk: e.target.value })}
        >
          {RISK_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Suivi */}
      <select
        className="select max-w-[200px] text-sm"
        value={value.followup}
        onChange={(e) => onChange({ ...value, followup: e.target.value })}
      >
        {FOLLOWUP_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {/* Pays */}
      <div className="inline-flex items-center gap-1">
        <Globe2 className="h-3.5 w-3.5 text-slate-500" />
        <select
          className="select max-w-[200px] text-sm"
          value={value.country}
          onChange={(e) => onChange({ ...value, country: e.target.value })}
        >
          <option value="">Tous pays</option>
          {countries.map((c) => (
            <option key={c.code} value={c.code}>{c.name || c.code}</option>
          ))}
        </select>
      </div>

      {/* Point d'entrée */}
      <div className="inline-flex items-center gap-1">
        <MapPin className="h-3.5 w-3.5 text-slate-500" />
        <select
          className="select max-w-[220px] text-sm"
          value={value.entryPoint}
          onChange={(e) => onChange({ ...value, entryPoint: e.target.value })}
        >
          <option value="">Tous points d'entrée</option>
          {entryPoints.map((e) => (
            <option key={e.id} value={String(e.id)}>{e.name}</option>
          ))}
        </select>
      </div>

      {hasFilters && (
        <button
          onClick={() => onChange({
            period: 30, risk: '', followup: '', country: '', entryPoint: '',
          })}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          <X className="h-3 w-3" /> Réinitialiser
        </button>
      )}
    </div>
  );
}
