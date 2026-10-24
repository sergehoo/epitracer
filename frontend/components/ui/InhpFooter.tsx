'use client';

import Image from 'next/image';
import Link from 'next/link';
import { Mail, PhoneCall } from 'lucide-react';
import { adminUrl } from '@/lib/hosts';
import { useLocale } from '@/lib/i18n';
import { LANDING_PHOTOS } from '@/lib/landingPhotos';
import { AfriqConsultingCredit } from './AfriqConsultingCredit';
import { TricolorBand } from './InhpHeader';

const EMERGENCY = [
  { key: 'samu', n: '185' },
  { key: 'health', n: '143' },
  { key: 'rescue', n: '101' },
] as const;

export function InhpFooter() {
  const { t, locale } = useLocale();
  const f = t.footer;
  const linkCls = 'rounded hover:text-white hover:underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white';

  return (
    <footer lang={locale} className="bg-ciForest text-emerald-50">
      <TricolorBand className="h-1.5" />

      {/* Identité institutionnelle */}
      <div className="border-b border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-5 px-4 py-8 sm:px-6 md:flex-row">
          <div className="flex items-center gap-3">
            {[
              { src: '/armoirie-ci-2.png', alt: "Armoiries de la République de Côte d'Ivoire", w: 'w-14' },
              { src: '/logo-min-sante-2.png', alt: 'MSHPCMU', w: 'w-14' },
              { src: '/logo-INHP.png', alt: "Institut National d'Hygiène Publique (INHP)", w: 'w-28' },
            ].map((l) => (
              <span key={l.src} className={`grid h-14 ${l.w} place-items-center rounded-2xl bg-white p-1.5`}>
                <Image src={l.src} alt={l.alt} width={96} height={48} className="h-full w-full object-contain" />
              </span>
            ))}
          </div>
          <div className="text-center md:text-right">
            <p className="text-xs font-bold uppercase tracking-widest text-orange-200">{t.brand.country}</p>
            <p className="text-sm italic text-emerald-100">{t.brand.motto}</p>
            <p className="mt-1 text-sm font-semibold">
              Ministère de la Santé, de l&apos;Hygiène Publique et de la Couverture Maladie Universelle · INHP
            </p>
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <p className="font-display text-2xl font-extrabold text-white">EpiTrace CI</p>
          <p className="mt-3 max-w-sm text-sm leading-6 text-emerald-100">{f.about}</p>
          <p className="mt-6 text-xs font-bold uppercase tracking-widest text-orange-200">{f.contact}</p>
          <ul className="mt-2 space-y-1.5 text-sm">
            <li className="flex items-center gap-2">
              <PhoneCall className="h-4 w-4" aria-hidden="true" />
              <a href="tel:143" className={linkCls}>INHP · Allô Santé 143</a>
            </li>
            <li className="flex items-center gap-2">
              <Mail className="h-4 w-4" aria-hidden="true" />
              <a href="mailto:info@destinationci.com" className={linkCls}>info@destinationci.com</a>
            </li>
          </ul>
        </div>

        <nav aria-label={f.travelers}>
          <p className="font-bold text-white">{f.travelers}</p>
          <ul className="mt-3 space-y-2 text-sm">
            <li><Link href="/voyageur" className={linkCls}>{f.prepare}</Link></li>
            <li><Link href="/pass" className={linkCls}>{f.pass}</Link></li>
            <li><Link href="/voyageur/suivi" className={linkCls}>{f.followup}</Link></li>
            <li><Link href="/maladies" className={linkCls}>{f.diseases}</Link></li>
            <li><Link href="/assistance" className={linkCls}>{f.advice}</Link></li>
          </ul>
        </nav>

        <div>
          <p className="font-bold text-white">{f.emergency}</p>
          <ul className="mt-3 space-y-2 text-sm">
            {EMERGENCY.map((e) => (
              <li key={e.n} className="flex items-center justify-between gap-4 border-b border-white/10 pb-2">
                <span>{f[e.key]}</span>
                <a href={`tel:${e.n}`} className={`font-display text-lg font-extrabold text-white ${linkCls}`}>{e.n}</a>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-8">
          <nav aria-label={f.institutional}>
            <p className="font-bold text-white">{f.institutional}</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li><a href="https://www.sante.gouv.ci" target="_blank" rel="noreferrer" className={linkCls}>MSHPCMU</a></li>
              <li><a href="https://www.inhp.ci" target="_blank" rel="noreferrer" className={linkCls}>INHP</a></li>
              <li><a href={adminUrl('/auth/login')} className={linkCls}>{f.pro}</a></li>
            </ul>
          </nav>
          <nav aria-label={f.legal}>
            <p className="font-bold text-white">{f.legal}</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li><Link href="/voyageur/confidentialite" className={linkCls}>{f.privacy}</Link></li>
              <li><Link href="/voyageur/mes-donnees" className={linkCls}>{f.myData}</Link></li>
            </ul>
          </nav>
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-5 text-xs text-emerald-100 sm:px-6 md:flex-row md:items-center md:justify-between">
          <span>© {new Date().getFullYear()} {t.brand.country} — MSHPCMU · INHP. {f.rights}</span>
          <span>{f.security}</span>
        </div>
        <p className="mx-auto max-w-7xl px-4 pb-5 text-[11px] text-emerald-100/90 sm:px-6">
          {f.photos} :{' '}
          {LANDING_PHOTOS.map((p, i) => (
            <span key={p.src}>
              {i > 0 && ' · '}
              <a href={p.page} target="_blank" rel="noreferrer" className={linkCls}>{p.credit}</a>
            </span>
          ))}{' '}
          (Unsplash)
        </p>
      </div>

      <div className="border-t border-white/10 bg-black/20">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
          <AfriqConsultingCredit variant="dark" />
        </div>
      </div>
      <TricolorBand />
    </footer>
  );
}
