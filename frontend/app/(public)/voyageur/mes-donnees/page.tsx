'use client';

/**
 * /voyageur/mes-donnees — espace RGPD self-service du voyageur.
 *
 * Le voyageur peut :
 * - voir un résumé de ses consentements et de ce qui est stocké ;
 * - retirer un consentement (donc arrêter la collecte) ;
 * - télécharger ses données au format JSON (right of access) ;
 * - obtenir le contact du DPO pour demande de suppression.
 *
 * Aucune authentification : lookup par public_id, comme les autres pages
 * PWA voyageur.
 */

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { Database, Download, ShieldAlert, ShieldCheck } from 'lucide-react';
import { Section } from '@/components/ui/Section';
import { FieldGroup } from '@/components/form/Field';
import { api, API_URL } from '@/lib/api';
import { recordConsent, type ConsentScope } from '@/lib/companion';

const LS_KEY = 'epi.suivi.last_public_id';

interface ConsentRow {
  scope: ConsentScope;
  label: string;
  granted: boolean;
  last_decision_at: string | null;
  history_count: number;
}

interface DataSummary {
  traveler: {
    public_id: string;
    full_name: string;
    registered_at: string;
  };
  consents: ConsentRow[];
  counters: {
    checkins: number;
    location_pings: number;
    push_subscriptions_active: number;
  };
}

// Wrapper Suspense requis (Next.js 14 + useSearchParams) — voir
// /voyageur/suivi/page.tsx pour l'explication détaillée.
export default function MesDonneesPage() {
  return (
    <Suspense fallback={<div className="card p-10 animate-pulse h-72" />}>
      <MesDonneesPageContent />
    </Suspense>
  );
}

function MesDonneesPageContent() {
  const params = useSearchParams();
  const [publicId, setPublicId] = useState('');
  const [data, setData] = useState<DataSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const fromUrl = params?.get('id') || params?.get('public_id') || '';
    const fromStorage = typeof window !== 'undefined' ? localStorage.getItem(LS_KEY) || '' : '';
    const initial = (fromUrl || fromStorage).toUpperCase();
    if (initial) setPublicId(initial);
  }, [params]);

  const load = useCallback(async (id: string) => {
    if (!id) return;
    setLoading(true);
    try {
      const { data } = await api.get<DataSummary>('/public/me/data-summary/', {
        params: { public_id: id },
      });
      setData(data);
      if (typeof window !== 'undefined') localStorage.setItem(LS_KEY, id);
    } catch {
      toast.error("Impossible de charger vos données pour le moment.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (publicId.trim().length >= 4) load(publicId.trim().toUpperCase());
  }, [publicId, load]);

  const revoke = async (scope: ConsentScope) => {
    if (!data) return;
    setBusy(true);
    try {
      await recordConsent(
        data.traveler.public_id, scope, false, '',
        'Retrait depuis /voyageur/mes-donnees',
      );
      toast.success("Consentement retiré. Aucune donnée ne sera plus collectée pour ce scope.");
      await load(data.traveler.public_id);
    } catch {
      toast.error("Impossible de retirer ce consentement pour le moment.");
    } finally {
      setBusy(false);
    }
  };

  const exportData = () => {
    if (!data) return;
    // Téléchargement direct via lien (Content-Disposition attachment côté serveur)
    const url = `${API_URL}/api/v1/public/me/export/?public_id=${encodeURIComponent(data.traveler.public_id)}`;
    window.open(url, '_blank', 'noopener');
  };

  return (
    <Section
      eyebrow="Confidentialité"
      title="Mes données et mes choix"
      description="Consultez ce que nous stockons à votre sujet, retirez un consentement, ou téléchargez l'ensemble de vos données."
    >
      {!data && (
        <div className="card p-6 max-w-xl mx-auto">
          <FieldGroup
            label="Votre identifiant voyageur"
            required
            help="Format TRV-XXXXX. Vous le trouvez sur votre Pass sanitaire."
          >
            <input
              className="input"
              value={publicId}
              onChange={(e) => setPublicId(e.target.value.toUpperCase())}
              placeholder="TRV-XXXXXXXX"
            />
          </FieldGroup>
          {loading && <p className="text-sm text-slate-500 mt-2">Chargement…</p>}
        </div>
      )}

      {data && (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* ============ Bloc consentements ============ */}
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-5">
              <div className="flex items-center gap-2 text-sm font-semibold mb-3">
                <ShieldCheck className="h-4 w-4 text-emerald-600" /> Vos consentements
              </div>
              <div className="space-y-3">
                {data.consents.map((c) => (
                  <div key={c.scope} className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 last:border-0">
                    <div>
                      <div className="font-semibold">{c.label}</div>
                      <div className="text-xs text-slate-500">
                        {c.granted ? 'Actif' : 'Non accordé / retiré'}
                        {c.last_decision_at && (
                          <> · Dernière décision : {new Date(c.last_decision_at).toLocaleDateString('fr-FR')}</>
                        )}
                        {c.history_count > 1 && (
                          <> · {c.history_count} décisions historiques</>
                        )}
                      </div>
                    </div>
                    {c.granted && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => revoke(c.scope)}
                        className="text-xs font-semibold text-rose-700 hover:underline disabled:opacity-50"
                      >
                        Retirer
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Compteurs */}
            <div className="card p-5">
              <div className="flex items-center gap-2 text-sm font-semibold mb-3">
                <Database className="h-4 w-4 text-emerald-600" /> Ce qui est stocké
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <Stat label="Check-ins" value={data.counters.checkins} />
                <Stat label="Positions partagées" value={data.counters.location_pings} />
                <Stat label="Abonnements actifs" value={data.counters.push_subscriptions_active} />
              </div>
            </div>

            {/* Export */}
            <div className="card p-5">
              <div className="text-sm font-semibold">Télécharger toutes mes données</div>
              <p className="text-xs text-slate-500 mt-1 leading-5">
                Vous obtenez un fichier JSON contenant l'ensemble des informations que
                nous avons stockées à votre sujet dans le cadre de votre accompagnement.
              </p>
              <button
                type="button"
                onClick={exportData}
                className="btn-paper mt-3 inline-flex items-center gap-2"
              >
                <Download className="h-4 w-4" /> Télécharger (JSON)
              </button>
            </div>
          </div>

          {/* ============ Sidebar info ============ */}
          <aside className="space-y-4">
            <div className="card p-5">
              <div className="text-xs uppercase tracking-widest text-emerald-700 font-bold">
                Identifiant
              </div>
              <div className="font-display font-black text-ciDark dark:text-emerald-100 mt-1">
                {data.traveler.public_id}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-300 mt-2">
                {data.traveler.full_name}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Enregistré le {new Date(data.traveler.registered_at).toLocaleDateString('fr-FR')}
              </div>
            </div>

            <div className="card p-5 bg-rose-50/60 dark:bg-rose-950/20 border-rose-100">
              <div className="text-sm font-semibold flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-rose-700" /> Suppression de mes données
              </div>
              <p className="text-xs text-slate-600 mt-2 leading-5">
                Pour demander la suppression complète de vos données, contactez
                notre Délégué à la Protection des Données :
              </p>
              <a
                href="mailto:info@destinationci.com?subject=Demande%20de%20suppression%20de%20mes%20donn%C3%A9es"
                className="block mt-2 text-sm font-semibold text-rose-700 underline break-all"
              >
                info@destinationci.com
              </a>
              <p className="text-[10px] text-slate-400 mt-2">
                Loi ivoirienne n° 2013-450, art. 35 — droit à l'effacement.
              </p>
            </div>

            <Link
              href="/voyageur/confidentialite"
              className="block text-center text-xs text-slate-500 hover:text-ciOrange underline"
            >
              Voir la politique de confidentialité complète
            </Link>
          </aside>
        </div>
      )}
    </Section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-slate-50 dark:bg-slate-900 p-4">
      <div className="text-2xl font-display font-black text-ciDark dark:text-emerald-100">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-slate-500 mt-1">{label}</div>
    </div>
  );
}
