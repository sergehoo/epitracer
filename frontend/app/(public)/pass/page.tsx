'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { QrCode, Search } from 'lucide-react';
import { Section } from '@/components/ui/Section';
import { VoyageurSubnav } from '@/components/public/VoyageurSubnav';

export default function PassLookupPage() {
  const router = useRouter();
  const [pid, setPid] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = pid.trim().toUpperCase();
    if (!v.startsWith('TRV-')) {
      setErr('Identifiant invalide. Il commence par TRV-…');
      return;
    }
    router.push(`/pass/${v}`);
  };

  return (
    <Section
      eyebrow="Pass sanitaire"
      title="Récupérez votre pass numérique"
      description="Saisissez votre identifiant voyageur (TRV-…) reçu lors de l'enregistrement pour consulter votre pass et son QR code."
    >
      <VoyageurSubnav />

      <div className="card p-6 lg:p-10 max-w-2xl">
        <form onSubmit={submit} className="space-y-4">
          <label className="field-label">Identifiant voyageur</label>
          <div className="flex gap-2">
            <input
              className="input"
              placeholder="TRV-XXXXXXXXXX"
              value={pid}
              onChange={(e) => setPid(e.target.value)}
            />
            <button className="btn-primary">
              <Search className="h-4 w-4" /> Rechercher
            </button>
          </div>
          {err && <p className="field-error">{err}</p>}
          <p className="field-help">
            Vous n'avez pas encore d'identifiant ? <a href="/voyageur" className="text-emerald-700 underline">Remplir la fiche passager</a>.
          </p>
        </form>

        <div className="mt-8 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 flex items-center gap-4">
          <QrCode className="h-10 w-10 text-emerald-600" />
          <div className="text-sm text-slate-600 dark:text-slate-300">
            Le pass sanitaire est signé numériquement et peut être <strong>vérifié hors-ligne</strong> par les agents
            de contrôle aux points d'entrée. Il est valable {String(30)} jours par défaut.
          </div>
        </div>
      </div>
    </Section>
  );
}
