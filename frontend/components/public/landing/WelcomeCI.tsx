'use client';

import Image from 'next/image';
import { MapPin } from 'lucide-react';
import { useLocale } from '@/lib/i18n';
import { panoramaPhoto } from '@/lib/landingPhotos';
import { Reveal } from './Reveal';

/** Section Côte d'Ivoire : photographie panoramique et message d'accueil. */
export function WelcomeCI() {
  const { t } = useLocale();
  const c = t.ci;
  return (
    <section aria-labelledby="ci-title" className="relative isolate overflow-hidden bg-slate-900">
      <Image
        src={panoramaPhoto.src}
        alt={c.photoAlt}
        fill
        sizes="100vw"
        loading="lazy"
        className="-z-10 object-cover"
      />
      <div className="absolute inset-0 -z-10 bg-gradient-to-r from-slate-950/85 via-slate-950/60 to-slate-950/10" aria-hidden="true" />
      <div className="mx-auto flex min-h-[28rem] max-w-7xl items-end px-4 py-16 sm:min-h-[32rem] sm:px-6 lg:items-center">
        <Reveal className="max-w-xl">
          <p className="text-sm font-bold uppercase tracking-widest text-orange-300">{c.eyebrow}</p>
          <h2 id="ci-title" className="mt-3 font-display text-3xl font-extrabold leading-tight text-white sm:text-5xl">
            {c.title}
          </h2>
          <p className="mt-5 text-base leading-7 text-slate-100 sm:text-lg sm:leading-8">{c.text}</p>
          <p className="mt-6 inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white backdrop-blur">
            <MapPin className="h-3.5 w-3.5" aria-hidden="true" /> {panoramaPhoto.place}
          </p>
        </Reveal>
      </div>
    </section>
  );
}
