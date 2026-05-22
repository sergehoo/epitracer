'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { QRCodeSVG } from 'qrcode.react';
import {
  Download, FileBadge2, FileText, MapPin, ShieldAlert, ShieldCheck, Smartphone,
} from 'lucide-react';
import { Section } from '@/components/ui/Section';
import { VoyageurSubnav } from '@/components/public/VoyageurSubnav';
import { RiskBadge } from '@/components/ui/RiskBadge';
import { Companion21Days } from '@/components/public/Companion21Days';
import { PassportUploader } from '@/components/public/PassportUploader';
import { api, API_URL, extractApiError } from '@/lib/api';
import { formatDate, formatDateTime, STATUS_LABELS } from '@/lib/utils';
import type { RiskLevel } from '@/types/ebola';

interface PassConsultPayload {
  traveler: {
    public_id: string;
    full_name: string;
    current_health_status: string;
    arrival_date: string | null;
    entry_point: string | null;
    has_passport: boolean;
  };
  investigation: {
    case_number: string;
    risk_level: RiskLevel;
    risk_score: number;
    surveillance_start: string | null;
    surveillance_end: string | null;
  } | null;
  pass: {
    pass_number: string;
    status: string;
    risk_level: RiskLevel;
    risk_score: number;
    issued_at: string;
    expires_at: string;
    qr_url: string | null;
    pdf_url: string | null;
    qr_token: string;
  } | null;
  downloads: {
    pass_pdf: string;
    official_form_pdf: string;
  };
}

export default function PassDetailPage() {
  const params = useParams<{ publicId: string }>();
  const search = useSearchParams();
  const justIssued = search.get('just_issued') === '1';

  const [data, setData] = useState<PassConsultPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    const id = params?.publicId;
    if (!id) return;
    setLoading(true);
    api
      .get<PassConsultPayload>(`/ebola/public/pass/${id}/`)
      .then((r) => setData(r.data))
      .catch((e) => setError(extractApiError(e)))
      .finally(() => setLoading(false));
  }, [params?.publicId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <Section title="Chargement du pass…">
        <div className="card p-10 animate-pulse h-72" />
      </Section>
    );
  }

  if (error || !data) {
    return (
      <Section title="Pass introuvable">
        <div className="card p-8 text-rose-600">{error || 'Aucun pass trouvé pour cet identifiant.'}</div>
      </Section>
    );
  }

  const hp = data.pass;
  const t = data.traveler;
  const inv = data.investigation;
  const absUrl = (path: string) =>
    path.startsWith('http') ? path : `${API_URL}${path}`;

  return (
    <Section
      eyebrow="Pass sanitaire numérique"
      title={`Bonjour ${t.full_name}`}
      description={`Votre identifiant voyageur : ${t.public_id}`}
    >
      <VoyageurSubnav publicId={t.public_id} />

      {justIssued && (
        <div className="mb-6 rounded-2xl bg-gradient-to-r from-emerald-50 to-orange-50 border border-emerald-200 dark:border-emerald-900 p-5 flex items-start gap-3">
          <ShieldCheck className="h-6 w-6 text-emerald-700 mt-0.5" />
          <div>
            <div className="font-display font-black text-ciDark">Fiche enregistrée par l'INHP</div>
            <div className="text-sm text-slate-700 mt-1">
              Votre pass sanitaire est délivré. Conservez cette page ou téléchargez les documents
              ci-dessous pour les présenter au contrôle.
            </div>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* ============ Carte principale du pass ============ */}
        <article className="lg:col-span-2 rounded-[2rem] overflow-hidden shadow-2xl border border-slate-200 dark:border-slate-800">
          {/* Bandeau drapeau ivoirien */}
          <div className="grid grid-cols-3 h-3">
            <div className="bg-ciOrange" />
            <div className="bg-white" />
            <div className="bg-ciGreen" />
          </div>

          {/* En-tête sombre avec 3 logos officiels */}
          <div className="bg-ciDark text-white px-6 py-5 flex items-center gap-3">
            <img
              src="/logo-min-sante-2.png"
              alt="MSHPCMU"
              className="h-12 w-12 rounded-xl bg-white p-1 object-contain shadow"
            />
            <img
              src="/armoirie-ci-2.png"
              alt="Armoiries Côte d'Ivoire"
              className="h-12 w-12 rounded-xl bg-white p-1 object-contain shadow"
            />
            <img
              src="/logo-INHP.png"
              alt="INHP"
              className="h-10 w-auto rounded-xl bg-white p-1 object-contain shadow"
            />
            <div className="leading-tight ml-2">
              <div className="text-[10px] uppercase tracking-widest text-white/80">
                RÉPUBLIQUE DE CÔTE D'IVOIRE
              </div>
              <div className="font-display font-black text-base">Pass Sanitaire National</div>
              <div className="text-[11px] text-emerald-200 mt-0.5">
                MSHPCMU · Institut National d'Hygiène Publique
              </div>
            </div>
            <div className="ml-auto text-right">
              <div className="text-[10px] uppercase text-white/70">N° de pass</div>
              <div className="font-display font-black text-lg text-ciGold">
                {hp?.pass_number || '—'}
              </div>
            </div>
          </div>

          {hp ? (
            <div className="bg-white dark:bg-slate-900 p-6 grid sm:grid-cols-[auto,1fr] gap-6 items-start">
              {/* QR avec cadre tricolore */}
              <div className="relative">
                <div className="absolute -inset-1.5 rounded-2xl bg-gradient-to-b from-ciOrange via-white to-ciGreen" />
                <div className="relative bg-white p-4 rounded-2xl">
                  <QRCodeSVG value={hp.qr_token} size={200} includeMargin />
                </div>
                <div className="mt-2 text-[10px] text-center text-slate-500 italic">
                  Signature Ed25519 · vérifiable hors-ligne
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between gap-3">
                  <RiskBadge level={hp.risk_level} score={hp.risk_score} />
                  <span className={`badge-${hp.status === 'active' ? 'low' : 'high'}`}>
                    {STATUS_LABELS[hp.status] || hp.status}
                  </span>
                </div>

                <dl className="mt-4 space-y-2.5 text-sm">
                  <Row label="Voyageur" value={t.full_name} accent />
                  <Row label="ID voyageur" value={t.public_id} />
                  <Row label="Maladie suivie" value="Maladie à Virus Ebola (MVE)" />
                  <Row label="Point d'entrée" value={t.entry_point || '—'} />
                  <Row label="Émis le" value={formatDateTime(hp.issued_at)} />
                  <Row label="Expire le" value={formatDateTime(hp.expires_at)} />
                </dl>
              </div>
            </div>
          ) : (
            <div className="bg-white p-6 text-rose-600">Aucun pass délivré pour ce voyageur.</div>
          )}

          {/* Pied tricolore + boutons */}
          <div className="bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 p-5 flex flex-wrap gap-3 justify-end">
            <a
              href={absUrl(data.downloads.official_form_pdf)}
              target="_blank" rel="noreferrer"
              className="btn-paper"
            >
              <FileText className="h-4 w-4" /> Fiche officielle INHP (PDF)
            </a>
            <a
              href={absUrl(data.downloads.pass_pdf)}
              target="_blank" rel="noreferrer"
              className="btn-dark"
            >
              <Download className="h-4 w-4" /> Télécharger mon pass
            </a>
          </div>

          <div className="grid grid-cols-3 h-3">
            <div className="bg-ciOrange" />
            <div className="bg-white" />
            <div className="bg-ciGreen" />
          </div>
        </article>

        {/* ============ Sidebar ============ */}
        <aside className="space-y-4">
          <Companion21Days
            surveillanceStart={inv?.surveillance_start}
            surveillanceEnd={inv?.surveillance_end}
          />

          {/* Accès rapide à l'espace de check-in quotidien */}
          <a
            href={`/voyageur/suivi?id=${t.public_id}`}
            className="card p-5 block hover:shadow-lg transition bg-gradient-to-br from-emerald-50 to-orange-50 dark:from-emerald-950/30 dark:to-orange-950/20 border-emerald-200/60"
          >
            <div className="text-xs uppercase tracking-widest text-emerald-700 font-bold">
              Espace de suivi
            </div>
            <div className="font-display font-black text-ciDark dark:text-emerald-100 mt-1">
              Donner de mes nouvelles
            </div>
            <div className="text-xs text-slate-600 dark:text-slate-300 mt-1">
              Check-in quotidien · partage facultatif de ma position
            </div>
          </a>

          <PassportUploader
            publicId={t.public_id}
            hasPassport={t.has_passport}
            onUploaded={load}
          />

          <div className="card p-5 bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900">
            <div className="flex items-center gap-2 text-sm font-semibold text-rose-700 dark:text-rose-300">
              <ShieldAlert className="h-4 w-4" />
              En cas de symptômes
            </div>
            <div className="mt-2 text-sm">
              SAMU <a href="tel:185" className="font-black text-ciOrange">185</a> ·
              Allô Santé <a href="tel:143" className="font-black text-ciOrange">143</a> ·
              Secours <a href="tel:101" className="font-black text-ciOrange">101</a>
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Smartphone className="h-4 w-4 text-ciOrange" />
              Installer l'application
            </div>
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 leading-5">
              Ajoutez ce portail à votre écran d'accueil pour consulter votre pass <strong>hors-ligne</strong>.
              Sur iPhone : Partager → « Sur l'écran d'accueil ». Sur Android : menu ⋮ → « Installer l'app ».
            </p>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <MapPin className="h-4 w-4 text-ciGreen" />
              Conservez cette page
            </div>
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 leading-5">
              Mettez-la en favori. En cas de perte, utilisez la page
              <a className="underline ml-1" href="/pass">Mon Pass</a> avec votre identifiant.
            </p>
          </div>
        </aside>
      </div>
    </Section>
  );
}

function Row({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="grid grid-cols-[110px,1fr] items-baseline gap-3 border-b border-slate-100 dark:border-slate-800 pb-2 last:border-0">
      <dt className="text-[10px] uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={accent ? 'font-black text-ciOrange' : 'font-semibold'}>{value}</dd>
    </div>
  );
}
