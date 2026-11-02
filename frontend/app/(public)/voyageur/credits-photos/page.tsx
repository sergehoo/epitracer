import Image, { type StaticImageData } from 'next/image';
import { Section } from '@/components/ui/Section';
import { HEALTH_PHOTOS, LANDING_PHOTOS } from '@/lib/landingPhotos';

export const metadata = {
  title: 'Crédits photos',
  description: "Auteurs, sources et licences des photographies du site Destination Côte d'Ivoire.",
};

const UNSPLASH_LICENSE = 'https://unsplash.com/license';

const HEALTH_LABELS: Record<keyof typeof HEALTH_PHOTOS, string> = {
  hands: 'Lavage des mains',
  contact: 'Gel hydroalcoolique',
  mosquitoes: 'Moustiquaire',
  foodWater: 'Étal de fruits et légumes',
  vaccination: 'Flacons de vaccins',
  airport: 'Aéroport international Félix-Houphouët-Boigny',
  thermometer: 'Thermomètre numérique',
};

type Credit = {
  key: string;
  src: StaticImageData;
  label: string;
  author: string;
  page: string;
  source: 'Unsplash' | 'Wikimedia Commons';
  license: string;
  licenseUrl: string;
  modified: boolean;
};

const CREDITS: Credit[] = [
  ...LANDING_PHOTOS.map((p) => ({
    key: p.key, src: p.src, label: p.place, author: p.credit, page: p.page,
    source: 'Unsplash' as const, license: 'Licence Unsplash', licenseUrl: UNSPLASH_LICENSE,
    modified: false,
  })),
  ...(Object.keys(HEALTH_PHOTOS) as (keyof typeof HEALTH_PHOTOS)[]).map((key) => {
    const p = HEALTH_PHOTOS[key];
    return {
      key, src: p.src, label: HEALTH_LABELS[key], author: p.credit, page: p.page,
      source: 'Wikimedia Commons' as const,
      license: p.license || 'Domaine public', licenseUrl: p.licenseUrl,
      // Recadrées (aucun visage), redimensionnées, métadonnées EXIF retirées.
      modified: true,
    };
  }),
];

const linkCls = 'font-medium text-emerald-700 underline-offset-4 hover:underline dark:text-emerald-400';

export default function CreditsPhotosPage() {
  return (
    <Section
      eyebrow="Informations légales"
      title="Crédits photos"
      description={
        "Les photographies du site sont utilisées sous licence libre. Les images issues de "
        + 'Wikimedia Commons ont été recadrées et redimensionnées ; elles restent diffusées '
        + 'sous leur licence d’origine.'
      }
    >
      <ul className="grid gap-4 sm:grid-cols-2">
        {CREDITS.map((c) => (
          <li
            key={c.key}
            className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
          >
            <Image
              src={c.src}
              alt=""
              sizes="112px"
              className="h-20 w-28 shrink-0 rounded-xl object-cover"
            />
            <div className="min-w-0 text-sm">
              <p className="font-semibold text-slate-900 dark:text-white">{c.label}</p>
              <p className="mt-1 text-slate-600 dark:text-slate-300">
                Photo :{' '}
                <a href={c.page} target="_blank" rel="noreferrer" className={linkCls}>{c.author}</a>
                {' '}({c.source})
              </p>
              <p className="text-slate-600 dark:text-slate-300">
                Licence :{' '}
                {c.licenseUrl
                  ? <a href={c.licenseUrl} target="_blank" rel="noreferrer license" className={linkCls}>{c.license}</a>
                  : c.license}
                {c.modified && ' · recadrée'}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}
