'use client';

/**
 * Page détail suivi sanitaire d'un voyageur — Phase 9C (en construction).
 *
 * Cette page va consommer les 16 endpoints `/api/v1/admin/followups/` livrés
 * en Phase 9B. La structure complète (Header, Progress, Timeline J1-J21,
 * SymptomPanel, SamplePanel, LabAnalysisPanel, NotificationPanel,
 * LocationPanel, DocumentsPanel, AuditPanel + 5 modales) sera livrée
 * dans la prochaine itération.
 *
 * En attendant, on offre une vue minimale fonctionnelle qui appelle déjà
 * l'endpoint /detail/ et affiche les KPIs principaux + un bouton de retour.
 */

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Activity, Calendar, MapPin, AlertTriangle,
  CheckCircle2, Construction, RefreshCcw, User as UserIcon,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

interface FollowupCaseDetail {
  id: number;
  public_id: string;
  traveler: {
    id: number; public_id: string; full_name: string;
    phone: string; email: string;
    nationality: string; entry_point: string;
  };
  disease: { code: string; name: string; color: string };
  status: 'active' | 'completed' | 'broken' | 'extended' | 'cancelled';
  started_on: string;
  expected_end_on: string;
  day_index: number;
  total_days: number;
  current_classification_label: string;
  days_completed: number;
  days_missed: number;
  samples_count: number;
  symptoms_count: number;
  critical_symptoms_count: number;
  alerts_count: number;
  last_location_ping: { latitude: number; longitude: number; captured_at: string } | null;
  closure_reason: string;
  geolocation_alert_raised_at: string | null;
}

const STATUS_LABEL: Record<string, string> = {
  active: 'Actif',
  completed: 'Terminé',
  broken: 'Interrompu',
  extended: 'Étendu',
  cancelled: 'Annulé',
};

const STATUS_TONE: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  completed: 'bg-slate-100 text-slate-800 border-slate-300',
  broken: 'bg-rose-100 text-rose-800 border-rose-300',
  extended: 'bg-amber-100 text-amber-800 border-amber-300',
  cancelled: 'bg-slate-100 text-slate-700 border-slate-300',
};

export default function FollowupDetailPage() {
  const params = useParams<{ travelerId: string }>();
  const travelerId = params?.travelerId;
  const [data, setData] = useState<FollowupCaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    if (!travelerId) return;
    setLoading(true);
    setError(null);
    api.get(`/admin/followups/${travelerId}/`)
      .then((r) => setData(r.data))
      .catch((e) => {
        const msg = extractApiError(e);
        setError(msg);
        toast.error(msg);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [travelerId]);

  const progressPct = data
    ? Math.min(100, Math.round(((data.day_index + 1) / Math.max(1, data.total_days + 1)) * 100))
    : 0;

  return (
    <div data-theme="light" className="light space-y-6">
      {/* Fil d'Ariane + retour */}
      <div className="flex items-center justify-between">
        <Link
          href="/suivi-voyageurs"
          className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-ciOrange transition"
        >
          <ArrowLeft className="h-4 w-4" /> Retour à la liste
        </Link>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold hover:bg-slate-50 disabled:opacity-40"
        >
          <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Actualiser
        </button>
      </div>

      {/* Bandeau "en construction" */}
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 flex items-start gap-3">
        <Construction className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
        <div className="text-sm text-amber-900">
          <div className="font-bold mb-1">Page détail en cours de finalisation</div>
          <p className="text-xs leading-relaxed">
            La page complète (timeline J1-J21, prélèvements, analyses labo, notifications,
            géolocalisation, audit) arrive prochainement. Vous voyez actuellement le
            résumé minimal du suivi. Toutes les actions médicales restent accessibles
            depuis les pages dédiées.
          </p>
        </div>
      </div>

      {/* Contenu */}
      {loading && !data ? (
        <div className="rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          Chargement…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          <div className="font-bold mb-1">Impossible de charger le détail</div>
          <p>{error}</p>
          <p className="mt-2 text-xs">
            Note : l'endpoint <code>/api/v1/admin/followups/{travelerId}/</code> doit être déployé.
            Si la Phase 9B n'est pas encore en staging, faire un <code>git pull + docker compose build</code>.
          </p>
        </div>
      ) : data ? (
        <>
          {/* Header voyageur */}
          <header className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex items-start gap-3">
                <div className="h-12 w-12 rounded-xl bg-emerald-100 text-emerald-700 grid place-items-center">
                  <UserIcon className="h-6 w-6" />
                </div>
                <div>
                  <h1 className="font-display text-xl font-black text-ciDark">
                    {data.traveler.full_name}
                  </h1>
                  <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="font-mono">{data.traveler.public_id}</span>
                    <span>{data.traveler.phone}</span>
                    {data.traveler.email && <span>{data.traveler.email}</span>}
                    <span>{data.traveler.nationality}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="px-2 py-1 rounded-md bg-sky-50 text-sky-700 text-xs font-bold border border-sky-200">
                      {data.disease.name}
                    </span>
                    <span className={`px-2 py-1 rounded-md text-xs font-bold border ${STATUS_TONE[data.status] ?? STATUS_TONE.active}`}>
                      {STATUS_LABEL[data.status] ?? data.status}
                    </span>
                    {data.current_classification_label && (
                      <span className="px-2 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-bold border border-slate-200">
                        {data.current_classification_label}
                      </span>
                    )}
                    {data.critical_symptoms_count > 0 && (
                      <span className="px-2 py-1 rounded-md bg-rose-100 text-rose-700 text-xs font-bold border border-rose-300 inline-flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" /> {data.critical_symptoms_count} symptôme(s) critique(s)
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="text-right text-xs text-slate-500">
                <div className="flex items-center gap-1 justify-end">
                  <Calendar className="h-3 w-3" /> Début : {new Date(data.started_on).toLocaleDateString('fr-FR')}
                </div>
                <div className="flex items-center gap-1 justify-end mt-0.5">
                  <Calendar className="h-3 w-3" /> Fin prévue : {new Date(data.expected_end_on).toLocaleDateString('fr-FR')}
                </div>
                {data.traveler.entry_point && (
                  <div className="flex items-center gap-1 justify-end mt-0.5">
                    <MapPin className="h-3 w-3" /> {data.traveler.entry_point}
                  </div>
                )}
              </div>
            </div>
          </header>

          {/* Progress */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-end justify-between gap-4 flex-wrap">
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-1">
                  Progression du suivi
                </div>
                <div className="font-display text-4xl font-black text-ciDark tabular-nums">
                  Jour {data.day_index + 1} <span className="text-slate-400 text-2xl">/ {data.total_days + 1}</span>
                </div>
              </div>
              <div className="flex-1 min-w-[200px] max-w-md">
                <div className="h-3 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-ciOrange to-ciGreen transition-all"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <div className="text-xs text-slate-500 mt-1 text-right">{progressPct}%</div>
              </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
              <KpiCard label="Jours complétés" value={data.days_completed} tone="emerald" icon={<CheckCircle2 />} />
              <KpiCard label="Jours manqués" value={data.days_missed} tone={data.days_missed > 0 ? 'rose' : 'slate'} icon={<AlertTriangle />} />
              <KpiCard label="Symptômes" value={data.symptoms_count} tone={data.critical_symptoms_count > 0 ? 'rose' : 'slate'} icon={<Activity />} />
              <KpiCard label="Prélèvements" value={data.samples_count} tone="sky" icon={<Activity />} />
            </div>

            {/* Alerte géoloc */}
            {data.geolocation_alert_raised_at && (
              <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                <strong>Géolocalisation absente</strong> — dernière alerte déclenchée le{' '}
                {new Date(data.geolocation_alert_raised_at).toLocaleString('fr-FR')}.
                Un agent de district peut être envoyé pour vérification.
              </div>
            )}
          </section>

          {/* Liens vers actions */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3">
              Actions rapides (page complète en préparation)
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <Link
                href={`/voyageurs/${data.traveler.public_id}`}
                className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 inline-flex items-center gap-1"
              >
                Fiche voyageur complète →
              </Link>
              <Link
                href={`/voyageurs/${data.traveler.public_id}/itineraire`}
                className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 inline-flex items-center gap-1"
              >
                Itinéraire & contacts →
              </Link>
              <Link
                href={`/alertes?traveler=${data.traveler.public_id}`}
                className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 inline-flex items-center gap-1"
              >
                Alertes liées →
              </Link>
              <Link
                href="/notifications"
                className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 inline-flex items-center gap-1"
              >
                Centre notifications →
              </Link>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function KpiCard({
  label, value, tone, icon,
}: {
  label: string; value: number;
  tone: 'emerald' | 'rose' | 'amber' | 'slate' | 'sky';
  icon: React.ReactNode;
}) {
  const tones = {
    emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    rose: 'bg-rose-50 text-rose-700 ring-rose-200',
    amber: 'bg-amber-50 text-amber-700 ring-amber-200',
    slate: 'bg-slate-50 text-slate-700 ring-slate-200',
    sky: 'bg-sky-50 text-sky-700 ring-sky-200',
  } as const;
  return (
    <div className={`rounded-xl ring-1 p-3 ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide font-bold">{label}</span>
        <span className="opacity-60">{icon}</span>
      </div>
      <div className="font-display text-2xl font-black tabular-nums mt-1">
        {value.toLocaleString('fr-FR')}
      </div>
    </div>
  );
}
