import Link from 'next/link';
import { CheckCircle2 } from 'lucide-react';
import type { SourcedAdvice } from '@/lib/healthContent';

/** Conseils publiés, cités tels quels, avec un lien vers chaque fiche source. */
export function AdviceList({ items, className = '' }: { items: SourcedAdvice[]; className?: string }) {
  return (
    <ul className={`space-y-3 ${className}`}>
      {items.map((a) => (
        <li key={a.text} className="flex gap-2.5 text-sm leading-6 text-slate-700">
          <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-ciForest" aria-hidden="true" />
          <span>
            {a.text}{' '}
            {a.sources.map((s) => (
              <Link
                key={s.slug}
                href={`/maladies/${s.slug}`}
                className="ml-1 inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 align-middle text-[11px] font-bold text-ciForest ring-1 ring-emerald-100 transition hover:bg-emerald-100"
              >
                {s.name}
              </Link>
            ))}
          </span>
        </li>
      ))}
    </ul>
  );
}
