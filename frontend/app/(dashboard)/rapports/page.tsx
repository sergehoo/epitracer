'use client';

/**
 * /dashboard/rapports — Centre de rapports opérationnels.
 *
 * Affiche les rapports disponibles sous forme de cartes. Chaque carte ouvre
 * un modal de paramètres (période + filtres spécifiques) puis déclenche un
 * téléchargement direct CSV ou PDF généré côté backend (apps.reports).
 */

import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import {
  AlertTriangle, BarChart3, Building2, CalendarDays, ClipboardCheck,
  Download, FileSpreadsheet, FileText, Globe2, HeartPulse, Users,
} from 'lucide-react';
import { api, extractApiError, API_URL } from '@/lib/api';

// =========================================================================
// Métadonnées des rapports — alignées sur apps.reports.views.REPORT_CATALOG
// =========================================================================

type Tone = 'orange' | 'emerald' | 'rose' | 'amber' | 'slate' | 'sky' | 'dark';
type Fmt = 'pdf' | 'csv';

interface ReportDef {
  key: string;
  title: string;
  desc: string;
  icon: React.ReactNode;
  tone: Tone;
  formats: Fmt[];
  filters: ('disease' | 'entry_point' | 'severity' | 'status' | 'qstatus' | 'alert_raised' | 'transport_mode')[];
  /** Si défini → endpoint backend ; sinon → carte "à venir" */
  endpoint?: string;
}

const REPORTS: ReportDef[] = [
  {
    key: 'travelers',
    title: 'Voyageurs enregistrés',
    desc: 'Liste détaillée des voyageurs avec point d\'entrée, transport et statut.',
    icon: <Users />, tone: 'emerald', formats: ['csv', 'pdf'],
    filters: ['entry_point', 'transport_mode'],
    endpoint: '/reports/travelers/',
  },
  {
    key: 'alerts',
    title: 'Alertes de santé',
    desc: 'Alertes ouvertes / résolues avec sévérité, maladie et délais.',
    icon: <AlertTriangle />, tone: 'rose', formats: ['csv', 'pdf'],
    filters: ['severity', 'status', 'disease'],
    endpoint: '/reports/alerts/',
  },
  {
    key: 'followups',
    title: 'Suivi 21 jours',
    desc: 'Quarantaines avec taux de check-ins et alertes déclenchées.',
    icon: <HeartPulse />, tone: 'amber', formats: ['csv', 'pdf'],
    filters: ['qstatus', 'disease'],
    endpoint: '/reports/followups/',
  },
  {
    key: 'checkins',
    title: 'Check-ins quotidiens',
    desc: 'Détail des auto-déclarations (symptômes, alertes).',
    icon: <ClipboardCheck />, tone: 'sky', formats: ['csv', 'pdf'],
    filters: ['alert_raised'],
    endpoint: '/reports/checkins/',
  },
  {
    key: 'overview',
    title: 'Synthèse épidémiologique',
    desc: 'Vue d\'ensemble : KPIs nationaux + top maladies/points d\'entrée.',
    icon: <BarChart3 />, tone: 'dark', formats: ['pdf'],
    filters: [],
    endpoint: '/reports/overview/',
  },
  // ----- Rapports à venir (UI conservée pour roadmap visible) -----
  {
    key: 'daily',
    title: 'Rapport journalier',
    desc: 'Synthèse 24h envoyée chaque matin au comité de pilotage.',
    icon: <CalendarDays />, tone: 'orange', formats: ['pdf', 'csv'],
    filters: [],
  },
  {
    key: 'by_district',
    title: 'Rapport par district',
    desc: 'Suivi par district sanitaire : voyageurs, visites, alertes.',
    icon: <Building2 />, tone: 'emerald', formats: ['pdf', 'csv'],
    filters: [],
  },
  {
    key: 'by_entry_point',
    title: 'Par point d\'entrée',
    desc: 'Activité agrégée par aéroport, port et frontière terrestre.',
    icon: <Globe2 />, tone: 'emerald', formats: ['pdf', 'csv'],
    filters: [],
  },
  {
    key: 'agents',
    title: 'Activité agents terrain',
    desc: 'Visites, alertes traitées, présence par équipe.',
    icon: <Users />, tone: 'slate', formats: ['pdf', 'csv'],
    filters: [],
  },
];

const TONE_BG: Record<Tone, string> = {
  orange: 'from-orange-50 to-amber-50 border-orange-200/60',
  emerald: 'from-emerald-50 to-teal-50 border-emerald-200/60',
  rose: 'from-rose-50 to-pink-50 border-rose-200/60',
  amber: 'from-amber-50 to-yellow-50 border-amber-200/60',
  slate: 'from-slate-50 to-gray-50 border-slate-200/60',
  sky: 'from-sky-50 to-blue-50 border-sky-200/60',
  dark: 'from-slate-100 to-slate-200 border-slate-300',
};
const TONE_TEXT: Record<Tone, string> = {
  orange: 'text-orange-700', emerald: 'text-emerald-700',
  rose: 'text-rose-700', amber: 'text-amber-700',
  slate: 'text-slate-700', sky: 'text-sky-700', dark: 'text-slate-900',
};

// =========================================================================
// Page principale
// =========================================================================
export default function RapportsPage() {
  const [openReport, setOpenReport] = useState<ReportDef | null>(null);

  return (
    <div className="space-y-6">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Exports & rapports
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Centre de rapports
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Générez et téléchargez les rapports opérationnels. CSV ouvrable directement dans
          Excel, PDF prêt à imprimer pour le comité de pilotage MSHPCMU / INHP.
        </p>
      </header>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {REPORTS.map((r, idx) => (
          <motion.article
            key={r.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: idx * 0.04 }}
            className={`p-5 rounded-2xl border bg-gradient-to-br ${TONE_BG[r.tone]} flex flex-col`}
          >
            <div
              className={`inline-flex items-center justify-center h-10 w-10 rounded-xl bg-white/70 dark:bg-slate-950/30 ${TONE_TEXT[r.tone]} mb-3`}
            >
              {r.icon}
            </div>
            <div className="flex items-center gap-2">
              <h3 className="font-display font-black text-ciDark dark:text-emerald-100">{r.title}</h3>
              {!r.endpoint && (
                <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500 bg-white/70 rounded px-1.5 py-0.5">
                  Bientôt
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-5 flex-1">{r.desc}</p>
            <div className="mt-4 flex gap-2 flex-wrap">
              {r.endpoint ? (
                <button
                  type="button"
                  onClick={() => setOpenReport(r)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold hover:border-ciOrange transition"
                >
                  <Download className="h-3.5 w-3.5" /> Générer
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() =>
                    toast('Disponible dans une prochaine version. Pour un export ad-hoc, contactez l\'INHP.', {
                      icon: 'ℹ️',
                    })
                  }
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/60 border border-slate-200 text-xs font-semibold text-slate-500 cursor-not-allowed"
                >
                  Demander un export
                </button>
              )}
            </div>
          </motion.article>
        ))}
      </div>

      <div className="card p-4 bg-emerald-50/40 border-emerald-200 text-emerald-900 text-xs">
        <strong>Astuce :</strong> le CSV est encodé UTF-8 avec BOM et séparateur point-virgule
        — il s'ouvre directement dans Excel ou LibreOffice Calc avec les accents préservés.
        Le PDF est paginé A4 paysage avec en-tête CI vert/orange, prêt à imprimer ou archiver.
        {API_URL && (
          <span className="text-slate-500"> • Canal sécurisé : {API_URL}</span>
        )}
      </div>

      {openReport && (
        <ReportParamsModal report={openReport} onClose={() => setOpenReport(null)} />
      )}
    </div>
  );
}

// =========================================================================
// Modal de paramétrage et téléchargement
// =========================================================================
function ReportParamsModal({ report, onClose }: { report: ReportDef; onClose: () => void }) {
  // Période par défaut : 30 derniers jours
  const today = new Date();
  const ago = new Date();
  ago.setDate(ago.getDate() - 30);

  const [dateFrom, setDateFrom] = useState(ago.toISOString().slice(0, 10));
  const [dateTo, setDateTo] = useState(today.toISOString().slice(0, 10));

  const [diseases, setDiseases] = useState<{ id: number; name: string }[]>([]);
  const [entryPoints, setEntryPoints] = useState<{ id: number; name: string }[]>([]);
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<Fmt | null>(null);

  useEffect(() => {
    // Charge les listes pour les filtres si nécessaires
    const needs = report.filters;
    if (needs.includes('disease')) {
      api.get('/diseases/?page_size=50')
        .then((r) => setDiseases(r.data.results || r.data))
        .catch(() => {});
    }
    if (needs.includes('entry_point')) {
      api.get('/geo/entry-points/?page_size=100')
        .then((r) => setEntryPoints(r.data.results || r.data))
        .catch(() => {});
    }
  }, [report]);

  const setFilter = (key: string, v: string) => setFilterValues((p) => ({ ...p, [key]: v }));

  const download = async (fmt: Fmt) => {
    if (!report.endpoint) return;
    setBusy(fmt);
    try {
      const params: Record<string, string> = {
        // Renommé `output` pour éviter la collision avec le paramètre
        // `format` de DRF (URL_FORMAT_OVERRIDE) qui essaie de matcher un
        // renderer csv/pdf et provoque un 404 si aucun n'est déclaré.
        // Le backend accepte aussi `format` en fallback pour la compat.
        output: fmt,
        date_from: dateFrom,
        date_to: dateTo,
      };
      for (const [k, v] of Object.entries(filterValues)) {
        if (v) params[k === 'qstatus' ? 'status' : k] = v;
      }
      const res = await api.get(report.endpoint, {
        params,
        responseType: 'blob',
      });

      // Extraction du filename depuis Content-Disposition (avec fallback)
      const cd = (res.headers['content-disposition'] || '') as string;
      const match = cd.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || `epitrace_${report.key}_${dateFrom}_${dateTo}.${fmt}`;

      const blob = new Blob([res.data], {
        type: fmt === 'pdf' ? 'application/pdf' : 'text/csv;charset=utf-8',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      toast.success(`Rapport ${fmt.toUpperCase()} téléchargé`);
      onClose();
    } catch (e: any) {
      // Si la réponse d'erreur est en blob, on tente d'extraire le message
      try {
        const txt = await e.response?.data?.text?.();
        toast.error(txt ? JSON.parse(txt).error?.message || txt : extractApiError(e));
      } catch {
        toast.error(extractApiError(e));
      }
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl mt-8 mb-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h2 className="font-display text-lg font-bold">{report.title}</h2>
            <p className="text-xs text-slate-500 mt-0.5">{report.desc}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-xl leading-none">
            ×
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Période */}
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Période</div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Du">
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="input-base"
                />
              </Field>
              <Field label="Au">
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="input-base"
                />
              </Field>
            </div>
          </div>

          {/* Filtres spécifiques */}
          {report.filters.length > 0 && (
            <div>
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Filtres</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {report.filters.includes('disease') && (
                  <Field label="Maladie">
                    <select value={filterValues.disease || ''} onChange={(e) => setFilter('disease', e.target.value)} className="input-base">
                      <option value="">Toutes</option>
                      {diseases.map((d) => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  </Field>
                )}
                {report.filters.includes('entry_point') && (
                  <Field label="Point d'entrée">
                    <select value={filterValues.entry_point || ''} onChange={(e) => setFilter('entry_point', e.target.value)} className="input-base">
                      <option value="">Tous</option>
                      {entryPoints.map((ep) => (
                        <option key={ep.id} value={ep.id}>{ep.name}</option>
                      ))}
                    </select>
                  </Field>
                )}
                {report.filters.includes('severity') && (
                  <Field label="Sévérité">
                    <select value={filterValues.severity || ''} onChange={(e) => setFilter('severity', e.target.value)} className="input-base">
                      <option value="">Toutes</option>
                      <option value="INFO">Info</option>
                      <option value="LOW">Faible</option>
                      <option value="MODERATE">Modérée</option>
                      <option value="HIGH">Élevée</option>
                      <option value="CRITICAL">Critique</option>
                    </select>
                  </Field>
                )}
                {report.filters.includes('status') && (
                  <Field label="Statut alerte">
                    <select value={filterValues.status || ''} onChange={(e) => setFilter('status', e.target.value)} className="input-base">
                      <option value="">Tous</option>
                      <option value="OPEN">Ouverte</option>
                      <option value="IN_PROGRESS">En cours</option>
                      <option value="RESOLVED">Résolue</option>
                      <option value="FALSE_POSITIVE">Faux positif</option>
                    </select>
                  </Field>
                )}
                {report.filters.includes('qstatus') && (
                  <Field label="Statut suivi">
                    <select value={filterValues.qstatus || ''} onChange={(e) => setFilter('qstatus', e.target.value)} className="input-base">
                      <option value="">Tous</option>
                      <option value="ACTIVE">Actif</option>
                      <option value="EXTENDED">Prolongé</option>
                      <option value="COMPLETED">Terminé</option>
                      <option value="CLOSED">Clôturé</option>
                    </select>
                  </Field>
                )}
                {report.filters.includes('transport_mode') && (
                  <Field label="Transport">
                    <select value={filterValues.transport_mode || ''} onChange={(e) => setFilter('transport_mode', e.target.value)} className="input-base">
                      <option value="">Tous</option>
                      <option value="plane">Avion</option>
                      <option value="boat">Bateau</option>
                      <option value="bus">Bus</option>
                      <option value="car">Voiture</option>
                      <option value="train">Train</option>
                      <option value="foot">À pied</option>
                    </select>
                  </Field>
                )}
                {report.filters.includes('alert_raised') && (
                  <Field label="Type de check-in">
                    <select value={filterValues.alert_raised || ''} onChange={(e) => setFilter('alert_raised', e.target.value)} className="input-base">
                      <option value="">Tous</option>
                      <option value="true">Avec alerte déclenchée</option>
                      <option value="false">Sans alerte</option>
                    </select>
                  </Field>
                )}
              </div>
            </div>
          )}

          {/* Boutons de téléchargement */}
          <div className="flex flex-wrap justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button onClick={onClose} className="btn-secondary">Annuler</button>
            {report.formats.includes('csv') && (
              <button
                onClick={() => download('csv')}
                disabled={busy !== null}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 text-white px-4 py-2 text-sm font-semibold hover:bg-slate-800 disabled:opacity-50"
              >
                <FileSpreadsheet className="h-4 w-4" /> {busy === 'csv' ? 'Génération...' : 'Télécharger CSV'}
              </button>
            )}
            {report.formats.includes('pdf') && (
              <button
                onClick={() => download('pdf')}
                disabled={busy !== null}
                className="inline-flex items-center gap-2 rounded-xl bg-rose-600 text-white px-4 py-2 text-sm font-semibold hover:bg-rose-700 disabled:opacity-50"
              >
                <FileText className="h-4 w-4" /> {busy === 'pdf' ? 'Génération...' : 'Télécharger PDF'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-500 mb-1">{label}</span>
      {children}
    </label>
  );
}
