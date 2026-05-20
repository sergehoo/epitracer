'use client';

import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { QRCodeSVG } from 'qrcode.react';
import { Download, FileBadge2, MapPin, ShieldAlert, ShieldCheck, TimerReset } from 'lucide-react';
import { Section } from '@/components/ui/Section';
import { RiskBadge } from '@/components/ui/RiskBadge';
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
  };
  investigation: any | null;
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
}

export default function PassDetailPage() {
  const params = useParams<{ publicId: string }>();
  const search = useSearchParams();
  const justIssued = search.get('just_issued') === '1';

  const [data, setData] = useState<PassConsultPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = params?.publicId;
    if (!id) return;
    setLoading(true);
    api.get<PassConsultPayload>(`/ebola/public/pass/${id}/`)
      .then((r) => setData(r.data))
      .catch((e) => setError(extractApiError(e)))
      .finally(() => setLoading(false));
  }, [params?.publicId]);

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

  return (
    <Section
      eyebrow="Pass sanitaire numérique"
      title={`Bonjour ${t.full_name}`}
      description={`Votre identifiant voyageur : ${t.public_id}`}
    >
      {justIssued && (
        <div className="mb-6 rounded-xl bg-emerald-50 border border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-900 p-4 text-sm flex items-start gap-2">
          <ShieldCheck className="h-5 w-5 text-emerald-700 dark:text-emerald-300 mt-0.5" />
          <div>
            Votre fiche a été enregistrée auprès de l'INHP. Votre pass sanitaire est délivré ci-dessous.
            Conservez cette page et présentez le QR au contrôle.
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Carte pass */}
        <article className="card p-6 lg:col-span-2 space-y-6">
          <header className="flex items-center justify-between gap-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-emerald-700 dark:text-emerald-400 font-semibold">
                Pass sanitaire — République de Côte d'Ivoire
              </div>
              <h3 className="font-display text-2xl font-bold mt-1">{hp?.pass_number || '—'}</h3>
            </div>
            {hp ? <RiskBadge level={hp.risk_level} score={hp.risk_score} /> : null}
          </header>

          {hp ? (
            <div className="grid sm:grid-cols-[auto,1fr] gap-6 items-center">
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-card">
                <QRCodeSVG value={hp.qr_token} size={220} includeMargin />
              </div>
              <dl className="space-y-3 text-sm">
                <Row label="Statut">
                  <span className="font-semibold">{STATUS_LABELS[hp.status] || hp.status}</span>
                </Row>
                <Row label="Maladie suivie">Maladie à Virus Ebola (MVE)</Row>
                <Row label="Émis le">{formatDateTime(hp.issued_at)}</Row>
                <Row label="Expire le">{formatDateTime(hp.expires_at)}</Row>
                <Row label="Signature">Cryptographique Ed25519 · vérifiable hors-ligne</Row>
              </dl>
            </div>
          ) : (
            <div className="text-rose-600">Aucun pass délivré pour ce voyageur.</div>
          )}

          <div className="flex flex-wrap gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
            {hp?.pdf_url && (
              <a
                href={hp.pdf_url.startsWith('http') ? hp.pdf_url : `${API_URL}${hp.pdf_url}`}
                target="_blank" rel="noreferrer"
                className="btn-secondary"
              >
                <Download className="h-4 w-4" /> Télécharger le PDF
              </a>
            )}
            <a href="/verifier" className="btn-outline">
              <FileBadge2 className="h-4 w-4" /> Vérifier un autre QR
            </a>
          </div>
        </article>

        {/* Sidebar : statut + instructions */}
        <aside className="space-y-4">
          <div className="card p-5">
            <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">Votre situation</div>
            <div className="mt-2 flex items-center justify-between">
              <span>Statut sanitaire</span>
              <span className="badge-low">{STATUS_LABELS[t.current_health_status] || t.current_health_status}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Arrivée</span>
              <span>{formatDate(t.arrival_date)}</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Point d'entrée</span>
              <span className="text-right">{t.entry_point || '—'}</span>
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <TimerReset className="h-4 w-4 text-emerald-600" />
              Suivi sanitaire 21 jours
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Conformément au protocole INHP, mesurez votre température chaque jour et signalez tout
              symptôme aux services sanitaires.
            </p>
          </div>

          <div className="card p-5 bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900">
            <div className="flex items-center gap-2 text-sm font-semibold text-rose-700 dark:text-rose-300">
              <ShieldAlert className="h-4 w-4" />
              En cas de symptômes
            </div>
            <div className="mt-2 text-sm">
              SAMU <a href="tel:185" className="font-bold">185</a> · Allô Santé <a href="tel:143" className="font-bold">143</a> · Secours <a href="tel:101" className="font-bold">101</a>
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <MapPin className="h-4 w-4 text-emerald-600" />
              Conservez cette page
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Mettez cette URL en favori. En cas de perte, vous pouvez la retrouver via la page
              <a className="underline ml-1" href="/pass">Mon Pass</a> avec votre identifiant.
            </p>
          </div>
        </aside>
      </div>
    </Section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-2 last:border-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  );
}
