'use client';

import Link from 'next/link';
import { ArrowRight, ClipboardList, HeartHandshake, QrCode } from 'lucide-react';
import { useLocale } from '@/lib/i18n';
import { Reveal } from './Reveal';

const STEP_ICONS = [ClipboardList, QrCode, HeartHandshake];

/** Parcours en 3 étapes illustrées (icônes Lucide dans des vignettes). */
export function HowItWorks() {
  const { t } = useLocale();
  const h = t.how;
  return (
    <section id="fonctionnement" aria-labelledby="how-title" className="scroll-mt-24 bg-white py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-widest text-orange-800">{h.eyebrow}</p>
          <h2 id="how-title" className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            {h.title}
          </h2>
        </div>
        <div className="relative mt-12">
          {/* Fil conducteur entre les étapes (desktop) */}
          <span className="absolute left-[16%] right-[16%] top-12 hidden h-0.5 bg-gradient-to-r from-ciOrange via-slate-200 to-ciForest md:block" aria-hidden="true" />
          <ol className="relative grid gap-6 md:grid-cols-3">
            {h.steps.map((step, i) => {
              const Icon = STEP_ICONS[i];
              return (
                <Reveal as="li" key={step.title} delay={i * 0.08} className="relative flex flex-col items-center text-center">
                  <span className="relative grid h-24 w-24 place-items-center rounded-[1.75rem] bg-gradient-to-br from-emerald-50 to-orange-50 ring-1 ring-slate-200">
                    <Icon className="h-10 w-10 text-ciForest" aria-hidden="true" />
                    <span className="absolute -right-2 -top-2 grid h-8 w-8 place-items-center rounded-full bg-ciForest text-sm font-black text-white">
                      {i + 1}
                    </span>
                  </span>
                  <h3 className="mt-6 font-display text-xl font-bold text-slate-900">{step.title}</h3>
                  <p className="mt-2 max-w-xs text-sm leading-6 text-slate-600">{step.desc}</p>
                </Reveal>
              );
            })}
          </ol>
        </div>
        <div className="mt-12 text-center">
          <Link
            href="/voyageur"
            className="inline-flex items-center gap-2 rounded-2xl bg-ciForest px-6 py-4 font-bold text-white shadow-lg shadow-emerald-900/20 transition hover:bg-emerald-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest"
          >
            {h.cta} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </section>
  );
}
