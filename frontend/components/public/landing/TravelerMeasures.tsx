'use client';

import Link from 'next/link';
import { ArrowRight, HeartHandshake, Info, MapPin, Megaphone, PlaneLanding, PlaneTakeoff } from 'lucide-react';
import { followupDurations, travelerAdvice } from '@/lib/healthContent';
import { useLocale } from '@/lib/i18n';
import { HEALTH_PHOTOS } from '@/lib/landingPhotos';
import type { PublicDisease, PublicDiseaseDetail, PublicNotice } from '@/types/portal';
import { AdviceList } from './AdviceList';
import { LandingPhoto } from './LandingPhoto';
import { Reveal } from './Reveal';

const STEPS = [
  { icon: PlaneTakeoff, href: '/voyageur' },
  { icon: PlaneLanding, href: '/pass' },
  { icon: HeartHandshake, href: '/voyageur/suivi' },
];

/**
 * Mesures sanitaires voyageurs : Avant le départ → À l'arrivée → Pendant le
 * séjour. Les démarches sont celles du dispositif (parcours existants) ; durées
 * de suivi et recommandations proviennent uniquement des contenus publiés.
 */
export function TravelerMeasures({
  diseases, details, notices,
}: {
  diseases: PublicDisease[];
  details: PublicDiseaseDetail[];
  notices: PublicNotice[];
}) {
  const { t } = useLocale();
  const m = t.measures;
  const durations = followupDurations(diseases);
  const stayAdvice = travelerAdvice(details).stay;
  const hasAlerts = notices.some((n) => n.kind === 'alert');
  const hasRecos = notices.some((n) => n.kind === 'recommendation');

  return (
    <section id="mesures" aria-labelledby="mesures-title" className="scroll-mt-24 bg-gradient-to-b from-emerald-50/60 to-white py-16 sm:py-24">
      {/* Ancre historique de « Comment ça marche » (menu, anciens liens) */}
      <span id="fonctionnement" className="sr-only" aria-hidden="true" />
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="grid items-center gap-8 lg:grid-cols-[1.1fr,1fr] lg:gap-12">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-orange-800">{m.eyebrow}</p>
            <h2 id="mesures-title" className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              {m.title}
            </h2>
            <p className="mt-3 max-w-xl text-slate-600">{m.subtitle}</p>
            <p className="mt-5 flex max-w-xl gap-2.5 rounded-2xl bg-white p-4 text-sm leading-6 text-slate-700 ring-1 ring-emerald-100">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-ciForest" aria-hidden="true" /> {m.note}
            </p>
          </div>
          <div className="relative aspect-[16/10] overflow-hidden rounded-[2rem] bg-emerald-100 shadow-[0_24px_60px_-28px_rgba(2,44,34,0.45)] ring-1 ring-slate-900/5">
            <LandingPhoto src={HEALTH_PHOTOS.airport.src} alt={m.photoAlt} sizes="(min-width: 1024px) 45vw, 100vw" />
            <p className="absolute bottom-4 left-4 inline-flex items-center gap-1 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-slate-800 shadow-sm backdrop-blur">
              <MapPin className="h-3.5 w-3.5 text-ciForest" aria-hidden="true" /> {m.place}
            </p>
          </div>
        </div>

        <div className="relative mt-12">
          {/* Fil conducteur Avant → Arrivée → Séjour, à hauteur des pictogrammes (desktop) */}
          <span className="absolute left-[16%] right-[16%] top-14 hidden h-0.5 bg-gradient-to-r from-ciOrange via-slate-200 to-ciForest lg:block" aria-hidden="true" />
          <ol className="relative grid gap-5 lg:grid-cols-3">
            {STEPS.map((step, i) => {
              const s = m.steps[i];
              const Icon = step.icon;
              return (
                <Reveal as="li" key={s.phase} delay={i * 0.08} className="flex">
                  <article className="flex w-full flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div className="flex items-center gap-3">
                      <span className="relative grid h-16 w-16 shrink-0 place-items-center rounded-[1.25rem] bg-gradient-to-br from-emerald-50 to-orange-50 ring-1 ring-slate-200" aria-hidden="true">
                        <Icon className="h-7 w-7 text-ciForest" />
                        <span className="absolute -right-2 -top-2 grid h-7 w-7 place-items-center rounded-full bg-ciForest text-xs font-black text-white">
                          {i + 1}
                        </span>
                      </span>
                      <p className="text-xs font-bold uppercase tracking-widest text-orange-800">{s.phase}</p>
                    </div>
                    <h3 className="mt-5 font-display text-xl font-bold text-slate-900">{s.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{s.desc}</p>

                    {i === 0 && (hasAlerts || hasRecos) && (
                      <ul className="mt-4 space-y-2 text-sm">
                        {hasAlerts && (
                          <li>
                            <a href="#alertes" className="inline-flex items-center gap-2 font-semibold text-orange-800 hover:underline">
                              <Megaphone className="h-4 w-4" aria-hidden="true" /> {m.alerts}
                            </a>
                          </li>
                        )}
                        {hasRecos && (
                          <li>
                            <a href="#recommandations" className="inline-flex items-center gap-2 font-semibold text-ciForest hover:underline">
                              <ArrowRight className="h-4 w-4" aria-hidden="true" /> {m.recos}
                            </a>
                          </li>
                        )}
                      </ul>
                    )}

                    {i === 2 && durations.length > 0 && (
                      <div className="mt-4 rounded-2xl bg-emerald-50 p-3">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{m.followup}</p>
                        <ul className="mt-2 flex flex-wrap gap-2">
                          {durations.map((d) => (
                            <li key={d.slug}>
                              <Link href={`/maladies/${d.slug}`} className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-bold text-ciForest ring-1 ring-emerald-100 hover:ring-ciForest">
                                {d.name} · {d.days} {m.days}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {i === 2 && stayAdvice.length > 0 && (
                      <div className="mt-4">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{m.published}</p>
                        <AdviceList items={stayAdvice.slice(0, 3)} className="mt-3" />
                      </div>
                    )}

                    <Link
                      href={step.href}
                      className="mt-auto inline-flex items-center gap-1 pt-6 text-sm font-bold text-ciForest hover:underline"
                    >
                      {s.cta} <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  </article>
                </Reveal>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}
