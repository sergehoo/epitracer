'use client';

import Link from 'next/link';
import { ArrowRight, Bug, Hand, ShieldPlus, Syringe, Utensils } from 'lucide-react';
import { PREVENTION_THEMES, preventionByTheme } from '@/lib/healthContent';
import { useLocale } from '@/lib/i18n';
import { HEALTH_PHOTOS } from '@/lib/landingPhotos';
import type { PublicDiseaseDetail } from '@/types/portal';
import { AdviceList } from './AdviceList';
import { LandingPhoto } from './LandingPhoto';
import { Reveal } from './Reveal';

const THEME_ICONS = { hands: Hand, contact: ShieldPlus, mosquitoes: Bug, foodWater: Utensils, vaccination: Syringe };

// Mosaïque 3 + 2 sur grand écran ; la 5e carte occupe toute la ligne sur tablette.
const SPANS = ['lg:col-span-2', 'lg:col-span-2', 'lg:col-span-2', 'lg:col-span-3', 'sm:col-span-2 lg:col-span-3'];

/**
 * Prévention et protection : cinq thèmes illustrés. Les conseils viennent
 * uniquement des fiches maladies publiées ; un thème sans conseil publié
 * affiche un repli neutre (aucune consigne inventée).
 */
export function PreventionSection({ details }: { details: PublicDiseaseDetail[] }) {
  const { t } = useLocale();
  const p = t.prevention;
  const byTheme = preventionByTheme(details);
  return (
    <section id="prevention" aria-labelledby="prevention-title" className="scroll-mt-24 bg-white py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-bold uppercase tracking-widest text-orange-800">{p.eyebrow}</p>
            <h2 id="prevention-title" className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              {p.title}
            </h2>
            <p className="mt-3 text-slate-600">{p.subtitle}</p>
          </div>
          <Link
            href="/maladies"
            className="inline-flex shrink-0 items-center gap-2 self-start rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-bold text-ciForest transition hover:border-ciForest md:self-auto"
          >
            {p.more} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        <ul className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-6">
          {PREVENTION_THEMES.map((theme, i) => {
            const Icon = THEME_ICONS[theme];
            const item = p.themes[theme];
            const advice = byTheme[theme];
            const headingId = `prevention-${theme}`;
            return (
              <Reveal as="li" key={theme} delay={i * 0.05} className={`flex ${SPANS[i]}`}>
                <article
                  aria-labelledby={headingId}
                  className="flex w-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-xl"
                >
                  <div className="relative aspect-[16/9] bg-emerald-50">
                    <LandingPhoto
                      src={HEALTH_PHOTOS[theme].src}
                      alt={item.alt}
                      sizes="(min-width: 1024px) 40vw, (min-width: 640px) 50vw, 100vw"
                    />
                    <span
                      className="absolute left-4 top-4 grid h-11 w-11 place-items-center rounded-2xl bg-white/95 text-ciForest shadow-md ring-1 ring-slate-900/5"
                      aria-hidden="true"
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                  </div>
                  <div className="flex flex-1 flex-col p-6">
                    <h3 id={headingId} className="font-display text-lg font-bold text-slate-900">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-6 text-slate-600">{item.desc}</p>
                    {advice.length > 0 ? (
                      <div className="mt-4 border-t border-slate-100 pt-4">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{p.published}</p>
                        <AdviceList items={advice.slice(0, 3)} className="mt-3" />
                      </div>
                    ) : (
                      <p className="mt-4 rounded-2xl bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                        {p.none}{' '}
                        <a href="tel:143" className="font-bold text-ciForest underline underline-offset-2">143</a>.
                      </p>
                    )}
                  </div>
                </article>
              </Reveal>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
