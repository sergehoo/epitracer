'use client';

import Link from 'next/link';
import { Activity, ArrowRight, CalendarClock, ClipboardCheck, Megaphone, ShieldCheck, Stethoscope } from 'lucide-react';
import { DiseaseCard } from '@/components/public/DiseaseCard';
import { NoticeCard } from '@/components/public/NoticeCard';
import { formatDate, lastUpdate } from '@/lib/healthContent';
import { useLocale } from '@/lib/i18n';
import { ALERT_LEVEL_ORDER } from '@/lib/portal';
import type { PublicDisease, PublicNotice } from '@/types/portal';
import { Reveal } from './Reveal';

const EN_LEVELS: Record<string, string> = {
  normal: 'Watch', moderate: 'Vigilance', high: 'Alert', critical: 'Health emergency',
};

/**
 * Alertes et surveillance sanitaire — uniquement les contenus PUBLIÉS par les
 * administrateurs habilités (API /public/), déjà localisés par le parent
 * (HealthHub). Le niveau d'alerte n'est affiché que s'il a été explicitement
 * relevé ; compteurs et date de mise à jour sont calculés sur ces contenus.
 */
export function DiseasesSection({ diseases, notices }: { diseases: PublicDisease[]; notices: PublicNotice[] }) {
  const { t, locale } = useLocale();
  const d = t.diseases;

  const alerts = notices
    .filter((n) => n.kind === 'alert')
    .sort((a, b) => ALERT_LEVEL_ORDER.indexOf(a.alert_level) - ALERT_LEVEL_ORDER.indexOf(b.alert_level));
  const recommendations = notices.filter((n) => n.kind === 'recommendation');
  const updated = lastUpdate(diseases, notices);
  const stats = [
    { icon: Megaphone, value: String(alerts.length), label: d.statAlerts, tone: 'bg-orange-50 text-orange-800' },
    { icon: Activity, value: String(diseases.length), label: d.statDiseases, tone: 'bg-emerald-50 text-ciForest' },
    { icon: ClipboardCheck, value: String(recommendations.length), label: d.statRecos, tone: 'bg-emerald-50 text-ciForest' },
    {
      icon: CalendarClock, value: updated ? formatDate(updated, locale) : d.noDate, label: d.statUpdated,
      tone: 'bg-orange-50 text-orange-800', dateTime: updated ?? undefined,
    },
  ];

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

        <dl className="mt-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {stats.map((st) => {
            const Icon = st.icon;
            return (
              // dl > div > (dt, dd) : le pictogramme est positionné dans le dt.
              <div key={st.label} className="relative flex min-h-[4.75rem] flex-col justify-center rounded-2xl border border-slate-200 bg-white py-3 pl-[4.25rem] pr-3">
                <dt className="text-xs text-slate-500">
                  <span className={`absolute left-4 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-xl ${st.tone}`} aria-hidden="true">
                    <Icon className="h-5 w-5" />
                  </span>
                  {st.label}
                </dt>
                <dd className="font-display text-base font-extrabold leading-tight text-slate-900 sm:text-lg">
                  {st.dateTime ? <time dateTime={st.dateTime}>{st.value}</time> : st.value}
                </dd>
              </div>
            );
          })}
        </dl>
        <p className="mt-4 flex flex-wrap items-center gap-3 text-xs font-semibold text-slate-600">
          <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 ring-1 ring-slate-200">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-min-sante-2.png" alt="" className="h-6 w-6 object-contain" />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-INHP.png" alt="" className="h-6 w-auto object-contain" />
            {d.source} : MSHPCMU · INHP
          </span>
          {d.langNote && <span className="font-normal text-slate-500">{d.langNote}</span>}
        </p>

        {alerts.length > 0 && (
          <div id="alertes" className="mt-10 scroll-mt-24" role="region" aria-labelledby="alertes-title">
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
                  updatedLabel={`${d.updatedOn} ${formatDate(dz.updated_at, locale)}`}
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
          <div id="recommandations" className="mt-12 scroll-mt-24" role="region" aria-labelledby="recos-title">
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
