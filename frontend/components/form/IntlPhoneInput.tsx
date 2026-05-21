'use client';

/**
 * Champ téléphone international léger (pas de dépendance externe).
 *
 * - Liste de dial codes courants (Afrique de l'Ouest + grands pôles).
 * - Sortie au format E.164-ish : `+XXXYYYYYYYY` (préfixe + numéro national
 *   sans espaces) — accepté par le regex DRF côté backend.
 * - Pré-sélection sur Côte d'Ivoire par défaut.
 *
 * Usage :
 *   <IntlPhoneInput value={phone} onChange={setPhone} placeholder="07 XX XX XX XX" />
 */

import { useEffect, useMemo, useState } from 'react';

interface DialCode {
  iso: string;
  name: string;
  dial: string;   // ex: "225"
  flag: string;   // emoji drapeau
}

// Liste alignée sur frontend/lib/datasets.ts COUNTRIES.
const DIAL_CODES: DialCode[] = [
  { iso: 'CI', name: "Côte d'Ivoire",        dial: '225', flag: '🇨🇮' },
  { iso: 'GH', name: 'Ghana',                dial: '233', flag: '🇬🇭' },
  { iso: 'NG', name: 'Nigeria',              dial: '234', flag: '🇳🇬' },
  { iso: 'CD', name: 'R.D. Congo',           dial: '243', flag: '🇨🇩' },
  { iso: 'CG', name: 'Rép. du Congo',        dial: '242', flag: '🇨🇬' },
  { iso: 'UG', name: 'Ouganda',              dial: '256', flag: '🇺🇬' },
  { iso: 'GN', name: 'Guinée',               dial: '224', flag: '🇬🇳' },
  { iso: 'SL', name: 'Sierra Leone',         dial: '232', flag: '🇸🇱' },
  { iso: 'LR', name: 'Liberia',              dial: '231', flag: '🇱🇷' },
  { iso: 'ML', name: 'Mali',                 dial: '223', flag: '🇲🇱' },
  { iso: 'BF', name: 'Burkina Faso',         dial: '226', flag: '🇧🇫' },
  { iso: 'SN', name: 'Sénégal',              dial: '221', flag: '🇸🇳' },
  { iso: 'TG', name: 'Togo',                 dial: '228', flag: '🇹🇬' },
  { iso: 'BJ', name: 'Bénin',                dial: '229', flag: '🇧🇯' },
  { iso: 'CM', name: 'Cameroun',             dial: '237', flag: '🇨🇲' },
  { iso: 'GA', name: 'Gabon',                dial: '241', flag: '🇬🇦' },
  { iso: 'CF', name: 'Centrafrique',         dial: '236', flag: '🇨🇫' },
  { iso: 'KE', name: 'Kenya',                dial: '254', flag: '🇰🇪' },
  { iso: 'ZA', name: 'Afrique du Sud',       dial: '27',  flag: '🇿🇦' },
  { iso: 'EG', name: 'Égypte',               dial: '20',  flag: '🇪🇬' },
  { iso: 'MA', name: 'Maroc',                dial: '212', flag: '🇲🇦' },
  { iso: 'TN', name: 'Tunisie',              dial: '216', flag: '🇹🇳' },
  { iso: 'FR', name: 'France',               dial: '33',  flag: '🇫🇷' },
  { iso: 'BE', name: 'Belgique',             dial: '32',  flag: '🇧🇪' },
  { iso: 'DE', name: 'Allemagne',            dial: '49',  flag: '🇩🇪' },
  { iso: 'CH', name: 'Suisse',               dial: '41',  flag: '🇨🇭' },
  { iso: 'GB', name: 'Royaume-Uni',          dial: '44',  flag: '🇬🇧' },
  { iso: 'ES', name: 'Espagne',              dial: '34',  flag: '🇪🇸' },
  { iso: 'IT', name: 'Italie',               dial: '39',  flag: '🇮🇹' },
  { iso: 'PT', name: 'Portugal',             dial: '351', flag: '🇵🇹' },
  { iso: 'US', name: 'États-Unis',           dial: '1',   flag: '🇺🇸' },
  { iso: 'CA', name: 'Canada',               dial: '1',   flag: '🇨🇦' },
  { iso: 'BR', name: 'Brésil',               dial: '55',  flag: '🇧🇷' },
  { iso: 'CN', name: 'Chine',                dial: '86',  flag: '🇨🇳' },
  { iso: 'IN', name: 'Inde',                 dial: '91',  flag: '🇮🇳' },
  { iso: 'TR', name: 'Turquie',              dial: '90',  flag: '🇹🇷' },
  { iso: 'AE', name: 'Émirats arabes unis',  dial: '971', flag: '🇦🇪' },
  { iso: 'SA', name: 'Arabie saoudite',      dial: '966', flag: '🇸🇦' },
  { iso: 'LB', name: 'Liban',                dial: '961', flag: '🇱🇧' },
];

const DEFAULT_ISO = 'CI';

/**
 * Sépare une valeur globale ("+22507112233") en (iso, national).
 * Si le prefix ne correspond à aucun code connu → on garde la liste par défaut.
 */
function splitValue(value: string): { iso: string; national: string } {
  if (!value || !value.startsWith('+')) {
    return { iso: DEFAULT_ISO, national: (value || '').replace(/\D/g, '') };
  }
  const digits = value.slice(1).replace(/\D/g, '');
  // Match longest prefix first (e.g. 225 before 22).
  const sorted = [...DIAL_CODES].sort((a, b) => b.dial.length - a.dial.length);
  for (const c of sorted) {
    if (digits.startsWith(c.dial)) {
      return { iso: c.iso, national: digits.slice(c.dial.length) };
    }
  }
  return { iso: DEFAULT_ISO, national: digits };
}

function joinValue(iso: string, national: string): string {
  const dial = DIAL_CODES.find((c) => c.iso === iso)?.dial || '225';
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
    const parsed = splitValue(value);
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

  const current = DIAL_CODES.find((c) => c.iso === iso) || DIAL_CODES[0];

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
          {DIAL_CODES.map((c) => (
            <option key={c.iso} value={c.iso}>
              {c.flag} {c.name} (+{c.dial})
            </option>
          ))}
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
