import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import {
  AlertTriangle, ArrowLeft, CheckCircle2, Clock, PhoneCall, ShieldCheck, Stethoscope, Waves,
} from 'lucide-react';
import { AlertLevelBadge } from '@/components/public/AlertLevelBadge';
import { NoticeCard } from '@/components/public/NoticeCard';
import { fetchPublicDisease } from '@/lib/portal';

export const revalidate = 300;

type Props = { params: { slug: string } };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  // API indisponible : métadonnées neutres, la page affiche alors error.tsx.
  const disease = await fetchPublicDisease(params.slug).catch(() => undefined);
  if (disease === undefined) return { title: 'Maladies sous surveillance', robots: { index: false } };
  if (!disease) return { title: 'Fiche introuvable', robots: { index: false } };
  const description = disease.description.slice(0, 160);
  return {
    title: `${disease.name} — symptômes, prévention et conseils aux voyageurs`,
    description,
    alternates: { canonical: `/maladies/${disease.slug}` },
    openGraph: { title: disease.name, description, type: 'article', locale: 'fr_FR' },
  };
}

const fmt = (d: string | null) =>
  d ? new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) : '';

export default async function DiseasePage({ params }: Props) {
  const disease = await fetchPublicDisease(params.slug);
  if (!disease) notFound();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'MedicalCondition',
    name: disease.name,
    description: disease.description,
    ...(disease.icd11_code && {
      code: { '@type': 'MedicalCode', code: disease.icd11_code, codingSystem: 'ICD-11' },
    }),
    signOrSymptom: disease.symptoms.map((s) => ({ '@type': 'MedicalSymptom', name: s.label })),
    ...(disease.prevention.length > 0 && { primaryPrevention: disease.prevention.join(' ') }),
  };

  return (
    <article className="bg-gradient-to-br from-white via-orange-50/30 to-emerald-50/50">
      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
      />
      <div className="mx-auto max-w-5xl px-6 py-16">
        <nav aria-label="Fil d'Ariane" className="text-xs text-slate-500">
          <Link href="/" className="hover:text-ciOrange">Accueil</Link> <span aria-hidden="true">›</span>{' '}
          <Link href="/maladies" className="hover:text-ciOrange">Maladies sous surveillance</Link>{' '}
          <span aria-hidden="true">›</span> <span aria-current="page">{disease.name}</span>
        </nav>

        <header className="mt-6">
          <div className="flex flex-wrap items-center gap-3">
            <AlertLevelBadge level={disease.public_alert_level} label={disease.alert_level_label} />
            <span
              className={`rounded-full px-3 py-1 text-[11px] font-black uppercase tracking-wide ring-1 ring-inset ${
                disease.under_surveillance
                  ? 'bg-orange-50 text-ciOrange ring-orange-200'
                  : 'bg-slate-50 text-slate-600 ring-slate-200'
              }`}
            >
              {disease.under_surveillance ? 'Sous surveillance' : 'Information générale'}
            </span>
          </div>
          <h1 className="mt-4 font-display text-4xl font-black leading-tight text-ciDark md:text-5xl">
            {disease.name}
          </h1>
          <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">{disease.description}</p>
        </header>

        <dl className="mt-8 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl bg-white p-4 shadow-sm">
            <dt className="flex items-center gap-1 text-xs text-slate-500"><Clock className="h-3.5 w-3.5" aria-hidden="true" /> Incubation</dt>
            <dd className="mt-1 font-black text-ciDark">
              {disease.incubation_min_days} à {disease.incubation_max_days} jours
            </dd>
          </div>
          <div className="rounded-2xl bg-white p-4 shadow-sm">
            <dt className="flex items-center gap-1 text-xs text-slate-500"><Waves className="h-3.5 w-3.5" aria-hidden="true" /> Transmission</dt>
            <dd className="mt-1 font-black text-ciDark">{disease.transmission.join(', ') || '—'}</dd>
          </div>
          <div className="rounded-2xl bg-white p-4 shadow-sm">
            <dt className="flex items-center gap-1 text-xs text-slate-500"><ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" /> Suivi des voyageurs</dt>
            <dd className="mt-1 font-black text-ciGreen">
              {disease.under_surveillance ? `${disease.followup_days} jours si nécessaire` : 'Pas de suivi en cours'}
            </dd>
          </div>
        </dl>

        {disease.notices.length > 0 && (
          <section aria-labelledby="annonces" className="mt-10">
            <h2 id="annonces" className="font-display text-2xl font-black text-ciDark">Alertes et recommandations</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {disease.notices.map((n) => <NoticeCard key={n.uuid} notice={n} />)}
            </div>
          </section>
        )}

        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          {disease.symptoms.length > 0 && (
            <section aria-labelledby="symptomes" className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm">
              <h2 id="symptomes" className="flex items-center gap-2 font-display text-xl font-black text-ciDark">
                <Stethoscope className="h-5 w-5 text-ciOrange" aria-hidden="true" /> Symptômes
              </h2>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {disease.symptoms.map((s) => (
                  <li key={s.label} className="flex items-start gap-2">
                    {s.is_red_flag
                      ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" aria-label="Signe d'alerte" />
                      : <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-ciOrange" aria-hidden="true" />}
                    <span>{s.label}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {disease.transmission_details && (
            <section aria-labelledby="transmission" className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm">
              <h2 id="transmission" className="flex items-center gap-2 font-display text-xl font-black text-ciDark">
                <Waves className="h-5 w-5 text-ciOrange" aria-hidden="true" /> Transmission
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-700">{disease.transmission_details}</p>
            </section>
          )}

          {disease.prevention.length > 0 && (
            <section aria-labelledby="prevention" className="rounded-3xl border border-emerald-100 bg-emerald-50/60 p-6">
              <h2 id="prevention" className="flex items-center gap-2 font-display text-xl font-black text-ciDark">
                <ShieldCheck className="h-5 w-5 text-ciGreen" aria-hidden="true" /> Prévention
              </h2>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {disease.prevention.map((p) => (
                  <li key={p} className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ciGreen" aria-hidden="true" />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {disease.traveler_recommendations.length > 0 && (
            <section aria-labelledby="recommandations" className="rounded-3xl border border-orange-100 bg-orange-50/60 p-6">
              <h2 id="recommandations" className="flex items-center gap-2 font-display text-xl font-black text-ciDark">
                <CheckCircle2 className="h-5 w-5 text-ciOrange" aria-hidden="true" /> Recommandations aux voyageurs
              </h2>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {disease.traveler_recommendations.map((r) => (
                  <li key={r} className="flex items-start gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-ciOrange" aria-hidden="true" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <aside className="mt-10 flex flex-col gap-4 rounded-3xl bg-ciDark p-8 text-white md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="font-display text-2xl font-black">Besoin d&apos;aide ?</h2>
            <p className="mt-1 text-emerald-100">
              Allô Santé 143 (gratuit) · SAMU 185. Signalez toujours votre voyage au personnel de santé.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <a href="tel:143" className="btn-orange"><PhoneCall className="h-4 w-4" aria-hidden="true" /> Appeler le 143</a>
            <Link href="/voyageur" className="btn-paper">Préparer mon arrivée</Link>
          </div>
        </aside>

        <footer className="mt-8 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <Link href="/maladies" className="inline-flex items-center gap-1 font-bold text-ciOrange hover:underline">
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" /> Toutes les maladies
          </Link>
          {disease.published_at && (
            <span>
              Fiche validée et publiée par les autorités sanitaires le {fmt(disease.published_at)}
              {disease.updated_at && ` · mise à jour le ${fmt(disease.updated_at)}`}
            </span>
          )}
        </footer>
      </div>
    </article>
  );
}
