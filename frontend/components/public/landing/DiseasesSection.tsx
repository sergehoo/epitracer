'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowRight, Megaphone, ShieldCheck, Stethoscope } from 'lucide-react';
import { DiseaseCard } from '@/components/public/DiseaseCard';
import { NoticeCard } from '@/components/public/NoticeCard';
import { useLocale } from '@/lib/i18n';
import { ALERT_LEVEL_ORDER, fetchPublicDiseases, fetchPublicNotices } from '@/lib/portal';
import type { PublicDisease, PublicNotice } from '@/types/portal';
import { Reveal } from './Reveal';

const EN_LEVELS: Record<string, string> = {
  normal: 'Watch', moderate: 'Vigilance', high: 'Alert', critical: 'Health emergency',
};

/**
 * Maladies sous surveillance — uniquement les contenus PUBLIÉS par les
 * administrateurs habilités (API /public/). Données rendues côté serveur en
 * français ; en anglais, les traductions publiées sont rechargées (repli FR).
 * Le niveau d'alerte n'est affiché que s'il a été explicitement relevé.
 */
export function DiseasesSection({
  diseases: initialDiseases, notices: initialNotices,
}: {
  diseases: PublicDisease[];
  notices: PublicNotice[];
}) {
  const { t, locale } = useLocale();
  const d = t.diseases;
  const [diseases, setDiseases] = useState(initialDiseases);
  const [notices, setNotices] = useState(initialNotices);

  useEffect(() => {
    if (locale === 'fr') {
      setDiseases(initialDiseases);
      setNotices(initialNotices);
      return;
    }
    let alive = true;
    Promise.all([fetchPublicDiseases('?active=true&lang=en'), fetchPublicNotices(undefined, 'en')]).then(
      ([ds, ns]) => {
        if (!alive) return;
        // Liste vide = API momentanément injoignable : on garde le contenu déjà affiché.
        if (ds.length) setDiseases(ds);
        if (ns.length) setNotices(ns);
      },
    );
    return () => { alive = false; };
  }, [locale, initialDiseases, initialNotices]);

  const alerts = notices
    .filter((n) => n.kind === 'alert')
    .sort((a, b) => ALERT_LEVEL_ORDER.indexOf(a.alert_level) - ALERT_LEVEL_ORDER.indexOf(b.alert_level));
  const recommendations = notices.filter((n) => n.kind === 'recommendation');

  return (
    <section id="maladies" aria-labelledby="maladies-title" className="scroll-mt-24 bg-slate-50 py-16 sm:py-24">
      {/* Ancre historique (anciens liens /#ebola) */}
      <span id="ebola" className="sr-only" aria-hidden="true" />
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-ciForest">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" /> {d.eyebrow}
            </p>
            <h2 id="maladies-title" className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              {d.title}
            </h2>
            <p className="mt-3 text-slate-600">{d.subtitle}</p>
          </div>
          <Link
            href="/maladies"
            className="inline-flex shrink-0 items-center gap-2 self-start rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-bold text-ciForest transition hover:border-ciForest md:self-auto"
          >
            {d.all} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        {alerts.length > 0 && (
          <div className="mt-10" role="region" aria-labelledby="alertes-title">
            <h3 id="alertes-title" className="inline-flex items-center gap-2 font-display text-xl font-bold text-slate-900">
              <Megaphone className="h-5 w-5 text-orange-700" aria-hidden="true" /> {d.alerts}
            </h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {alerts.slice(0, 4).map((n) => <NoticeCard key={n.uuid} notice={n} locale={locale} />)}
            </div>
          </div>
        )}

        {diseases.length > 0 ? (
          <ul className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {diseases.slice(0, 6).map((dz, i) => (
              <Reveal as="li" key={dz.slug} delay={i * 0.05} className="flex">
                <DiseaseCard
                  disease={dz}
                  hideNormalLevel
                  levelLabel={locale === 'en' ? EN_LEVELS[dz.public_alert_level] : undefined}
                  labels={{
                    transmission: d.transmission, followup: d.followup, days: d.days,
                    notMonitored: d.notMonitored, open: d.open,
                  }}
                />
              </Reveal>
            ))}
          </ul>
        ) : (
          <div className="mt-10 flex items-start gap-4 rounded-3xl border border-slate-200 bg-white p-6">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-emerald-50 text-ciForest" aria-hidden="true">
              <Stethoscope className="h-5 w-5" />
            </span>
            <p className="text-slate-700">
              {d.empty}{' '}
              <a href="tel:143" className="font-bold text-ciForest underline underline-offset-2">143</a>.
            </p>
          </div>
        )}

        {recommendations.length > 0 && (
          <div className="mt-12" role="region" aria-labelledby="recos-title">
            <h3 id="recos-title" className="font-display text-xl font-bold text-slate-900">{d.recommendations}</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recommendations.slice(0, 6).map((n) => <NoticeCard key={n.uuid} notice={n} locale={locale} />)}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
