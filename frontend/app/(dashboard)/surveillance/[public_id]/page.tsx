'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  AlertTriangle, ArrowLeft, Briefcase, Calendar, CheckCircle2, Clock,
  Download, ExternalLink, FileText, Globe2, Hash, Hospital, IdCard, Mail,
  MapPin, MessageSquare, Phone, Plane, QrCode, RefreshCcw, Send,
  ShieldCheck, Stethoscope, Thermometer, User, X,
} from 'lucide-react';
import { API_URL, api, extractApiError } from '@/lib/api';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { formatDate, formatDateTime, STATUS_LABELS } from '@/lib/utils';
import type { RiskLevel } from '@/types/ebola';
import { SendMessageModal, SendMessageTarget } from '@/components/notifications/SendMessageModal';
import { NotificationHistory } from '@/components/notifications/NotificationHistory';

/* ============================================================
   Types (depuis /ebola/public/pass/<public_id>/ — endpoint AllowAny)
   ============================================================ */
interface TravelerLite {
  public_id: string;
  full_name: string;
  current_health_status: string;
  arrival_date: string | null;
  entry_point: string | null;
  has_passport: boolean;
}

interface PassInfo {
  pass_number: string;
  uuid: string;
  status: string;
  risk_level: RiskLevel;
  risk_score: number;
  issued_at: string | null;
  expires_at: string | null;
  qr_url: string | null;
  pdf_url: string | null;
  qr_token: string;
}

interface Investigation {
  case_number: string;
  status: string;
  risk_level: RiskLevel;
  risk_score: number;
  entry_point_name: string;
  notes: string;
  surveillance_start: string | null;
  surveillance_end: string | null;
  created_at: string;
  traveler_detail?: any;
  exposure?: any;
  declaration?: any;
  last_symptoms?: any;
}

interface ConsultResp {
  traveler: TravelerLite;
  investigation: Investigation | null;
  pass: PassInfo | null;
  downloads: { pass_pdf: string; official_form_pdf: string };
}

export default function TravelerDetailPage() {
  const { public_id } = useParams<{ public_id: string }>();
  const router = useRouter();
  const [data, setData] = useState<ConsultResp | null>(null);
  const [traveler, setTraveler] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msgTarget, setMsgTarget] = useState<SendMessageTarget | null>(null);

  const load = () => {
    setLoading(true);
    setErr(null);
    Promise.allSettled([
      api.get<ConsultResp>(`/ebola/public/pass/${public_id}/`),
      api.get(`/travelers/${public_id}/`),
    ])
      .then(([a, b]) => {
        if (a.status === 'fulfilled') setData(a.value.data);
        else setErr(extractApiError(a.reason));
        if (b.status === 'fulfilled') setTraveler(b.value.data);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [public_id]);

  if (loading) return <div className="card p-10 animate-pulse h-40" />;
  if (err || !data) {
    return (
      <div className="card p-6 text-rose-600 flex items-center justify-between">
        <span>{err || 'Voyageur introuvable.'}</span>
        <button onClick={() => router.back()} className="btn-outline text-sm">
          <ArrowLeft className="h-4 w-4" /> Retour
        </button>
      </div>
    );
  }

  const t = data.traveler;
  const inv = data.investigation;
  const pass = data.pass;

  const formUrl = `${API_URL}/api/v1/ebola/public/pass/${public_id}/official-form.pdf`;
  const passUrl = `${API_URL}/api/v1/ebola/public/pass/${public_id}/pdf/`;

  // Actions (auth requise)
  const recompute = () => {
    if (!inv) return;
    setBusy('recompute');
    api.post(`/ebola/investigations/${inv.case_number}/recompute-score/`)
      .then(() => load())
      .catch((e) => alert(extractApiError(e)))
      .finally(() => setBusy(null));
  };
  const closeCase = () => {
    if (!inv) return;
    if (!confirm(`Clôturer l'enquête ${inv.case_number} ?`)) return;
    setBusy('close');
    api.post(`/ebola/investigations/${inv.case_number}/close/`)
      .then(() => load())
      .catch((e) => alert(extractApiError(e)))
      .finally(() => setBusy(null));
  };
  const revokePass = () => {
    if (!pass) return;
    const reason = prompt('Motif de révocation ?', '');
    if (reason === null) return;
    setBusy('revoke');
    api.post(`/health-pass/${pass.pass_number}/revoke/`, { reason })
      .then(() => load())
      .catch((e) => alert(extractApiError(e)))
      .finally(() => setBusy(null));
  };

  return (
    <div className="space-y-6 animate-fade-up">
      {/* En-tête */}
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <button
            onClick={() => router.back()}
            className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ciOrange font-bold uppercase tracking-wide mb-2"
          >
            <ArrowLeft className="h-3 w-3" /> Retour
          </button>
          <div className="text-[11px] uppercase tracking-widest text-ciOrange font-bold">
            Fiche voyageur · INHP
          </div>
          <h1 className="font-display text-3xl font-black leading-tight">{t.full_name}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <span className="inline-flex items-center gap-1 font-mono text-xs"><Hash className="h-3 w-3" /> {t.public_id}</span>
            <span>·</span>
            <span className="inline-flex items-center gap-1"><Plane className="h-3.5 w-3.5" /> {t.entry_point || '—'}</span>
            <span>·</span>
            <span className="inline-flex items-center gap-1"><Calendar className="h-3.5 w-3.5" /> {t.arrival_date ? formatDate(t.arrival_date) : '—'}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <a href={formUrl} target="_blank" rel="noreferrer" className="btn-outline text-sm">
            <FileText className="h-4 w-4" /> Fiche INHP (PDF)
          </a>
          <a href={passUrl} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold bg-gradient-to-r from-ciOrange to-orange-600 text-white shadow-lg shadow-orange-500/25">
            <Download className="h-4 w-4" /> Pass sanitaire (PDF)
          </a>
        </div>
      </header>

      {/* Bandeau statut */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatusTile
          label="État sanitaire"
          value={STATUS_LABELS[t.current_health_status] || t.current_health_status}
          icon={<Stethoscope className="h-5 w-5" />}
        />
        {inv && (
          <StatusTile
            label="Niveau de risque"
            value={<RiskBadge level={inv.risk_level} score={inv.risk_score} />}
            icon={<AlertTriangle className="h-5 w-5" />}
          />
        )}
        {inv && (
          <StatusTile
            label="Surveillance"
            value={
              inv.surveillance_start && inv.surveillance_end
                ? `${formatDate(inv.surveillance_start)} → ${formatDate(inv.surveillance_end)}`
                : '—'
            }
            icon={<Clock className="h-5 w-5" />}
          />
        )}
        {pass && (
          <StatusTile
            label="Pass sanitaire"
            value={
              <span>
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold ${
                  pass.status === 'active' ? 'bg-emerald-100 text-emerald-700' :
                  pass.status === 'revoked' ? 'bg-rose-100 text-rose-700' :
                  'bg-slate-100 text-slate-700'
                }`}>{pass.status}</span>
                <span className="ml-2 text-xs font-mono">{pass.pass_number}</span>
              </span>
            }
            icon={<ShieldCheck className="h-5 w-5" />}
          />
        )}
      </section>

      {/* Grille principale */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Colonne gauche : sections du formulaire INHP */}
        <div className="lg:col-span-2 space-y-4">
          <Section title="Section 1 — Voyage" icon={<Plane className="h-4 w-4 text-ciOrange" />}>
            <GridKV
              data={[
                ['Date d\'arrivée', traveler?.arrival_date ? formatDate(traveler.arrival_date) : '—'],
                ['Heure d\'arrivée', traveler?.arrival_time || '—'],
                ['Moyen de transport', traveler?.transport_mode || '—'],
                ['N° vol / voyage', traveler?.flight_or_voyage_number || '—'],
                ['N° de siège', traveler?.seat_number || '—'],
                ['Point d\'entrée', traveler?.entry_point_name || '—'],
              ]}
            />
          </Section>

          <Section title="Section 2 — Identité & contacts" icon={<User className="h-4 w-4 text-ciGreen" />}>
            <GridKV
              data={[
                ['Nom', traveler?.last_name || '—'],
                ['Prénoms', `${traveler?.first_name || ''} ${traveler?.middle_name || ''}`.trim() || '—'],
                ['Âge', traveler?.age ? `${traveler.age} ${traveler.age_unit === 'months' ? 'mois' : 'ans'}` : '—'],
                ['Date de naissance', traveler?.date_of_birth ? formatDate(traveler.date_of_birth) : '—'],
                ['Sexe', traveler?.gender === 'M' ? 'Masculin' : traveler?.gender === 'F' ? 'Féminin' : '—'],
                ['Profession', traveler?.profession || '—'],
                ['Pièce', `${traveler?.id_document_type || ''} · ${traveler?.id_document_number || '—'}`],
                ['Nationalité', traveler?.nationality_code || '—'],
                ['Téléphone', traveler?.phone_mobile || '—'],
                ['Email', traveler?.email || '—'],
                ['Adresse postale', traveler?.postal_address || '—'],
              ]}
            />
            {traveler?.passport_document && (
              <a
                href={`${API_URL}${traveler.passport_document.startsWith('/') ? '' : '/'}${traveler.passport_document}`}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold hover:border-ciOrange/60"
              >
                <IdCard className="h-4 w-4 text-ciOrange" /> Document de voyage joint
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </Section>

          <Section title="Section 3 — Historique des déplacements (3 dernières semaines)" icon={<Globe2 className="h-4 w-4 text-ciOrange" />}>
            {!traveler?.travel_history?.length ? (
              <p className="text-sm text-slate-500">Aucun déplacement enregistré.</p>
            ) : (
              <ul className="space-y-2">
                {traveler.travel_history.map((h: any) => (
                  <li key={h.id} className="rounded-xl bg-slate-50 dark:bg-slate-900 px-3 py-2 text-sm">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold">
                        <span className="badge badge-low mr-2">{h.role}</span>
                        {h.country_code} {h.city ? `· ${h.city}` : ''}
                      </div>
                      <div className="text-xs text-slate-500">
                        {h.arrival_date ? formatDate(h.arrival_date) : ''} {h.departure_date ? `→ ${formatDate(h.departure_date)}` : ''}
                      </div>
                    </div>
                    {(h.hotel || h.residence_address) && (
                      <div className="text-xs text-slate-500 mt-1">{[h.hotel, h.residence_address].filter(Boolean).join(' · ')}</div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Section 4 — Adresse de confinement (CI)" icon={<MapPin className="h-4 w-4 text-ciGreen" />}>
            <GridKV
              data={[
                ['Ville', traveler?.confinement_city || '—'],
                ['Commune', traveler?.confinement_commune || '—'],
                ['Quartier', traveler?.confinement_neighborhood || '—'],
                ['N° rue / lot', `${traveler?.confinement_street_number || ''} ${traveler?.confinement_lot ? '· lot ' + traveler.confinement_lot : ''}`.trim() || '—'],
                ['Hôtel / hébergement', traveler?.confinement_hotel || '—'],
                ['N° chambre', traveler?.confinement_room_number || '—'],
                ['Téléphone urgence CI', traveler?.emergency_phone_ci || '—'],
                ['Adresse consolidée', traveler?.confinement_address || '—'],
              ]}
            />
          </Section>

          {inv?.exposure && (
            <Section title="Section 5 — Évaluation du risque (21 derniers jours)" icon={<AlertTriangle className="h-4 w-4 text-ciOrange" />}>
              <ul className="space-y-2 text-sm">
                <YesNo label="Séjour en zone Ebola" value={!!inv.exposure.visited_ebola_zone} extra={inv.exposure.visited_ebola_zone_details} />
                <YesNo label="Contact avec un cas Ebola" value={!!inv.exposure.contact_with_case} />
                <YesNo label="Participation à des funérailles / contact corps" value={!!inv.exposure.attended_funeral_or_touched_corpse} />
                <YesNo label="Visite d'une structure Ebola" value={!!inv.exposure.visited_ebola_healthcare_facility} />
              </ul>
              {typeof inv.exposure.positive_answers_count === 'number' && (
                <div className="mt-3 text-xs text-slate-500">
                  Réponses positives : <b>{inv.exposure.positive_answers_count}/4</b> · Score brut : {inv.exposure.raw_exposure_score}
                </div>
              )}
            </Section>
          )}

          {inv?.last_symptoms && (
            <Section title="Section 6 — État de santé (48 dernières heures)" icon={<Thermometer className="h-4 w-4 text-rose-500" />}>
              {inv.last_symptoms.temperature_celsius != null && (
                <div className="text-sm mb-2">
                  Température : <b>{inv.last_symptoms.temperature_celsius} °C</b>
                  {inv.last_symptoms.has_high_fever && <span className="ml-2 badge badge-high">Fièvre élevée</span>}
                </div>
              )}
              <ul className="space-y-1.5 text-sm">
                <YesNo label="Fièvre" value={!!inv.last_symptoms.fever} />
                <YesNo label="Fatigue intense" value={!!inv.last_symptoms.intense_fatigue} />
                <YesNo label="Douleurs musculaires / articulaires" value={!!inv.last_symptoms.muscle_joint_pain} />
                <YesNo label="Maux de tête sévères" value={!!inv.last_symptoms.severe_headache} />
                <YesNo label="Mal de gorge / abdominal" value={!!inv.last_symptoms.sore_throat_or_abdominal} />
                <YesNo label="Diarrhée, nausées, vomissements" value={!!inv.last_symptoms.diarrhea_nausea_vomiting} />
                <YesNo label="Saignements inexpliqués" value={!!inv.last_symptoms.unexplained_bleeding} highlight />
              </ul>
              {inv.last_symptoms.other_symptoms && (
                <div className="mt-2 text-xs text-slate-500 italic">Autres : {inv.last_symptoms.other_symptoms}</div>
              )}
            </Section>
          )}

          {inv?.declaration && (
            <Section title="Section 7 — Certification & signature" icon={<CheckCircle2 className="h-4 w-4 text-ciGreen" />}>
              <GridKV
                data={[
                  ['Déclarant', inv.declaration.declarant_full_name || '—'],
                  ['Fait à', inv.declaration.signed_place || '—'],
                  ['Date', inv.declaration.declared_at ? formatDateTime(inv.declaration.declared_at) : '—'],
                  ['Certification honneur', inv.declaration.truthful_declaration ? 'Oui' : 'Non'],
                  ['Consentement données', inv.declaration.consent_data_processing ? 'Oui' : 'Non'],
                  ['Consentement suivi santé', inv.declaration.consent_health_followup ? 'Oui' : 'Non'],
                ]}
              />
              {inv.declaration.signature && (
                <div className="mt-3">
                  <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">Signature</div>
                  <img
                    src={`${API_URL}${inv.declaration.signature.startsWith('/') ? '' : '/'}${inv.declaration.signature}`}
                    alt="Signature"
                    className="h-20 object-contain rounded-lg border border-slate-200 dark:border-slate-700 bg-white p-2"
                  />
                </div>
              )}
            </Section>
          )}
        </div>

        {/* Colonne droite : Pass + actions + référence */}
        <aside className="space-y-4">
          {pass && (
            <div className="card p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-black flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-ciGreen" /> Pass sanitaire
                </h3>
                <span className={`text-xs font-bold rounded-full px-2 py-0.5 ${
                  pass.status === 'active' ? 'bg-emerald-100 text-emerald-700' :
                  pass.status === 'revoked' ? 'bg-rose-100 text-rose-700' :
                  'bg-slate-100 text-slate-700'
                }`}>{pass.status}</span>
              </div>
              <div className="mt-3 text-sm space-y-1">
                <div className="font-mono text-xs text-slate-500">{pass.pass_number}</div>
                <div>Émis le : <b>{pass.issued_at ? formatDateTime(pass.issued_at) : '—'}</b></div>
                <div>Expire le : <b>{pass.expires_at ? formatDateTime(pass.expires_at) : '—'}</b></div>
              </div>
              {pass.qr_url && (
                <div className="mt-3 rounded-xl bg-slate-50 dark:bg-slate-900 p-3 grid place-items-center">
                  <img
                    src={`${API_URL}${pass.qr_url.startsWith('/') ? '' : '/'}${pass.qr_url}`}
                    alt="QR pass"
                    className="h-40 w-40 object-contain"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 inline-flex items-center gap-1"><QrCode className="h-3 w-3" /> Scanner pour vérifier</span>
                </div>
              )}
              <div className="mt-3 space-y-2">
                <a href={passUrl} target="_blank" rel="noreferrer" className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-ciOrange to-orange-600 text-white font-bold px-4 py-2.5 text-sm shadow-lg shadow-orange-500/25">
                  <Download className="h-4 w-4" /> Télécharger le pass
                </a>
                {pass.status === 'active' && (
                  <button
                    disabled={busy === 'revoke'}
                    onClick={revokePass}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 dark:border-rose-900 text-rose-600 font-bold px-4 py-2.5 text-sm hover:bg-rose-50 dark:hover:bg-rose-950/30 disabled:opacity-50"
                  >
                    <X className="h-4 w-4" /> Révoquer le pass
                  </button>
                )}
              </div>
            </div>
          )}

          {inv && (
            <div className="card p-5">
              <h3 className="font-display text-lg font-black flex items-center gap-2">
                <Hospital className="h-5 w-5 text-ciOrange" /> Enquête
              </h3>
              <div className="mt-3 text-sm space-y-1">
                <div>N° : <span className="font-mono text-xs">{inv.case_number}</span></div>
                <div>Statut : <b>{STATUS_LABELS[inv.status] || inv.status}</b></div>
                <div>Ouverte : <b>{formatDateTime(inv.created_at)}</b></div>
                <div>Point d'entrée : <b>{inv.entry_point_name || '—'}</b></div>
              </div>
              {inv.notes && (
                <div className="mt-2 rounded-xl bg-slate-50 dark:bg-slate-900 p-3 text-xs text-slate-600 dark:text-slate-300">
                  {inv.notes}
                </div>
              )}
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  disabled={busy === 'recompute'}
                  onClick={recompute}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold hover:border-ciOrange/60 disabled:opacity-50"
                >
                  <RefreshCcw className="h-3.5 w-3.5" /> Recalculer
                </button>
                <button
                  disabled={busy === 'close' || inv.status === 'closed'}
                  onClick={closeCase}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 dark:border-rose-900 text-rose-600 px-3 py-2 text-xs font-bold hover:bg-rose-50 dark:hover:bg-rose-950/30 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <X className="h-3.5 w-3.5" /> Clôturer
                </button>
              </div>
            </div>
          )}

          {/* Contacts rapides */}
          <div className="card p-5">
            <h3 className="font-display text-lg font-black flex items-center gap-2">
              <Phone className="h-5 w-5 text-ciGreen" /> Contacts rapides
            </h3>
            <ul className="mt-3 space-y-1.5 text-sm">
              {t && traveler?.phone_mobile && (
                <li className="flex items-center gap-2">
                  <Phone className="h-3.5 w-3.5 text-slate-400" />
                  <a href={`tel:${traveler.phone_mobile}`} className="hover:text-ciOrange">{traveler.phone_mobile}</a>
                </li>
              )}
              {traveler?.email && (
                <li className="flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-slate-400" />
                  <a href={`mailto:${traveler.email}`} className="hover:text-ciOrange">{traveler.email}</a>
                </li>
              )}
              {traveler?.emergency_phone_ci && (
                <li className="flex items-center gap-2">
                  <Phone className="h-3.5 w-3.5 text-rose-500" />
                  <span className="text-xs text-slate-500">Urgence CI :</span>
                  <a href={`tel:${traveler.emergency_phone_ci}`} className="font-bold hover:text-ciOrange">{traveler.emergency_phone_ci}</a>
                </li>
              )}
            </ul>
          </div>

          {/* Référence rapide */}
          <div className="card p-5">
            <h3 className="font-display text-lg font-black flex items-center gap-2">
              <Briefcase className="h-5 w-5 text-ciOrange" /> Référence
            </h3>
            <ul className="mt-3 space-y-1.5 text-xs text-slate-500">
              <li>Public ID : <span className="font-mono text-slate-700 dark:text-slate-200">{t.public_id}</span></li>
              {inv && <li>Cas : <span className="font-mono text-slate-700 dark:text-slate-200">{inv.case_number}</span></li>}
              {pass && <li>Pass : <span className="font-mono text-slate-700 dark:text-slate-200">{pass.pass_number}</span></li>}
            </ul>
          </div>
        </aside>
      </div>

      {/* ============================================================
          Messages & notifications — historique + envoi rapide
          ============================================================ */}
      <section className="space-y-3 pt-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="font-display text-lg font-bold inline-flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-ciOrange" />
            Messages &amp; notifications
          </h2>
          <button
            type="button"
            onClick={() => setMsgTarget({
              traveler_public_id: t.public_id,
              traveler_name: `${t.last_name} ${t.first_name}`,
              phone: t.phone_mobile || (t as any).whatsapp_phone || '',
              first_name: t.first_name,
            })}
            className="inline-flex items-center gap-2 rounded-xl bg-ciOrange text-white px-4 py-2 text-sm font-semibold shadow hover:bg-orange-600 transition"
          >
            <Send className="h-4 w-4" /> Envoyer un message
          </button>
        </div>
        <NotificationHistory publicId={t.public_id} pageSize={50} />
      </section>

      {msgTarget && (
        <SendMessageModal
          open={!!msgTarget}
          target={msgTarget}
          onClose={() => setMsgTarget(null)}
        />
      )}
    </div>
  );
}

/* ============================================================
   Sub-components
   ============================================================ */
function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <article className="card p-5">
      <h3 className="font-display text-base font-black flex items-center gap-2 mb-3">
        {icon} {title}
      </h3>
      {children}
    </article>
  );
}

function GridKV({ data }: { data: [string, React.ReactNode][] }) {
  return (
    <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
      {data.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-1.5">
          <dt className="text-slate-500">{k}</dt>
          <dd className="font-semibold text-right truncate max-w-[60%]" title={String(v ?? '')}>{v || '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

function YesNo({ label, value, extra, highlight }: { label: string; value: boolean; extra?: string; highlight?: boolean }) {
  return (
    <li className="flex items-center justify-between">
      <span className={highlight && value ? 'font-bold text-rose-600' : ''}>{label}</span>
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold ${
        value ? (highlight ? 'bg-rose-100 text-rose-700' : 'bg-amber-50 text-amber-700') : 'bg-emerald-50 text-emerald-700'
      }`}>
        {value ? `Oui${extra ? ' · ' + extra : ''}` : 'Non'}
      </span>
    </li>
  );
}

function StatusTile({ label, value, icon }: { label: string; value: React.ReactNode; icon: React.ReactNode }) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className="h-10 w-10 rounded-xl bg-orange-50 dark:bg-orange-950/40 text-ciOrange grid place-items-center">{icon}</div>
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-wide font-bold text-slate-500">{label}</div>
        <div className="font-semibold text-sm mt-0.5 truncate">{value}</div>
      </div>
    </div>
  );
}
