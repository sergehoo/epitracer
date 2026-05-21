'use client';

import { useEffect } from 'react';

/** Enregistre le service worker /sw.js au montage. */
export function PwaRegister() {
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!('serviceWorker' in navigator)) return;
    if (process.env.NODE_ENV !== 'production') return; // pas en dev pour éviter le cache aggressif

    const onLoad = () => {
      navigator.serviceWorker.register('/sw.js').catch(() => undefined);
    };
    window.addEventListener('load', onLoad);
    return () => window.removeEventListener('load', onLoad);
  }, []);
  return null;
}
