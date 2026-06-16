'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  /** Page courante (1-indexée) */
  page: number;
  /** Nombre total d'éléments */
  total: number;
  /** Taille de page */
  pageSize: number;
  /** Callback changement de page */
  onPageChange: (next: number) => void;
  /** Texte personnalisable (ex: "voyageur(s)", "utilisateur(s)") */
  itemLabel?: string;
  /** Cacher si une seule page */
  hideIfSinglePage?: boolean;
}

/**
 * Pagination réutilisable — compteur "X éléments · page Y / Z" + boutons
 * Préc / Suiv et numéros de page avec fenêtre glissante ±1.
 */
export function Pagination({
  page,
  total,
  pageSize,
  onPageChange,
  itemLabel = 'élément(s)',
  hideIfSinglePage = false,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safe = Math.min(page, totalPages);

  if (hideIfSinglePage && totalPages <= 1) return null;

  const setPage = (p: number) => {
    if (p < 1 || p > totalPages || p === safe) return;
    onPageChange(p);
  };

  return (
    <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 px-4 py-3 text-sm">
      <div className="text-xs text-slate-500">
        {total.toLocaleString('fr-FR')} {itemLabel} · page {safe} / {totalPages}
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => setPage(safe - 1)}
          disabled={safe === 1}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          <ChevronLeft className="h-3.5 w-3.5" /> Préc.
        </button>
        {Array.from({ length: totalPages }).map((_, i) => {
          const num = i + 1;
          const showAlways = num === 1 || num === totalPages;
          const inWindow = Math.abs(num - safe) <= 1;
          if (!showAlways && !inWindow) {
            if (num === safe - 2 || num === safe + 2) {
              return <span key={num} className="px-1 text-slate-400 text-xs">…</span>;
            }
            return null;
          }
          return (
            <button
              key={num}
              onClick={() => setPage(num)}
              className={`min-w-[32px] px-2 py-1 rounded-lg text-xs font-bold transition ${
                num === safe
                  ? 'bg-ciOrange text-white'
                  : 'border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              {num}
            </button>
          );
        })}
        <button
          onClick={() => setPage(safe + 1)}
          disabled={safe === totalPages}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          Suiv. <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

/** Helper : tranche un tableau pour la page donnée */
export function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}
