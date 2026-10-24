import type { Metadata } from 'next';
import Link from 'next/link';
import { PhoneCall, ShieldCheck } from 'lucide-react';
import { DiseaseExplorer } from '@/components/public/DiseaseExplorer';
import { NoticeCard } from '@/components/public/NoticeCard';
import { fetchPublicDiseases, fetchPublicNotices } from '@/lib/portal';

export const revalidate = 300;

export const metadata: Metadata = {
  title: 'Maladies sous surveillance',
  description:
    "Fiches d'information des maladies surveillées en Côte d'Ivoire : symptômes, transmission, prévention, recommandations aux voyageurs et niveau d'alerte. MSHPCMU · INHP.",
  alternates: { canonical: '/maladies' },
  openGraph: {
    title: "Maladies sous surveillance — Destination Côte d'Ivoire",
    description: 'Informations sanitaires validées par le MSHPCMU et l’INHP pour les voyageurs.',
    type: 'website',
    locale: 'fr_FR',
  },
};

export default async function MaladiesPage() {
  const [diseases, alerts] = await Promise.all([fetchPublicDiseases(), fetchPublicNotices('alert')]);
  return (
    <div className="bg-gradient-to-br from-white via-orange-50/30 to-emerald-50/50">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <nav aria-label="Fil d'Ariane" className="text-xs text-slate-500">
          <Link href="/" className="hover:text-ciOrange">Accueil</Link> <span aria-hidden="true">›</span>{' '}
          <span aria-current="page">Maladies sous surveillance</span>
        </nav>
        <header className="mt-6 max-w-3xl">
          <span className="pill-green">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" /> Information sanitaire officielle
          </span>
          <h1 className="mt-5 font-display text-4xl font-black leading-tight text-ciDark md:text-5xl">
            Maladies sous surveillance
          </h1>
          <p className="mt-4 leading-8 text-slate-600">
            Retrouvez pour chaque maladie les symptômes à connaître, les modes de transmission, les
            gestes de prévention et les recommandations aux voyageurs. Ces fiches sont validées et
            publiées par le MSHPCMU et l&apos;INHP.
          </p>
        </header>

        {alerts.length > 0 && (
          <section aria-labelledby="alertes-en-cours" className="mt-10">
            <h2 id="alertes-en-cours" className="font-display text-2xl font-black text-ciDark">Alertes en cours</h2>
            <div className="mt-4 grid gap-6 md:grid-cols-2">
              {alerts.map((n) => <NoticeCard key={n.uuid} notice={n} />)}
            </div>
          </section>
        )}

        <section aria-label="Fiches maladies" className="mt-10">
          <DiseaseExplorer diseases={diseases} />
        </section>

        <aside className="mt-12 flex flex-col items-start gap-4 rounded-3xl bg-ciDark p-8 text-white md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="font-display text-2xl font-black">Un symptôme, un doute ?</h2>
            <p className="mt-1 text-emerald-100">Les services de santé vous écoutent et vous orientent.</p>
          </div>
          <a href="tel:143" className="btn-orange">
            <PhoneCall className="h-4 w-4" aria-hidden="true" /> Allô Santé 143
          </a>
        </aside>
      </div>
    </div>
  );
}
