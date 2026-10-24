'use client';

import { useEffect, useState } from 'react';
import { BellRing, CheckCircle2, Download, PhoneCall, Smartphone, WifiOff } from 'lucide-react';
import { useLocale } from '@/lib/i18n';
import { DestinationBrand } from '@/components/public/DestinationBrand';
import { Reveal } from './Reveal';

/** Évènement non standard exposé par Chrome / Edge / Android. */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

type InstallState = 'checking' | 'prompt' | 'ios' | 'installed' | 'unsupported';

/** Installation PWA : bouton si le navigateur le permet, sinon la marche à suivre. */
function InstallControl() {
  const { t } = useLocale();
  const [state, setState] = useState<InstallState>('checking');
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches
      || (navigator as Navigator & { standalone?: boolean }).standalone === true;
    if (standalone) {
      setState('installed');
      return;
    }
    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
    setState(isIos ? 'ios' : 'unsupported');

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setState('prompt');
    };
    const onInstalled = () => { setDeferred(null); setState('installed'); };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    const { outcome } = await deferred.userChoice;
    if (outcome === 'accepted') setState('installed');
    setDeferred(null);
  };

  if (state === 'checking') return null;
  if (state === 'prompt') {
    return (
      <button
        type="button"
        onClick={install}
        className="inline-flex items-center gap-2 rounded-2xl bg-ciOrange px-6 py-4 font-bold text-slate-900 shadow-lg transition hover:bg-orange-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
      >
        <Download className="h-5 w-5" aria-hidden="true" /> {t.pwa.install}
      </button>
    );
  }
  const message = state === 'installed' ? t.pwa.installed : state === 'ios' ? t.pwa.ios : t.pwa.unsupported;
  return (
    <p className="inline-flex items-start gap-2 rounded-2xl bg-white/10 px-4 py-3 text-sm text-emerald-50" role="status">
      <Smartphone className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> {message}
    </p>
  );
}

const BENEFIT_ICONS = [WifiOff, BellRing, PhoneCall];

export function PwaSection() {
  const { t } = useLocale();
  const p = t.pwa;
  return (
    <section id="application" aria-labelledby="pwa-title" className="scroll-mt-24 bg-ciForest py-16 text-white sm:py-24">
      <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2">
        <Reveal>
          <p className="text-xs font-bold uppercase tracking-widest text-orange-200">{p.eyebrow}</p>
          <h2 id="pwa-title" className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">{p.title}</h2>
          <p className="mt-4 max-w-xl text-emerald-50">{p.text}</p>
          <ul className="mt-8 space-y-4">
            {p.benefits.map((b, i) => {
              const Icon = BENEFIT_ICONS[i];
              return (
                <li key={b} className="flex items-start gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/10" aria-hidden="true">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="pt-2 text-sm font-semibold sm:text-base">{b}</span>
                </li>
              );
            })}
          </ul>
          <div className="mt-8"><InstallControl /></div>
        </Reveal>

        {/* Téléphone stylisé : écran d'accueil de l'application (illustration) */}
        <Reveal delay={0.1} className="flex justify-center">
          <div className="relative w-64 rounded-[2.75rem] border-[10px] border-slate-900 bg-slate-900 shadow-2xl" aria-hidden="true">
            <div className="absolute left-1/2 top-2 h-5 w-24 -translate-x-1/2 rounded-full bg-slate-800" />
            <div className="overflow-hidden rounded-[2rem] bg-white">
              <div className="flex h-1.5"><span className="flex-1 bg-ciOrange" /><span className="flex-1 bg-white" /><span className="flex-1 bg-ciGreen" /></div>
              <div className="space-y-3 px-4 pb-6 pt-9 text-slate-900">
                <DestinationBrand size="sm" tagline={false} />
                <div className="rounded-2xl bg-emerald-50 p-3">
                  <div className="h-2 w-20 rounded bg-emerald-200" />
                  <div className="mt-2 grid grid-cols-[1fr,auto] items-center gap-2">
                    <div className="space-y-1.5">
                      <div className="h-2 w-24 rounded bg-slate-200" />
                      <div className="h-2 w-16 rounded bg-slate-200" />
                    </div>
                    <div className="grid h-14 w-14 grid-cols-3 gap-0.5 rounded-lg bg-white p-1">
                      {Array.from({ length: 9 }).map((_, i) => (
                        <span key={i} className={i % 2 === 0 ? 'bg-slate-900' : 'bg-slate-200'} />
                      ))}
                    </div>
                  </div>
                </div>
                {[0, 1, 2].map((i) => (
                  <div key={i} className="flex items-center gap-2 rounded-xl border border-slate-100 p-2.5">
                    <CheckCircle2 className="h-4 w-4 text-ciForest" />
                    <div className="h-2 flex-1 rounded bg-slate-200" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
