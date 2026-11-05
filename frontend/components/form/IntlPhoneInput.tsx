'use client';

/**
 * Champ téléphone international léger (pas de dépendance externe).
 *
 * - Tous les pays et territoires dotés d'un indicatif (lib/datasets.ts) :
 *   pays fréquents en tête, puis la liste complète de A à Z.
 * - Sortie au format E.164-ish : `+XXXYYYYYYYY` (préfixe + numéro national
 *   sans espaces) — accepté par le regex DRF côté backend.
 * - Pré-sélection sur Côte d'Ivoire par défaut.
 *
 * Usage :
 *   <IntlPhoneInput value={phone} onChange={setPhone} placeholder="07 XX XX XX XX" />
 */

import { useEffect, useMemo, useState } from 'react';
import { COUNTRIES, COUNTRY_DIAL_CODES, DIAL_CODE_COUNTRY } from '@/lib/datasets';

interface DialCode {
  iso: string;
  name: string;
  dial: string;   // ex: "225"
  flag: string;   // emoji drapeau
}

// Pays fréquents (sous-région, diaspora, grandes liaisons aériennes), proposés en tête.
const FREQUENT_ISO = [
  'CI', 'GH', 'NG', 'CD', 'CG', 'UG', 'GN', 'SL', 'LR', 'ML', 'BF', 'SN', 'TG', 'BJ', 'NE',
  'GW', 'GM', 'CV', 'MR', 'CM', 'GA', 'CF', 'KE', 'ZA', 'EG', 'MA', 'TN', 'FR', 'BE', 'DE',
  'CH', 'GB', 'ES', 'IT', 'PT', 'US', 'CA', 'BR', 'CN', 'IN', 'TR', 'AE', 'SA', 'LB',
];

// Drapeau emoji dérivé du code ISO (lettres régionales Unicode).
const flagOf = (iso: string) => String.fromCodePoint(...[...iso].map((ch) => 0x1f1a5 + ch.charCodeAt(0)));

const BY_ISO = new Map<string, DialCode>(
  COUNTRIES.filter((c) => COUNTRY_DIAL_CODES[c.code]).map((c) => [
    c.code,
    { iso: c.code, name: c.name, dial: COUNTRY_DIAL_CODES[c.code], flag: flagOf(c.code) },
  ]),
);
const FREQUENT = FREQUENT_ISO.map((iso) => BY_ISO.get(iso)!);
const ALL_SORTED = [...BY_ISO.values()].sort((a, b) => a.name.localeCompare(b.name, 'fr'));

const DEFAULT_ISO = 'CI';

/**
 * Sépare une valeur globale ("+22507112233") en (iso, national).
 * Un indicatif partagé (+1, +7, +44…) garde le pays déjà choisi, sinon le pays
 * principal de l'indicatif. Préfixe inconnu → pays par défaut.
 */
function splitValue(value: string, currentIso?: string): { iso: string; national: string } {
  const current = currentIso ? BY_ISO.get(currentIso) : undefined;
  if (!value || !value.startsWith('+')) {
    return { iso: current?.iso || DEFAULT_ISO, national: (value || '').replace(/\D/g, '') };
  }
  const digits = value.slice(1).replace(/\D/g, '');
  if (current && digits.startsWith(current.dial)) {
    return { iso: current.iso, national: digits.slice(current.dial.length) };
  }
  // Indicatif le plus long d'abord (ex. 225 avant 22).
  for (const len of [3, 2, 1]) {
    const iso = DIAL_CODE_COUNTRY[digits.slice(0, len)];
    if (iso && BY_ISO.has(iso)) return { iso, national: digits.slice(len) };
  }
  return { iso: DEFAULT_ISO, national: digits };
}

function joinValue(iso: string, national: string): string {
  const dial = BY_ISO.get(iso)?.dial || '225';
  const cleaned = (national || '').replace(/\D/g, '');
  if (!cleaned) return '';
  return `+${dial}${cleaned}`;
}

interface Props {
  value: string;
  onChange: (e164: string) => void;
  placeholder?: string;
  required?: boolean;
  invalid?: boolean;
  id?: string;
}

export function IntlPhoneInput({ value, onChange, placeholder, invalid, id }: Props) {
  const initial = useMemo(() => splitValue(value), [value]);
  const [iso, setIso] = useState<string>(initial.iso);
  const [national, setNational] = useState<string>(initial.national);

  // Sync interne si la valeur externe change (form reset, etc.)
  useEffect(() => {
    const parsed = splitValue(value, iso);
    setIso(parsed.iso);
    setNational(parsed.national);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const handleIso = (newIso: string) => {
    setIso(newIso);
    onChange(joinValue(newIso, national));
  };
  const handleNational = (raw: string) => {
    const cleaned = raw.replace(/[^\d\s().-]/g, '');
    setNational(cleaned);
    onChange(joinValue(iso, cleaned));
  };

  const current = BY_ISO.get(iso) || BY_ISO.get(DEFAULT_ISO)!;
  const label = (c: DialCode) => `${c.flag} ${c.name} (+${c.dial})`;

  return (
    <div
      className={`flex items-stretch rounded-xl border ${
        invalid ? 'border-rose-400' : 'border-slate-300 dark:border-slate-700'
      } bg-white dark:bg-slate-950 overflow-hidden focus-within:ring-2 focus-within:ring-ciOrange/40`}
    >
      <div className="relative inline-flex items-center px-2 border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
        <span className="text-xl mr-1 select-none" aria-hidden>
          {current.flag}
        </span>
        <span className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-200">
          +{current.dial}
        </span>
        <select
          value={iso}
          onChange={(e) => handleIso(e.target.value)}
          className="absolute inset-0 opacity-0 cursor-pointer"
          aria-label="Indicatif pays"
        >
          <optgroup label="Pays fréquents">
            {FREQUENT.map((c) => (
              <option key={`frequent-${c.iso}`} value={c.iso}>{label(c)}</option>
            ))}
          </optgroup>
          <optgroup label="Tous les pays (A à Z)">
            {ALL_SORTED.map((c) => (
              <option key={c.iso} value={c.iso}>{label(c)}</option>
            ))}
          </optgroup>
        </select>
      </div>
      <input
        id={id}
        type="tel"
        inputMode="tel"
        autoComplete="tel-national"
        value={national}
        onChange={(e) => handleNational(e.target.value)}
        placeholder={placeholder || '07 XX XX XX XX'}
        className="flex-1 px-3 py-2 bg-transparent outline-none text-sm font-medium"
      />
    </div>
  );
}
