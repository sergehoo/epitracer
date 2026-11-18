'use client';

/**
 * Liste déroulante de pays avec recherche (motif ARIA « combobox »).
 *
 * - Tous les pays du référentiel local ISO 3166-1 (lib/datasets.ts), sans appel réseau.
 * - Recherche dès le premier caractère, insensible aux accents et à la casse (noms FR et EN).
 * - Clavier : ↓/↑ pour parcourir, Entrée pour choisir, Échap pour annuler.
 * - Valeur : code ISO alpha-2 ; seul un pays de la liste peut être retenu.
 *
 * Usage :
 *   <CountryCombobox value={code} onChange={setCode} aria-label="Pays de provenance" />
 */

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { ChevronDown } from 'lucide-react';
import { buildCountryOptions, findExactCountry, searchCountries } from '@/lib/countrySearch';
import { COUNTRIES } from '@/lib/datasets';
import { useLocale } from '@/lib/i18n';

interface Props {
  value: string;
  onChange: (code: string) => void;
  invalid?: boolean;
  placeholder?: string;
  id?: string;
  'aria-label'?: string;
}

export function CountryCombobox({
  value, onChange, invalid, placeholder = 'Rechercher un pays…', id, 'aria-label': ariaLabel,
}: Props) {
  const { locale } = useLocale();
  const options = useMemo(() => buildCountryOptions(COUNTRIES, locale), [locale]);
  const selected = useMemo(
    () => options.find((o) => o.code === (value || '').toUpperCase()),
    [options, value],
  );
  // null : pas de saisie en cours, le champ affiche le pays retenu.
  const [query, setQuery] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const results = useMemo(() => searchCountries(options, query ?? ''), [options, query]);

  const listId = useId();
  const autoId = useId();
  const listRef = useRef<HTMLUListElement>(null);
  const optionId = (code: string) => `${listId}-${code}`;

  // L'option active reste visible pendant la navigation au clavier.
  useEffect(() => {
    if (open) listRef.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [active, open]);

  const openList = () => {
    if (open) return;
    setOpen(true);
    setActive(Math.max(0, results.findIndex((o) => o.code === selected?.code)));
  };
  const choose = (code: string) => {
    onChange(code);
    setQuery(null);
    setOpen(false);
  };
  // Sortie du champ : nom exact d'un pays → retenu ; champ vidé → effacé ;
  // sinon le pays précédent est réaffiché (aucune saisie libre).
  const leave = () => {
    if (query !== null) {
      const exact = findExactCountry(options, query);
      if (exact) onChange(exact.code);
      else if (!query.trim()) onChange('');
    }
    setQuery(null);
    setOpen(false);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!open) return openList();
      const step = e.key === 'ArrowDown' ? 1 : -1;
      setActive((i) => Math.min(Math.max(i + step, 0), results.length - 1));
    } else if (e.key === 'Enter' && open && results[active]) {
      e.preventDefault();
      choose(results[active].code);
    } else if (e.key === 'Escape' && open) {
      e.preventDefault();
      setQuery(null);
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <input
        id={id ?? autoId}
        type="text"
        role="combobox"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && results[active] ? optionId(results[active].code) : undefined}
        aria-invalid={invalid || undefined}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        className={`input pr-9 ${invalid ? 'border-rose-400' : ''}`}
        placeholder={placeholder}
        value={query ?? selected?.label ?? value ?? ''}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={openList}
        onClick={openList}
        onBlur={leave}
        onKeyDown={onKeyDown}
      />
      <ChevronDown
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
        aria-hidden="true"
      />
      {open && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-label={ariaLabel ?? 'Pays'}
          // Garde le focus dans le champ (clic, défilement, toucher) : le choix se fait au clic.
          onMouseDown={(e) => e.preventDefault()}
          className="absolute z-30 mt-1 max-h-64 w-full overflow-y-auto overscroll-contain rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-950"
        >
          {results.map((o, i) => (
            <li
              key={o.code}
              id={optionId(o.code)}
              role="option"
              aria-selected={o.code === selected?.code}
              data-index={i}
              onClick={() => choose(o.code)}
              onMouseMove={() => setActive(i)}
              className={`flex cursor-pointer items-center justify-between gap-3 px-3 py-2.5 text-sm ${
                i === active ? 'bg-emerald-50 dark:bg-emerald-950/40' : ''
              } ${o.code === selected?.code ? 'font-semibold' : ''}`}
            >
              <span>{o.label}</span>
              <span className="text-xs tabular-nums text-slate-400">{o.code}</span>
            </li>
          ))}
          {results.length === 0 && (
            <li role="presentation" className="px-3 py-2.5 text-sm text-slate-500">
              Aucun pays ne correspond à « {query} ».
            </li>
          )}
        </ul>
      )}
      <p className="sr-only" role="status" aria-live="polite">
        {open && query ? `${results.length} pays trouvé${results.length > 1 ? 's' : ''}` : ''}
      </p>
    </div>
  );
}
