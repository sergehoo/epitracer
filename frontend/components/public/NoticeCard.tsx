import Link from 'next/link';
import { Globe2, Megaphone, ShieldCheck } from 'lucide-react';
import { AlertLevelBadge } from './AlertLevelBadge';
import type { PublicNotice } from '@/types/portal';

const LABELS = {
  fr: { alert: 'Alerte sanitaire', reco: 'Recommandation', sheet: 'Fiche', published: 'Publiée le', date: 'fr-FR' },
  en: { alert: 'Health alert', reco: 'Advice', sheet: 'Fact sheet', published: 'Published on', date: 'en-GB' },
};

/** Alerte sanitaire ou recommandation publiée par les autorités. */
export function NoticeCard({ notice, locale = 'fr' }: { notice: PublicNotice; locale?: 'fr' | 'en' }) {
  const L = LABELS[locale];
  const fmt = (d: string | null) =>
    d ? new Date(d).toLocaleDateString(L.date, { day: 'numeric', month: 'long', year: 'numeric' }) : '';
  const isAlert = notice.kind === 'alert';
  const Icon = isAlert ? Megaphone : ShieldCheck;
  return (
    <article
      className={`rounded-3xl border p-6 shadow-sm ${
        isAlert ? 'border-orange-200 bg-orange-50/60' : 'border-emerald-100 bg-white'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Icon className={`h-5 w-5 ${isAlert ? 'text-orange-700' : 'text-ciForest'}`} aria-hidden="true" />
        <span className="text-[11px] font-black uppercase tracking-wide text-slate-500">
          {isAlert ? L.alert : L.reco}
        </span>
        {isAlert && <AlertLevelBadge level={notice.alert_level} label={notice.alert_level_label} />}
      </div>
      <h3 className="mt-3 font-display text-lg font-black text-ciDark">{notice.title}</h3>
      {notice.summary && <p className="mt-2 text-sm font-semibold text-slate-700">{notice.summary}</p>}
      {notice.body && <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{notice.body}</p>}
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500">
        {notice.countries.length > 0 && (
          <span className="inline-flex items-center gap-1">
            <Globe2 className="h-3.5 w-3.5" aria-hidden="true" />
            {notice.countries.map((c) => c.name).join(', ')}
          </span>
        )}
        {notice.disease && (
          <Link href={`/maladies/${notice.disease.slug}`} className="font-bold text-ciForest hover:underline">
            {L.sheet} : {notice.disease.name}
          </Link>
        )}
        {notice.published_at && <time dateTime={notice.published_at}>{L.published} {fmt(notice.published_at)}</time>}
      </div>
    </article>
  );
}
