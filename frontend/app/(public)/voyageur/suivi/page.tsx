'use client';

/**
 * Page /voyageur/suivi — espace personnel d'accompagnement sanitaire.
 *
 * Le voyageur :
 *  1. saisit son identifiant TRV-XXXX (ou il est pré-rempli via ?id=…) ;
 *  2. voit son calendrier de 21 jours + dernier check-in ;
 *  3. fait son check-in du jour (3 boutons : Je vais bien / Symptôme / Assistance) ;
 *  4. peut activer/désactiver le partage de position (consentement explicite) ;
 *  5. peut consulter la politique de confidentialité.
 *
 * Tout le langage est volontairement rassurant ("accompagnement",
 * "vos nouvelles") — pas de "surveillance" ni "quarantaine" affichés.
 */

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import {
  Activity, Bell, BellOff, HeartHandshake, MapPin, ShieldCheck, Smile, ThermometerSun,
} from 'lucide-react';
import { Section } from '@/components/ui/Section';
import { Companion21Days } from '@/components/public/Companion21Days';
import { FieldGroup, YesNo } from '@/components/form/Field';
import {
  CONSENT_VERSION, fetchFollowUpStatus, recordConsent, submitCheckin,
  tryGetPosition, type FollowUpStatus,
} from '@/lib/companion';
import {
  getExistingSubscription, isPermissionDenied, isPushSupported,
  subscribeUserToPush, unsubscribeUserFromPush,
} from '@/lib/push';

const SYMPTOM_KEYS = [
  { key: 'fever', label: 'Avez-vous de la fièvre ?' },
  { key: 'intense_fatigue', label: 'Une fatigue inhabituelle ?' },
  { key: 'severe_headache', label: 'Des maux de tête importants ?' },
  { key: 'muscle_joint_pain', label: 'Des douleurs musculaires ou articulaires ?' },
  { key: 'sore_throat_or_abdominal', label: 'Mal à la gorge ou au ventre ?' },
  { key: 'diarrhea_nausea_vomiting', label: 'Diarrhée, nausées ou vomissements ?' },
  { key: 'unexplained_bleeding', label: 'Des saignements inexpliqués ?' },
] as const;

const LS_KEY = 'epi.suivi.last_public_id';

// Wrapper Suspense — requis par Next.js 14 dès qu'on utilise
// useSearchParams() dans un Client Component avec rendu statique. Sans ce
// wrapper, le build casse avec "useSearchParams() should be wrapped in a
// suspense boundary".
export default function SuiviPage() {
  return (
    <Suspense fallback={<div className="card p-10 animate-pulse h-72" />}>
      <SuiviPageContent />
    </Suspense>
  );
}

function SuiviPageContent() {
  const params = useSearchParams();
  const [publicId, setPublicId] = useState<string>('');
  const [status, setStatus] = useState<FollowUpStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Mode check-in ---
  const [showSymptomForm, setShowSymptomForm] = useState(false);
  const [symptoms, setSymptoms] = useState<Record<string, boolean>>({});
  const [temp, setTemp] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  // --- Géoloc ---
  const [geoConsent, setGeoConsent] = useState<boolean>(false);
  const [geoBusy, setGeoBusy] = useState<boolean>(false);

  // --- Push ---
  const [pushEnabled, setPushEnabled] = useState<boolean>(false);
  const [pushBusy, setPushBusy] = useState<boolean>(false);
  const [pushSupported, setPushSupported] = useState<boolean>(true);
  const [pushBlocked, setPushBlocked] = useState<boolean>(false);

  // Au montage : détecte le support navigateur + état de la subscription
  useEffect(() => {
    setPushSupported(isPushSupported());
    setPushBlocked(isPermissionDenied());
    getExistingSubscription().then((s) => setPushEnabled(Boolean(s)));
  }, []);

  // Pre-fill public_id depuis la query ou le localStorage
  useEffect(() => {
    const fromUrl = params?.get('id') || params?.get('public_id') || '';
    const fromStorage = typeof window !== 'undefined'
      ? localStorage.getItem(LS_KEY) || '' : '';
    const initial = (fromUrl || fromStorage).toUpperCase();
    if (initial) setPublicId(initial);
  }, [params]);

  const refresh = useCallback(async (id: string) => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFollowUpStatus(id);
      setStatus(data);
      setGeoConsent(Boolean(data.consents?.geolocation));
      if (typeof window !== 'undefined') localStorage.setItem(LS_KEY, id);
    } catch (e: unknown) {
      setStatus(null);
      const msg = e instanceof Error ? e.message : 'Identifiant introuvable.';
      setError(msg.includes('404')
        ? "Aucun voyageur trouvé pour cet identifiant. Vérifiez la saisie."
        : "Impossible de charger votre suivi pour le moment. Réessayez dans un instant.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (publicId.trim().length >= 4) {
      refresh(publicId.trim().toUpperCase());
    }
  }, [publicId, refresh]);

  // --- Actions ---

  const toggleGeoConsent = async (nextValue: boolean) => {
    if (!status) return;
    try {
      await recordConsent(
        status.traveler.public_id,
        'geolocation',
        nextValue,
        nextValue
          ? "J'autorise le partage de ma position lors des check-ins et des demandes d'assistance."
          : "Je retire mon autorisation de partage de position.",
        nextValue ? '' : 'Retrait par l\'utilisateur depuis /voyageur/suivi',
      );
      setGeoConsent(nextValue);
      toast.success(nextValue
        ? 'Merci. Vous pourrez être orienté plus rapidement en cas de besoin.'
        : "C'est noté. Aucune position ne sera collectée.");
    } catch {
      toast.error("Impossible d'enregistrer votre choix pour le moment.");
    }
  };

  const togglePush = async (next: boolean) => {
    if (!status) return;
    setPushBusy(true);
    try {
      if (next) {
        const result = await subscribeUserToPush(status.traveler.public_id);
        if (result.ok) {
          setPushEnabled(true);
          toast.success('Vous recevrez désormais nos rappels — merci !');
        } else if (result.reason === 'denied') {
          setPushBlocked(true);
          toast.error("Les notifications sont bloquées dans votre navigateur.");
        } else if (result.reason === 'unsupported') {
          toast.error("Votre navigateur ne supporte pas les notifications.");
        } else {
          toast.error("Impossible d'activer les rappels pour le moment.");
        }
      } else {
        const ok = await unsubscribeUserFromPush(status.traveler.public_id);
        if (ok) {
          setPushEnabled(false);
          toast.success("Rappels désactivés. Vous pouvez les réactiver à tout moment.");
        } else {
          toast.error("Impossible de désactiver pour le moment.");
        }
      }
    } finally {
      setPushBusy(false);
    }
  };

  const sendCheckin = async (feeling: 'ok' | 'symptom' | 'assistance') => {
    if (!status) return;
    setSubmitting(true);
    try {
      // Best-effort : si géoloc consentie, on tente de récupérer la position
      let pos: GeolocationPosition | null = null;
      if (geoConsent) {
        setGeoBusy(true);
        pos = await tryGetPosition();
        setGeoBusy(false);
      }

      const filteredSymptoms = Object.fromEntries(
        Object.entries(symptoms).filter(([, v]) => v),
      );

      const result = await submitCheckin({
        public_id: status.traveler.public_id,
        feeling,
        symptoms: filteredSymptoms,
        temperature_celsius: temp ? Number(temp) : null,
        notes,
        needs_contact: feeling === 'assistance',
        latitude: pos?.coords.latitude ?? null,
        longitude: pos?.coords.longitude ?? null,
        accuracy_m: pos?.coords.accuracy ?? null,
      });

      toast.success(result.message, { duration: 6000 });
      setShowSymptomForm(false);
      setSymptoms({});
      setTemp('');
      setNotes('');
      // Rafraîchir le statut (last_check à jour)
      await refresh(status.traveler.public_id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Erreur';
      toast.error(`Impossible d'enregistrer votre check-in : ${msg}`);
    } finally {
      setSubmitting(false);
      setGeoBusy(false);
    }
  };

  const dayLabel = useMemo(() => {
    const di = status?.quarantine?.day_index;
    const tot = status?.quarantine?.total_days;
    if (di == null || tot == null) return '';
    return `Jour ${di + 1} sur ${tot + 1}`;
  }, [status]);

  return (
    <Section
      eyebrow="Espace voyageur"
      title="Comment vous sentez-vous aujourd'hui ?"
      description="Prenez quelques secondes pour nous donner de vos nouvelles. Vos informations restent confidentielles et nous permettent de mieux vous accompagner."
    >
      {/* ID input */}
      {!status && (
        <div className="card p-6 max-w-xl mx-auto">
          <FieldGroup
            label="Votre identifiant voyageur"
            required
            help="Format TRV-XXXXX. Vous le trouvez sur votre Pass sanitaire."
            error={error || undefined}
          >
            <input
              className="input"
              value={publicId}
              onChange={(e) => setPublicId(e.target.value.toUpperCase())}
              placeholder="TRV-XXXXXXXX"
              autoComplete="off"
            />
          </FieldGroup>
          {loading && <p className="text-sm text-slate-500 mt-2">Chargement de votre suivi…</p>}
        </div>
      )}

      {status && (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* ============ Bloc principal ============ */}
          <div className="lg:col-span-2 space-y-6">
            {/* En-tête */}
            <div className="card p-6 bg-gradient-to-br from-emerald-50 to-orange-50 dark:from-emerald-950/30 dark:to-orange-950/20 border-emerald-200/60 dark:border-emerald-900/60">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-2xl bg-emerald-600 text-white grid place-items-center">
                  <HeartHandshake className="h-6 w-6" />
                </div>
                <div>
                  <div className="text-xs uppercase tracking-widest text-emerald-700 font-bold">
                    Bonjour
                  </div>
                  <div className="font-display text-2xl font-black text-ciDark dark:text-emerald-100">
                    {status.traveler.full_name}
                  </div>
                  {dayLabel && (
                    <div className="text-sm text-slate-600 dark:text-slate-300 mt-0.5">
                      {dayLabel}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Boutons rapides */}
            {!showSymptomForm && (
              <div className="grid sm:grid-cols-3 gap-4">
                <button
                  onClick={() => sendCheckin('ok')}
                  disabled={submitting}
                  className="card p-5 hover:shadow-lg transition flex flex-col items-center text-center gap-2 disabled:opacity-50"
                >
                  <Smile className="h-8 w-8 text-emerald-600" />
                  <div className="font-bold text-emerald-700">Je vais bien</div>
                  <div className="text-xs text-slate-500">Confirmer mon état du jour</div>
                </button>
                <button
                  onClick={() => setShowSymptomForm(true)}
                  disabled={submitting}
                  className="card p-5 hover:shadow-lg transition flex flex-col items-center text-center gap-2 disabled:opacity-50"
                >
                  <ThermometerSun className="h-8 w-8 text-amber-600" />
                  <div className="font-bold text-amber-700">Je ressens un symptôme</div>
                  <div className="text-xs text-slate-500">Décrire calmement ce que je ressens</div>
                </button>
                <button
                  onClick={() => sendCheckin('assistance')}
                  disabled={submitting}
                  className="card p-5 hover:shadow-lg transition flex flex-col items-center text-center gap-2 disabled:opacity-50 border-rose-100 bg-rose-50/60 dark:bg-rose-950/20"
                >
                  <Activity className="h-8 w-8 text-rose-600" />
                  <div className="font-bold text-rose-700">J'ai besoin d'aide</div>
                  <div className="text-xs text-slate-500">Une équipe me recontactera</div>
                </button>
              </div>
            )}

            {/* Formulaire symptômes */}
            {showSymptomForm && (
              <div className="card p-6 space-y-4">
                <div>
                  <h3 className="font-display text-lg font-bold">Précisez ce que vous ressentez</h3>
                  <p className="text-sm text-slate-500">
                    Aucune réponse n'est obligatoire. Indiquez seulement ce qui vous concerne.
                  </p>
                </div>
                <div className="space-y-2">
                  {SYMPTOM_KEYS.map((q) => (
                    <div
                      key={q.key}
                      className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 py-2"
                    >
                      <span className="text-sm">{q.label}</span>
                      <YesNo
                        name={q.key}
                        value={Boolean(symptoms[q.key])}
                        onChange={(v) => setSymptoms((s) => ({ ...s, [q.key]: v }))}
                      />
                    </div>
                  ))}
                </div>
                <FieldGroup label="Température (°C)" help="Si vous l'avez mesurée récemment.">
                  <input
                    type="number"
                    step={0.1}
                    min={30}
                    max={45}
                    className="input max-w-[140px]"
                    value={temp}
                    onChange={(e) => setTemp(e.target.value)}
                  />
                </FieldGroup>
                <FieldGroup label="Notes (optionnel)">
                  <textarea
                    className="textarea"
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Décrivez si vous le souhaitez (sommeil, appétit, contexte…)"
                  />
                </FieldGroup>
                <div className="flex justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => setShowSymptomForm(false)}
                    className="btn-ghost"
                    disabled={submitting}
                  >
                    Annuler
                  </button>
                  <button
                    type="button"
                    onClick={() => sendCheckin('symptom')}
                    disabled={submitting}
                    className="btn-primary"
                  >
                    {submitting ? 'Envoi…' : 'Envoyer mon signalement'}
                  </button>
                </div>
              </div>
            )}

            {/* Calendrier 21 jours */}
            <Companion21Days
              surveillanceStart={status.quarantine.started_on}
              surveillanceEnd={status.quarantine.expected_end_on}
            />
          </div>

          {/* ============ Sidebar ============ */}
          <aside className="space-y-4">
            {/* Activation des rappels (Web Push) */}
            {pushSupported && (
              <div className="card p-5">
                <div className="flex items-center gap-2 text-sm font-semibold mb-2">
                  {pushEnabled ? (
                    <Bell className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <BellOff className="h-4 w-4 text-slate-500" />
                  )}
                  Rappels sanitaires
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-5">
                  Recevez un rappel doux chaque matin pour donner de vos nouvelles.
                  Vous gardez la main : un seul clic pour vous désabonner.
                </p>
                {pushBlocked ? (
                  <p className="mt-3 text-xs text-rose-600">
                    Les notifications sont actuellement bloquées dans votre navigateur.
                    Réactivez-les depuis les réglages du site pour recevoir nos messages.
                  </p>
                ) : (
                  <button
                    type="button"
                    onClick={() => togglePush(!pushEnabled)}
                    disabled={pushBusy}
                    className={`mt-3 w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm transition ${
                      pushEnabled
                        ? 'bg-white border border-emerald-300 text-emerald-700 hover:bg-emerald-50'
                        : 'bg-gradient-to-r from-ciOrange to-orange-600 text-white shadow-lg shadow-orange-500/20'
                    } disabled:opacity-50`}
                  >
                    {pushBusy ? '…' : pushEnabled ? 'Désactiver les rappels' : 'Activer les rappels'}
                  </button>
                )}
              </div>
            )}

            {/* Consentement géoloc */}
            <div className="card p-5">
              <div className="flex items-center gap-2 text-sm font-semibold mb-2">
                <MapPin className="h-4 w-4 text-emerald-600" />
                Partager ma position
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-5">
                Votre position est utilisée <strong>uniquement</strong> au moment d'un
                check-in ou d'une demande d'aide, pour permettre aux équipes sanitaires
                de vous orienter plus rapidement si besoin.
              </p>
              <label className="mt-3 flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={geoConsent}
                  onChange={(e) => toggleGeoConsent(e.target.checked)}
                  disabled={geoBusy}
                />
                <span className="text-sm">
                  J'autorise le partage de ma position au moment de mes check-ins.
                </span>
              </label>
              <p className="text-[10px] text-slate-400 mt-2">Politique {CONSENT_VERSION}</p>
            </div>

            {/* Dernier check-in */}
            {status.last_check && (
              <div className="card p-5">
                <div className="text-sm font-semibold flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  Dernier check-in
                </div>
                <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Le {new Date(status.last_check.check_date).toLocaleDateString('fr-FR')}
                  {status.last_check.temperature_celsius != null && (
                    <> · {status.last_check.temperature_celsius}°C</>
                  )}
                </div>
              </div>
            )}

            {/* Assistance */}
            <div className="card p-5 bg-rose-50/60 dark:bg-rose-950/20 border-rose-100">
              <div className="text-sm font-semibold">En cas d'urgence</div>
              <div className="mt-2 text-sm space-y-1">
                <div>SAMU : <a href={`tel:${status.assistance.samu}`} className="font-black text-ciOrange">{status.assistance.samu}</a></div>
                <div>Allô Santé : <a href={`tel:${status.assistance.allo_sante}`} className="font-black text-ciOrange">{status.assistance.allo_sante}</a></div>
                <div>Secours : <a href={`tel:${status.assistance.secours}`} className="font-black text-ciOrange">{status.assistance.secours}</a></div>
              </div>
            </div>

            {/* Liens RGPD */}
            <div className="text-center text-xs text-slate-500 space-x-3">
              <Link
                href={`/voyageur/mes-donnees?id=${status.traveler.public_id}`}
                className="hover:text-ciOrange underline"
              >
                Mes données
              </Link>
              <span>·</span>
              <Link
                href="/voyageur/confidentialite"
                className="hover:text-ciOrange underline"
              >
                Politique
              </Link>
            </div>
          </aside>
        </div>
      )}
    </Section>
  );
}
