'use client';

import Link from 'next/link';
import { ArrowRight, ClipboardList, HeartPulse, LifeBuoy, QrCode } from 'lucide-react';
import { useLocale } from '@/lib/i18n';
import { Reveal } from './Reveal';

const SERVICES = [
  { href: '/voyageur', icon: ClipboardList, tone: 'bg-emerald-50 text-ciForest' },
  { href: '/pass', icon: QrCode, tone: 'bg-orange-50 text-orange-800' },
  { href: '/voyageur/suivi', icon: HeartPulse, tone: 'bg-emerald-50 text-ciForest' },
  { href: '/assistance', icon: LifeBuoy, tone: 'bg-orange-50 text-orange-800' },
];

export function QuickServices() {
  const { t } = useLocale();
  const s = t.services;
  return (
    <section id="services" aria-labelledby="services-title" className="scroll-mt-24 bg-white py-16 sm:py-20">
      {/* Ancres historiques conservées pour les anciens liens */}
      <span id="accompagnement" className="sr-only" aria-hidden="true" />
      <span id="urgence" className="sr-only" aria-hidden="true" />
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="max-w-2xl">
          <h2 id="services-title" className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">{s.title}</h2>
          <p className="mt-3 text-slate-600">{s.subtitle}</p>
        </div>
        <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SERVICES.map((svc, i) => {
            const item = s.items[i];
            const Icon = svc.icon;
            return (
              <Reveal as="li" key={svc.href} delay={i * 0.05}>
                <Link
                  href={svc.href}
                  className="group flex h-full flex-col rounded-3xl border border-slate-200 bg-white p-6 transition hover:-translate-y-1 hover:border-ciForest/40 hover:shadow-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest"
                >
                  <span className={`grid h-12 w-12 place-items-center rounded-2xl ${svc.tone}`} aria-hidden="true">
                    <Icon className="h-6 w-6" />
                  </span>
                  <span className="mt-5 font-display text-lg font-bold text-slate-900">{item.title}</span>
                  <span className="mt-2 flex-1 text-sm leading-6 text-slate-600">{item.desc}</span>
                  <span className="mt-5 inline-flex items-center gap-1 text-sm font-bold text-ciForest">
                    {item.cta}
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" aria-hidden="true" />
                  </span>
                </Link>
              </Reveal>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
