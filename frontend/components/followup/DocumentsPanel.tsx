'use client';

/**
 * DocumentsPanel — Phase 9F.
 *
 * Liste les PDFs générés (fiches, orientations, rapports labo, attestations)
 * et permet d'en lancer la génération asynchrone (Celery côté backend).
 *
 * Endpoints :
 *   GET  /admin/followups/{id}/documents/
 *        → { documents: DocumentItem[], available_types: [...] }
 *   POST /admin/followups/{id}/documents/?type=sheet|orientation|sample|certificate
 *        (+ sample_id=X si type=sample)
 *
 * Stratégie de "poll" : après un POST, on refetch la liste toutes les 5s
 * pendant 60s — c'est suffisant pour voir apparaître le PDF généré par
 * Celery dans des conditions normales.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  FileText, FileSpreadsheet, FileCheck, FilePlus2, Download,
  Loader2, RefreshCcw, AlertTriangle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import type { MedicalSample } from './SamplePanel';

interface DocumentItem {
  id: string;
  type: 'sheet' | 'orientation' | 'sample_report' | 'certificate' | string;
  label: string;
  filename: string;
  url: string;
  generated_at: string;
  size_bytes: number;
  generated_by?: { actor_id: number | null; actor_name: string };
}

interface Props {
  travelerId: string;
  /** Statut courant — sert à désactiver le bouton "certificat" si non-clôturé. */
  caseStatus?: string;
  /** Liste des prélèvements connus pour proposer un dropdown. */
  samples?: MedicalSample[];
}

const DOC_TYPE_TONE: Record<string, string> = {
  sheet: 'bg-sky-100 text-sky-700 border-sky-200',
  orientation: 'bg-amber-100 text-amber-700 border-amber-200',
  sample_report: 'bg-violet-100 text-violet-700 border-violet-200',
  certificate: 'bg-emerald-100 text-emerald-700 border-emerald-200',
};

const DOC_TYPE_ICON: Record<string, React.ReactNode> = {
  sheet: <FileText className="h-3 w-3" />,
  orientation: <FilePlus2 className="h-3 w-3" />,
  sample_report: <FileSpreadsheet className="h-3 w-3" />,
  certificate: <FileCheck className="h-3 w-3" />,
};

function formatBytes(n?: number): string {
  if (!n || n < 1) return '—';
  if (n < 1024) return `${n} o`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`;
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`;
}

function formatDateTime(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function DocumentsPanel({ travelerId, caseStatus, samples = [] }: Props) {
  const [items, setItems] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [sampleId, setSampleId] = useState<string>('');
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollStop = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchList = async () => {
    setLoading(true);
    try {
      const resp = await api.get<{ documents: DocumentItem[] }>(
        `/admin/followups/${travelerId}/documents/`,
      );
      setItems(resp.data?.documents ?? []);
    } catch (e) {
      // best-effort : on n'affiche le toast que si pas en poll silencieux
      toast.error(extractApiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
      if (pollStop.current) clearTimeout(pollStop.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [travelerId]);

  /** Démarre un poll toutes les 5s pendant 60s, sans afficher d'erreurs. */
  const startPoll = () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    if (pollStop.current) clearTimeout(pollStop.current);
    pollTimer.current = setInterval(async () => {
      try {
        const resp = await api.get<{ documents: DocumentItem[] }>(
          `/admin/followups/${travelerId}/documents/`,
        );
        setItems(resp.data?.documents ?? []);
      } catch {
        /* silencieux pendant le poll */
      }
    }, 5_000);
    pollStop.current = setTimeout(() => {
      if (pollTimer.current) clearInterval(pollTimer.current);
      pollTimer.current = null;
    }, 60_000);
  };

  const generate = async (type: 'sheet' | 'orientation' | 'sample' | 'certificate') => {
    if (type === 'sample' && !sampleId) {
      toast.error('Sélectionnez un prélèvement.');
      return;
    }
    setGenerating(type);
    try {
      const params: Record<string, string> = { type };
      if (type === 'sample') params.sample_id = sampleId;
      await api.post(
        `/admin/followups/${travelerId}/documents/`,
        {},
        { params },
      );
      toast.success('Génération en cours…');
      startPoll();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setGenerating(null);
    }
  };

  const sortedItems = useMemo(
    () => [...items].sort((a, b) => {
      const da = new Date(a.generated_at).getTime();
      const db = new Date(b.generated_at).getTime();
      return db - da;
    }),
    [items],
  );

  const certificateDisabled = caseStatus && caseStatus !== 'completed';

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-emerald-600" />
            <h2 className="font-display text-lg font-black text-ciDark">Documents PDF</h2>
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Fiches de suivi, orientations médicales, rapports labo, attestations.
          </div>
        </div>
        <button
          type="button"
          onClick={fetchList}
          disabled={loading}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </button>
      </header>

      {/* Boutons "Générer..." */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
        <button
          type="button"
          onClick={() => generate('sheet')}
          disabled={generating !== null}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-sky-200 bg-sky-50 text-sky-700 px-3 py-2 text-xs font-bold hover:bg-sky-100 disabled:opacity-50"
        >
          {generating === 'sheet' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
          Fiche de suivi
        </button>
        <button
          type="button"
          onClick={() => generate('orientation')}
          disabled={generating !== null}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 text-amber-700 px-3 py-2 text-xs font-bold hover:bg-amber-100 disabled:opacity-50"
        >
          {generating === 'orientation' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FilePlus2 className="h-3.5 w-3.5" />}
          Fiche d'orientation
        </button>
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={() => generate('sample')}
            disabled={generating !== null || !sampleId}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-violet-200 bg-violet-50 text-violet-700 px-3 py-2 text-xs font-bold hover:bg-violet-100 disabled:opacity-50"
          >
            {generating === 'sample' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileSpreadsheet className="h-3.5 w-3.5" />}
            Rapport prélèvement
          </button>
          <select
            value={sampleId}
            onChange={(e) => setSampleId(e.target.value)}
            className="text-[11px] rounded-lg border border-slate-200 px-2 py-1"
          >
            <option value="">Choisir un prélèvement…</option>
            {samples.map((s) => (
              <option key={s.id} value={String(s.id)}>
                {s.sample_code || `#${s.id}`}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={() => generate('certificate')}
          disabled={generating !== null || !!certificateDisabled}
          title={certificateDisabled ? 'Disponible uniquement après clôture du suivi' : ''}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700 px-3 py-2 text-xs font-bold hover:bg-emerald-100 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {generating === 'certificate' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileCheck className="h-3.5 w-3.5" />}
          Attestation fin
        </button>
      </div>

      {certificateDisabled && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-700 flex items-center gap-2 mb-3">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          L'attestation de fin de suivi ne peut être générée qu'après clôture (statut = completed).
        </div>
      )}

      {/* Liste documents */}
      {sortedItems.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-sm">
          {loading ? 'Chargement…' : 'Aucun document généré pour ce suivi.'}
        </div>
      ) : (
        <ul className="space-y-2">
          {sortedItems.map((doc) => {
            const tone = DOC_TYPE_TONE[doc.type] ?? 'bg-slate-100 text-slate-700 border-slate-200';
            const icon = DOC_TYPE_ICON[doc.type] ?? <FileText className="h-3 w-3" />;
            return (
              <li
                key={doc.id}
                className="rounded-xl border border-slate-200 bg-white p-3 flex items-start justify-between gap-3 flex-wrap"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase ${tone}`}>
                      {icon} {doc.label || doc.type}
                    </span>
                    <span className="font-bold text-slate-800 text-sm break-all">
                      {doc.filename}
                    </span>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-500 flex flex-wrap gap-x-3 gap-y-0.5">
                    <span>{formatDateTime(doc.generated_at)}</span>
                    <span>{formatBytes(doc.size_bytes)}</span>
                    {doc.generated_by?.actor_name && (
                      <span>par {doc.generated_by.actor_name}</span>
                    )}
                  </div>
                </div>
                <a
                  href={doc.url}
                  target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 text-white px-3 py-1.5 text-xs font-bold hover:bg-emerald-700 shrink-0"
                >
                  <Download className="h-3.5 w-3.5" /> Télécharger
                </a>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default DocumentsPanel;
