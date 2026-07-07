'use client';

/**
 * Page détail voyageur — fiche complète d'identité, voyage, contact, pass.
 *
 * Distincte de `/suivi-voyageurs/[travelerId]` (qui est la fiche de suivi
 * sanitaire/médicale 21j). Ici on a l'identité administrative + le pass +
 * un raccourci vers le suivi médical et l'itinéraire.
 */

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, RefreshCcw, User as UserIcon, Phone, Mail, MapPin,
  Calendar, Plane, BadgeCheck, AlertTriangle, Send, Map as MapIcon,
  Activity, FileText,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import { SendMessageModal, type SendMessageTarget } from '@/components/notifications/SendMessageModal';

interface TravelerDetail {
  id: number;
  public_id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  gender: string;
  date_of_birth: string | null;
  nationality: { code: string; name: string } | string | null;
  id_document_type: string;
  id_document_number: string;
  id_document_country: { code: string; name: string } | string | null;
  phone_mobile: string;
  whatsapp_phone: string;
  email: string;
  emergency_phone_ci: string;
  // Voyage
  arrival_date: string | null;
  flight_number: string;
  seat_number: string;
  transport_mode: string;
  entry_point: { id: number; name: string; code: string } | string | null;
  origin_country: string;
  origin_city: string;
  // Hébergement
  confinement_city: string;
  confinement_commune: string;
  confinement_neighborhood: string;
  confinement_address: string;
  // Santé
  current_health_status: string;
  current_risk_level?: string;
  current_quarantine_status?: string;
  // Pass
  pass_number?: string;
  pass_expires_at?: string;
  // Méta
  created_at: string;
}

function fmt(s: string | null | undefined): string {
  if (!s) return '—';
  return s;
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—';
  try {
    return new Date(s).toLocaleDateString('fr-FR');
  } catch {
    return s;
  }
}

function unwrap(v: any, key: string = 'name'): string {
  if (!v) return '—';
  if (typeof v === 'string') return v;
  if (typeof v === 'object' && key in v) return v[key];
  return String(v);
}

export default function TravelerDetailPage() {
  const params = useParams<{ publicId: string }>();
  const publicId = params?.publicId;
  const [data, setData] = useState<TravelerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msgOpen, setMsgOpen] = useState(false);

  const load = () => {
    if (!publicId) return;
    setLoading(true);
    setError(null);
    api.get<TravelerDetail>(`/travelers/${publicId}/`)
      .then((r) => setData(r.data))
      .catch((e) => {
        const msg = extractApiError(e);
        setError(msg);
        toast.error(msg);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [publicId]);

  const sendTarget: SendMessageTarget | null = data
    ? {
        traveler_id: data.id,
        traveler_public_id: data.public_id,
        traveler_name: data.full_name || `${data.first_name} ${data.last_name}`.trim(),
        phone: data.whatsapp_phone || data.phone_mobile || '',
        email: data.email || '',
        first_name: data.first_name || '',
      }
    : null;

  return (
    <div data-theme="light" className="light space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <Link
          href="/voyageurs"
          className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-ciOrange transition"
        >
          <ArrowLeft className="h-4 w-4" /> Retour à la liste
        </Link>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold hover:bg-slate-50 disabled:opacity-40"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Actualiser
          </button>
        </div>
      </div>

      {loading && !data ? (
        <div className="rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          Chargement…
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          <div className="font-bold mb-1 inline-flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> Voyageur introuvable
          </div>
          <p>{error}</p>
          <p className="mt-2 text-xs">
            ID demandé : <code>{publicId}</code>
          </p>
        </div>
      ) : data ? (
        <>
          {/* Header identité */}
          <header className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex items-start gap-4">
                <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-ciOrange to-orange-600 text-white grid place-items-center shadow-md">
                  <UserIcon className="h-7 w-7" />
                </div>
                <div>
                  <h1 className="font-display text-2xl font-black text-ciDark">
                    {data.full_name || `${data.first_name} ${data.last_name}`}
                  </h1>
                  <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="font-mono font-semibold text-slate-700">{data.public_id}</span>
                    <span>{data.gender === 'M' ? 'Masculin' : data.gender === 'F' ? 'Féminin' : data.gender}</span>
                    {data.date_of_birth && <span>Né(e) le {fmtDate(data.date_of_birth)}</span>}
                    <span>{unwrap(data.nationality)}</span>
                  </div>
                  {data.pass_number && (
                    <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200">
                      <BadgeCheck className="h-3 w-3" /> Pass {data.pass_number}
                      {data.pass_expires_at && (
                        <span className="opacity-70">· expire {fmtDate(data.pass_expires_at)}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setMsgOpen(true)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700"
                >
                  <Send className="h-3.5 w-3.5" /> Envoyer notification
                </button>
                <Link
                  href={`/suivi-voyageurs/${data.public_id}`}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-sky-600 text-white text-xs font-semibold hover:bg-sky-700"
                >
                  <Activity className="h-3.5 w-3.5" /> Suivi médical →
                </Link>
                <Link
                  href={`/voyageurs/${data.public_id}/itineraire`}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold hover:bg-slate-50"
                >
                  <MapIcon className="h-3.5 w-3.5" /> Itinéraire & contacts
                </Link>
              </div>
            </div>
          </header>

          {/* Grille de cards */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Identité */}
            <Card title="Identité" icon={<UserIcon className="h-4 w-4" />}>
              <Row label="Document" value={`${fmt(data.id_document_type).toUpperCase()} ${data.id_document_number}`} />
              <Row label="Émis par" value={unwrap(data.id_document_country)} />
              <Row label="Nationalité" value={unwrap(data.nationality)} />
            </Card>

            {/* Contact */}
            <Card title="Contact" icon={<Phone className="h-4 w-4" />}>
              <Row
                label="Téléphone"
                value={data.phone_mobile || '—'}
                href={data.phone_mobile ? `tel:${data.phone_mobile}` : undefined}
              />
              <Row
                label="WhatsApp"
                value={data.whatsapp_phone || '—'}
                href={data.whatsapp_phone ? `https://wa.me/${data.whatsapp_phone.replace(/\D/g, '')}` : undefined}
              />
              <Row
                label="Email"
                value={data.email || '—'}
                href={data.email ? `mailto:${data.email}` : undefined}
              />
              {data.emergency_phone_ci && (
                <Row label="Tél. d'urgence" value={data.emergency_phone_ci} href={`tel:${data.emergency_phone_ci}`} />
              )}
            </Card>

            {/* Voyage */}
            <Card title="Voyage" icon={<Plane className="h-4 w-4" />}>
              <Row label="Arrivée" value={fmtDate(data.arrival_date)} />
              <Row label="Vol / Transport" value={data.flight_number || '—'} />
              <Row label="Siège" value={data.seat_number || '—'} />
              <Row label="Mode" value={data.transport_mode || '—'} />
              <Row label="Point d'entrée" value={unwrap(data.entry_point)} />
              <Row label="Origine" value={[data.origin_city, data.origin_country].filter(Boolean).join(', ') || '—'} />
            </Card>

            {/* Hébergement / confinement */}
            <Card title="Hébergement" icon={<MapPin className="h-4 w-4" />}>
              <Row label="Ville" value={data.confinement_city || '—'} />
              <Row label="Commune" value={data.confinement_commune || '—'} />
              <Row label="Quartier" value={data.confinement_neighborhood || '—'} />
              {data.confinement_address && (
                <Row label="Adresse" value={data.confinement_address} multiline />
              )}
            </Card>

            {/* Santé */}
            <Card title="Statut sanitaire" icon={<Activity className="h-4 w-4" />}>
              <Row label="État" value={data.current_health_status || '—'} />
              <Row label="Niveau de risque" value={data.current_risk_level || '—'} />
              <Row label="Quarantaine" value={data.current_quarantine_status || '—'} />
              <div className="mt-3">
                <Link
                  href={`/suivi-voyageurs/${data.public_id}`}
                  className="text-xs text-sky-700 hover:underline font-semibold inline-flex items-center gap-1"
                >
                  Voir le suivi sanitaire complet (J1-J21) →
                </Link>
              </div>
            </Card>

            {/* Pass */}
            <Card title="Pass santé" icon={<BadgeCheck className="h-4 w-4" />}>
              <Row label="N° Pass" value={data.pass_number || '—'} />
              <Row label="Expire" value={fmtDate(data.pass_expires_at)} />
              <Row label="Inscrit le" value={fmtDate(data.created_at)} />
              {data.pass_number && (
                <div className="mt-3">
                  <a
                    href={`/api/v1/passes/${data.pass_number}/pdf/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-ciOrange hover:underline font-semibold inline-flex items-center gap-1"
                  >
                    <FileText className="h-3 w-3" /> Télécharger le pass PDF
                  </a>
                </div>
              )}
            </Card>
          </div>
        </>
      ) : null}

      {/* Modale notification */}
      {msgOpen && sendTarget && (
        <SendMessageModal
          target={sendTarget}
          open={msgOpen}
          onClose={() => setMsgOpen(false)}
        />
      )}
    </div>
  );
}

function Card({
  title, icon, children,
}: {
  title: string; icon: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3 inline-flex items-center gap-1.5">
        <span className="text-ciOrange">{icon}</span>
        {title}
      </div>
      <div className="space-y-2 text-sm">{children}</div>
    </div>
  );
}

function Row({
  label, value, href, multiline,
}: {
  label: string; value: string; href?: string; multiline?: boolean;
}) {
  const content = href ? (
    <a href={href} className="text-ciOrange hover:underline">
      {value}
    </a>
  ) : (
    <span className={`text-slate-700 ${multiline ? 'whitespace-pre-wrap' : ''}`}>{value}</span>
  );
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-xs text-slate-500 uppercase tracking-wide font-semibold shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-right">{content}</span>
    </div>
  );
}
