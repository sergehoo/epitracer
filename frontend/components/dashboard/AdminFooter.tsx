'use client';

import { AfriqConsultingCredit } from '@/components/ui/AfriqConsultingCredit';

/**
 * Footer discret affiché en bas du dashboard d'administration.
 * Une seule ligne, fond neutre, ne perturbe pas l'UX de travail.
 */
export function AdminFooter() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-950/60 py-3 px-4">
      <AfriqConsultingCredit variant="light" />
    </footer>
  );
}
