'use client';

import { useId, useState } from 'react';
import { Plus } from 'lucide-react';
import { useLocale } from '@/lib/i18n';

/** FAQ interactive (accordéon accessible) — contenus existants, FR/EN. */
export function HomeFaq() {
  const { t } = useLocale();
  const [open, setOpen] = useState<number | null>(0);
  const baseId = useId();
  return (
    <section id="faq" className="scroll-mt-24 bg-slate-50 py-16 sm:py-24" aria-labelledby="faq-title">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <div className="mb-10 text-center">
          <h2 id="faq-title" className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            {t.faq.title}
          </h2>
          <p className="mt-3 text-slate-600">{t.faq.subtitle}</p>
        </div>
        <div className="space-y-3">
          {t.faq.items.map((f, i) => {
            const isOpen = open === i;
            const panelId = `${baseId}-faq-${i}`;
            return (
              <div key={i} className="rounded-2xl border border-slate-200 bg-white shadow-sm">
                <h3>
                  <button
                    type="button"
                    onClick={() => setOpen(isOpen ? null : i)}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    className="flex w-full items-center justify-between gap-4 rounded-2xl p-5 text-left font-bold text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest"
                  >
                    <span>{f.q}</span>
                    <span className={`shrink-0 text-ciForest transition-transform ${isOpen ? 'rotate-45' : ''}`} aria-hidden="true">
                      <Plus className="h-5 w-5" />
                    </span>
                  </button>
                </h3>
                <div id={panelId} role="region" hidden={!isOpen} className="px-5 pb-5 leading-7 text-slate-600">
                  {f.a}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
