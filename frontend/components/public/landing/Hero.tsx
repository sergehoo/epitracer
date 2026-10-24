'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, BadgeCheck, MapPin, QrCode } from 'lucide-react';
import { useLocale } from '@/lib/i18n';
import { heroPhoto } from '@/lib/landingPhotos';
import { DemoPass } from './DemoPass';

export function Hero() {
  const { t } = useLocale();
  const h = t.hero;
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden bg-gradient-to-b from-emerald-50/70 via-white to-white">
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 pb-16 pt-10 sm:px-6 lg:grid-cols-[1.05fr,1fr] lg:gap-14 lg:pb-24 lg:pt-16">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        >
          <p className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-ciForest shadow-sm ring-1 ring-emerald-100">
            <span className="h-2 w-2 rounded-full bg-ciOrange" aria-hidden="true" />
            {h.eyebrow}
          </p>
          <h1 id="hero-title" className="mt-5 font-display text-[2.15rem] font-extrabold leading-[1.1] tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
            {h.title}
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">{h.subtitle}</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/voyageur"
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-ciForest px-6 py-4 text-base font-bold text-white shadow-lg shadow-emerald-900/20 transition hover:-translate-y-0.5 hover:bg-emerald-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest"
            >
              {h.ctaPrimary} <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              href="/pass"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border-2 border-slate-200 bg-white px-6 py-4 text-base font-bold text-slate-800 transition hover:border-ciForest hover:text-ciForest focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ciForest"
            >
              <QrCode className="h-4 w-4" aria-hidden="true" /> {h.ctaSecondary}
            </Link>
          </div>
          <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm font-semibold text-slate-700">
            {h.reassurance.map((r) => (
              <li key={r} className="inline-flex items-center gap-1.5">
                <BadgeCheck className="h-4 w-4 text-ciForest" aria-hidden="true" /> {r}
              </li>
            ))}
          </ul>
        </motion.div>

        <div className="relative pb-24 sm:pb-16 lg:pb-0">
          <div className="relative aspect-[4/3] overflow-hidden rounded-[2rem] bg-emerald-100 shadow-2xl ring-1 ring-slate-900/5">
            <Image
              src={heroPhoto.src}
              alt={h.photoAlt}
              fill
              priority
              sizes="(min-width: 1024px) 48vw, 100vw"
              className="object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/40 via-transparent to-transparent" aria-hidden="true" />
            <p className="absolute right-4 top-4 inline-flex items-center gap-1 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-slate-800 backdrop-blur">
              <MapPin className="h-3.5 w-3.5 text-ciForest" aria-hidden="true" /> {heroPhoto.place}
            </p>
          </div>
          {/* Conteneur de positionnement : framer-motion pilote le transform de la carte. */}
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 sm:left-auto sm:right-6 sm:translate-x-0 lg:-bottom-10 lg:-left-10 lg:right-auto">
            <DemoPass />
          </div>
        </div>
      </div>
    </section>
  );
}
