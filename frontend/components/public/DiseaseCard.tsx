import Link from 'next/link';
import { ArrowRight, Stethoscope } from 'lucide-react';
import { AlertLevelBadge } from './AlertLevelBadge';
import type { PublicDisease } from '@/types/portal';

/** Carte d'une maladie publiée (accueil, page /maladies). */
export function DiseaseCard({ disease, headingLevel = 3 }: { disease: PublicDisease; headingLevel?: 2 | 3 }) {
  const Heading = headingLevel === 2 ? 'h2' : 'h3';
  return (
    <article className="group relative flex flex-col rounded-3xl border border-slate-100 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg focus-within:ring-2 focus-within:ring-ciOrange">
      <div className="flex items-start justify-between gap-3">
        <div
          className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl text-white"
          style={{ backgroundColor: disease.color || '#064E3B' }}
          aria-hidden="true"
        >
          <Stethoscope className="h-6 w-6" />
        </div>
        <AlertLevelBadge level={disease.public_alert_level} label={disease.alert_level_label} />
      </div>
      <Heading className="mt-4 font-display text-xl font-black text-ciDark">
        <Link href={`/maladies/${disease.slug}`} className="after:absolute after:inset-0 focus:outline-none">
          {disease.name}
        </Link>
      </Heading>
      <p className="mt-2 flex-1 text-sm leading-6 text-slate-600 line-clamp-4">{disease.description}</p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-xl bg-orange-50 p-2">
          <dt className="text-slate-500">Transmission</dt>
          <dd className="font-bold text-ciDark">{disease.transmission.join(', ') || '—'}</dd>
        </div>
        <div className="rounded-xl bg-emerald-50 p-2">
          <dt className="text-slate-500">Suivi des voyageurs</dt>
          <dd className="font-bold text-ciGreen">
            {disease.under_surveillance ? `${disease.followup_days} jours` : 'Non surveillée'}
          </dd>
        </div>
      </dl>
      <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-ciOrange">
        Voir la fiche <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden="true" />
      </span>
    </article>
  );
}
