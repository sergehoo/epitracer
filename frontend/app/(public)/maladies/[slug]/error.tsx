'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { startTransition, useEffect } from 'react';
import { ArrowLeft, PhoneCall, RefreshCw } from 'lucide-react';
import { DISEASE_TEXT } from '@/lib/diseasePageText';
import { useLocale } from '@/lib/i18n';

/**
 * Fiche maladie impossible à charger (API publique injoignable) : message
 * clair et numéros d'urgence au lieu de l'écran « Application error ».
 */
export default function DiseaseError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();
  const T = DISEASE_TEXT[useLocale().locale];
  useEffect(() => {
    console.error(error);
  }, [error]);
  // L'erreur vient du rendu serveur : refresh() refait la requête, reset() réaffiche.
  const retry = () => startTransition(() => {
    router.refresh();
    reset();
  });

  return (
    <div className="bg-gradient-to-br from-white via-orange-50/30 to-emerald-50/50">
      <div className="mx-auto max-w-3xl px-6 py-20">
        <nav aria-label={T.breadcrumb} className="text-xs text-slate-500">
          <Link href="/" className="hover:text-ciOrange">{T.home}</Link> <span aria-hidden="true">›</span>{' '}
          <Link href="/maladies" className="hover:text-ciOrange">{T.diseases}</Link>
        </nav>
        <div role="alert" className="mt-6 rounded-3xl border border-slate-100 bg-white p-8 shadow-sm">
          <h1 className="font-display text-3xl font-black text-ciDark">{T.errorTitle}</h1>
          <p className="mt-4 leading-7 text-slate-600">{T.errorText}</p>
          <p className="mt-3 leading-7 text-slate-600">{T.errorHelp}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={retry} className="btn-orange">
              <RefreshCw className="h-4 w-4" aria-hidden="true" /> {T.retry}
            </button>
            <a href="tel:143" className="btn-paper">
              <PhoneCall className="h-4 w-4" aria-hidden="true" /> {T.call}
            </a>
            <Link href="/maladies" className="btn-paper">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" /> {T.allSheets}
            </Link>
          </div>
          {error.digest && (
            <p className="mt-6 text-xs text-slate-400">{T.reference} : {error.digest}</p>
          )}
        </div>
      </div>
    </div>
  );
}
