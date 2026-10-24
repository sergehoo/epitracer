'use client';

import Link from 'next/link';
import {
  Activity, AlertTriangle, ArrowRight, BatteryLow, Bone, Brain, ClipboardPlus, Droplet, Eye, LifeBuoy,
  PhoneCall, Thermometer, Wind, type LucideIcon,
} from 'lucide-react';
import { travelerAdvice, watchedSymptoms } from '@/lib/healthContent';
import { useLocale } from '@/lib/i18n';
import { HEALTH_PHOTOS } from '@/lib/landingPhotos';
import type { PublicDiseaseDetail } from '@/types/portal';
import { AdviceList } from './AdviceList';
import { LandingPhoto } from './LandingPhoto';
import { Reveal } from './Reveal';

const MAX_SYMPTOMS = 12;

// Pictogramme indicatif d'après le libellé publié (FR/EN) ; à défaut, pictogramme générique.
const SYMPTOM_ICONS: [RegExp, LucideIcon][] = [
  [/fievre|fever|temperature/, Thermometer],
  [/saign|sang|bleed|blood/, Droplet],
  [/toux|cough|respir|gorge|throat|souffle|breath/, Wind],
  [/cephal|\btete\b|headache/, Brain],
  [/fatigue|faiblesse|weak|tired/, BatteryLow],
  [/yeux|\boeil|\beyes?\b/, Eye],
  [/muscul|articul|douleur|pain|ache|joint/, Bone],
];
const iconFor = (label: string) => {
  const text = label.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  return SYMPTOM_ICONS.find(([re]) => re.test(text))?.[1] ?? Activity;
};

/**
 * Symptômes et conduite à tenir : signes publiés dans les fiches (signes
 * d'alerte d'abord), conseils publiés, puis les canaux existants — Allô Santé
 * 143, SAMU 185, signalement du suivi et assistance.
 */
export function SymptomsSection({ details }: { details: PublicDiseaseDetail[] }) {
  const { t } = useLocale();
  const s = t.symptoms;
  const symptoms = watchedSymptoms(details);
  const advice = travelerAdvice(details).symptoms;
  const hidden = symptoms.length - MAX_SYMPTOMS;

  const actions = [
    { href: 'tel:143', icon: PhoneCall, title: `${s.health} 143`, note: s.healthNote, tone: 'bg-emerald-50 text-ciForest' },
    { href: 'tel:185', icon: PhoneCall, title: `${s.samu} 185`, note: s.samuNote, tone: 'bg-orange-50 text-orange-800' },
    { href: '/voyageur/suivi', icon: ClipboardPlus, title: s.report, note: s.reportNote, tone: 'bg-emerald-50 text-ciForest' },
    { href: '/assistance', icon: LifeBuoy, title: s.assistance, note: s.assistanceNote, tone: 'bg-orange-50 text-orange-800' },
  ];

  return (
    <section id="symptomes" aria-labelledby="symptomes-title" className="scroll-mt-24 bg-slate-50 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-widest text-orange-800">{s.eyebrow}</p>
          <h2 id="symptomes-title" className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            {s.title}
          </h2>
          <p className="mt-3 text-slate-600">{s.subtitle}</p>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.15fr,1fr]">
          <Reveal as="article" className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
            <div className="relative aspect-[21/9] bg-emerald-50">
              <LandingPhoto src={HEALTH_PHOTOS.thermometer.src} alt={s.photoAlt} sizes="(min-width: 1024px) 55vw, 100vw" />
            </div>
            <div className="p-6">
              <h3 className="font-display text-xl font-bold text-slate-900">{s.watch}</h3>
              {symptoms.length > 0 ? (
                <>
                  <ul className="mt-4 grid grid-cols-2 gap-2">
                    {symptoms.slice(0, MAX_SYMPTOMS).map((sym) => {
                      const Icon = iconFor(sym.label);
                      return (
                        <li
                          key={sym.label}
                          className={`flex items-center gap-2 rounded-2xl px-2.5 py-2 text-[13px] leading-tight sm:gap-3 sm:px-3 sm:py-2.5 sm:text-sm ${
                            sym.redFlag ? 'bg-orange-50 ring-1 ring-orange-200' : 'bg-slate-50'
                          }`}
                        >
                          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-white text-ciForest ring-1 ring-slate-200 sm:h-9 sm:w-9" aria-hidden="true">
                            <Icon className="h-4 w-4" />
                          </span>
                          <span className="font-semibold text-slate-800">
                            {sym.label}
                            {sym.redFlag && (
                              <span className="mt-0.5 flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-orange-800">
                                <AlertTriangle className="h-3 w-3" aria-hidden="true" /> {s.redFlag}
                              </span>
                            )}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="mt-4 text-xs leading-5 text-slate-500">
                    {s.from} :{' '}
                    {details.map((d, i) => (
                      <span key={d.slug}>
                        {i > 0 && ', '}
                        <Link href={`/maladies/${d.slug}`} className="font-bold text-ciForest hover:underline">
                          {d.short_name || d.name}
                        </Link>
                      </span>
                    ))}
                    {hidden > 0 && <> · +{hidden} {s.moreSigns}</>}
                  </p>
                </>
              ) : (
                <p className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">{s.empty}</p>
              )}
            </div>
          </Reveal>

          <Reveal as="article" delay={0.08} className="flex flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="font-display text-xl font-bold text-slate-900">{s.conduct}</h3>
            {advice.length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{s.advice}</p>
                <AdviceList items={advice} className="mt-3" />
              </div>
            )}
            <ul className="mt-6 grid gap-3 sm:grid-cols-2">
              {actions.map((a) => {
                const Icon = a.icon;
                const inner = (
                  <>
                    <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${a.tone}`} aria-hidden="true">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span>
                      <span className="block font-bold text-slate-900">{a.title}</span>
                      <span className="block text-xs text-slate-600">{a.note}</span>
                    </span>
                  </>
                );
                const cls = 'flex h-full items-center gap-3 rounded-2xl border border-slate-200 p-3 transition hover:border-ciForest/40 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest';
                return (
                  <li key={a.href}>
                    {a.href.startsWith('tel:')
                      ? <a href={a.href} className={cls}>{inner}</a>
                      : <Link href={a.href} className={cls}>{inner}</Link>}
                  </li>
                );
              })}
            </ul>
            <p className="mt-auto pt-6 text-xs text-slate-500">{s.disclaimer}</p>
            <Link href="/maladies" className="mt-2 inline-flex items-center gap-1 self-start text-sm font-bold text-ciForest hover:underline">
              {t.prevention.more} <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
