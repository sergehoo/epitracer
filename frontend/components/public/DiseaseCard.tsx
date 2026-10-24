import Link from 'next/link';
import { ArrowRight, Stethoscope } from 'lucide-react';
import { AlertLevelBadge } from './AlertLevelBadge';
import type { PublicDisease } from '@/types/portal';

const DEFAULT_LABELS = {
  transmission: 'Transmission',
  followup: 'Suivi des voyageurs',
  days: 'jours',
  notMonitored: 'Non surveillée',
  open: 'Voir la fiche',
};

/** Carte d'une maladie publiée (accueil, page /maladies). */
export function DiseaseCard({
  disease, headingLevel = 3, labels = DEFAULT_LABELS, hideNormalLevel = false, levelLabel,
}: {
  disease: PublicDisease;
  headingLevel?: 2 | 3;
  labels?: typeof DEFAULT_LABELS;
  /** N'affiche le niveau d'alerte que s'il a été relevé (pas la valeur par défaut). */
  hideNormalLevel?: boolean;
  levelLabel?: string;
}) {
  const Heading = headingLevel === 2 ? 'h2' : 'h3';
  const showLevel = !(hideNormalLevel && disease.public_alert_level === 'normal');
  return (
    <article className="group relative flex w-full flex-col rounded-3xl border border-slate-100 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg focus-within:ring-2 focus-within:ring-ciForest">
      <div className="flex items-start justify-between gap-3">
        <div
          className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl text-white"
          style={{ backgroundColor: disease.color || '#064E3B' }}
          aria-hidden="true"
        >
          <Stethoscope className="h-6 w-6" />
        </div>
        {showLevel && (
          <AlertLevelBadge level={disease.public_alert_level} label={levelLabel || disease.alert_level_label} />
        )}
      </div>
      <Heading className="mt-4 font-display text-xl font-black text-ciDark">
        <Link href={`/maladies/${disease.slug}`} className="after:absolute after:inset-0 focus:outline-none">
          {disease.name}
        </Link>
      </Heading>
      <p className="mt-2 flex-1 text-sm leading-6 text-slate-600 line-clamp-4">{disease.description}</p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-xl bg-orange-50 p-2">
          <dt className="text-slate-500">{labels.transmission}</dt>
          <dd className="font-bold text-ciDark">{disease.transmission.join(', ') || '—'}</dd>
        </div>
        <div className="rounded-xl bg-emerald-50 p-2">
          <dt className="text-slate-500">{labels.followup}</dt>
          <dd className="font-bold text-ciForest">
            {disease.under_surveillance ? `${disease.followup_days} ${labels.days}` : labels.notMonitored}
          </dd>
        </div>
      </dl>
      <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-ciForest">
        {labels.open} <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden="true" />
      </span>
    </article>
  );
}
