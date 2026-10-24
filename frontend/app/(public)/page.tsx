import type { Metadata } from 'next';
import { HomeFaq } from '@/components/public/HomeFaq';
import { DiseasesSection } from '@/components/public/landing/DiseasesSection';
import { Hero } from '@/components/public/landing/Hero';
import { HowItWorks } from '@/components/public/landing/HowItWorks';
import { PwaSection } from '@/components/public/landing/PwaSection';
import { QuickServices } from '@/components/public/landing/QuickServices';
import { WelcomeCI } from '@/components/public/landing/WelcomeCI';
import { fetchPublicDiseases, fetchPublicNotices } from '@/lib/portal';

// Contenus publiés par les autorités : régénérés toutes les 5 minutes.
export const revalidate = 300;

export const metadata: Metadata = {
  title: { absolute: "Destination Côte d'Ivoire — Voyager serein, accompagné en santé" },
  description:
    "Portail national MSHPCMU · INHP : préparez votre arrivée en Côte d'Ivoire, obtenez votre pass sanitaire numérique, consultez les maladies sous surveillance et les recommandations aux voyageurs.",
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    locale: 'fr_FR',
    alternateLocale: ['en_GB'],
    siteName: "Destination Côte d'Ivoire",
    title: "Destination Côte d'Ivoire — Akwaba, voyagez serein",
    description: "Information, prévention et accompagnement sanitaire des voyageurs en Côte d'Ivoire.",
  },
};

const JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'GovernmentService',
  name: "Destination Côte d'Ivoire",
  serviceType: 'Accompagnement sanitaire des voyageurs',
  areaServed: { '@type': 'Country', name: "Côte d'Ivoire" },
  provider: [
    {
      '@type': 'GovernmentOrganization',
      name: "Ministère de la Santé, de l'Hygiène Publique et de la Couverture Maladie Universelle (MSHPCMU)",
      url: 'https://www.sante.gouv.ci',
    },
    {
      '@type': 'GovernmentOrganization',
      name: "Institut National d'Hygiène Publique (INHP)",
      url: 'https://www.inhp.ci',
    },
  ],
};

export default async function HomePage() {
  const [diseases, notices] = await Promise.all([
    fetchPublicDiseases('?active=true'),
    fetchPublicNotices(),
  ]);
  return (
    <>
      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD).replace(/</g, '\\u003c') }}
      />
      <Hero />
      <QuickServices />
      <DiseasesSection diseases={diseases} notices={notices} />
      <HowItWorks />
      <WelcomeCI />
      <PwaSection />
      <HomeFaq />
    </>
  );
}
