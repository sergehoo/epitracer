'use client';

import { MotionConfig } from 'framer-motion';
import { LocaleProvider, useLocale } from '@/lib/i18n';

function SkipLink() {
  const { t } = useLocale();
  return (
    <a
      href="#contenu"
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-ciForest focus:px-4 focus:py-2 focus:font-bold focus:text-white"
    >
      {t.skip}
    </a>
  );
}

/** Langue FR/EN + animations désactivées si l'utilisateur préfère réduire les mouvements. */
export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <LocaleProvider>
      <MotionConfig reducedMotion="user">
        <SkipLink />
        {children}
      </MotionConfig>
    </LocaleProvider>
  );
}
