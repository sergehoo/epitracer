'use client';

/**
 * /dashboard/rapports — Centre de rapports opérationnels.
 *
 * Page d'entrée pour les exports / impressions. Les rapports listés sont
 * conceptuels pour l'instant ; chaque carte ouvrira son endpoint dédié
 * lorsque les générateurs PDF/Excel seront implémentés côté backend
 * (Celery + reportlab/openpyxl).
 *
 * Le bouton "Télécharger" est cliquable pour ceux dont l'endpoint existe
 * déjà ; les autres affichent un toast informatif.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import {
  Activity, AlertTriangle, BarChart3, Building2, CalendarDays, Download,
  FileSpreadsheet, FileText, Globe2, HeartPulse, Stethoscope, Users,
} from 'lucide-react';
import { API_URL } from '@/lib/api';

interface ReportDef {
  id: string;
  title: string;
  desc: string;
  icon: React.ReactNode;
  formats: ('pdf' | 'xlsx' | 'csv')[];
  href?: string; // si défini → vrai téléchargement
  tone: 'orange' | 'emerald' | 'rose' | 'amber' | 'slate';
}

const REPORTS: ReportDef[] = [
  {
    id: 'daily',
    title: 'Rapport journalier',
    desc: 'Synthèse des arrivées, check-ins et alertes des dernières 24 heures.',
    icon: <CalendarDays />, formats: ['pdf', 'xlsx'], tone: 'orange',
  },
  {
    id: 'weekly',
    title: 'Rapport hebdomadaire',
    desc: 'Indicateurs hebdomadaires consolidés (par maladie, point d\'entrée, district).',
    icon: <BarChart3 />, formats: ['pdf', 'xlsx'], tone: 'orange',
  },
  {
    id: 'by_disease',
    title: 'Rapport par maladie',
    desc: 'Volumes, alertes et niveau de risque par maladie suivie.',
    icon: <Stethoscope />, formats: ['pdf', 'xlsx', 'csv'], tone: 'emerald',
  },
  {
    id: 'by_entry_point',
    title: 'Rapport par point d\'entrée',
    desc: 'Activité agrégée par aéroport, port et frontière terrestre.',
    icon: <Globe2 />, formats: ['pdf', 'xlsx'], tone: 'emerald',
  },
  {
    id: 'by_district',
    title: 'Rapport par district sanitaire',
    desc: 'Suivi par district : voyageurs, visites terrain, alertes ouvertes.',
    icon: <Building2 />, formats: ['pdf', 'xlsx'], tone: 'emerald',
  },
  {
    id: 'alerts',
    title: 'Rapport des alertes',
    desc: 'Détail des alertes sanitaires, traitement et délais de résolution.',
    icon: <AlertTriangle />, formats: ['pdf', 'csv'], tone: 'rose',
  },
  {
    id: 'followup_21d',
    title: 'Rapport suivi 21 jours',
    desc: 'Check-ins, taux de complétion, manqués, fin de période.',
    icon: <HeartPulse />, formats: ['pdf', 'xlsx'], tone: 'amber',
  },
  {
    id: 'high_risk',
    title: 'Voyageurs à risque élevé',
    desc: 'Liste nominative des voyageurs actuellement classés HIGH ou CRITICAL.',
    icon: <Activity />, formats: ['pdf', 'csv'], tone: 'rose',
  },
  {
    id: 'agents',
    title: 'Rapport agents terrain',
    desc: 'Activité des équipes : visites, alertes traitées, présence.',
    icon: <Users />, formats: ['pdf', 'xlsx'], tone: 'slate',
  },
];

const TONE_BG: Record<ReportDef['tone'], string> = {
  orange: 'from-orange-50 to-amber-50 border-orange-200/60',
  emerald: 'from-emerald-50 to-teal-50 border-emerald-200/60',
  rose: 'from-rose-50 to-pink-50 border-rose-200/60',
  amber: 'from-amber-50 to-yellow-50 border-amber-200/60',
  slate: 'from-slate-50 to-gray-50 border-slate-200/60',
};
const TONE_TEXT: Record<ReportDef['tone'], string> = {
  orange: 'text-orange-700', emerald: 'text-emerald-700',
  rose: 'text-rose-700', amber: 'text-amber-700', slate: 'text-slate-700',
};

export default function RapportsPage() {
  const [generating, setGenerating] = useState<string | null>(null);

  const handleDownload = async (report: ReportDef, format: string) => {
    if (!report.href) {
      toast('Ce rapport sera disponible dans une prochaine version. Contactez l\'INHP pour un export sur mesure.',
            { icon: 'ℹ️' });
      return;
    }
    setGenerating(`${report.id}-${format}`);
    try {
      window.open(`${report.href}?format=${format}`, '_blank', 'noopener');
    } finally {
      setTimeout(() => setGenerating(null), 1500);
    }
  };

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
          Générez et téléchargez les rapports opérationnels. Les rapports sont disponibles
          en PDF (rapport mis en page), Excel (données analysables) et CSV (intégration).
        </p>
      </header>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {REPORTS.map((r, idx) => (
          <motion.article
            key={r.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: idx * 0.04 }}
            className={`p-5 rounded-2xl border bg-gradient-to-br ${TONE_BG[r.tone]} flex flex-col`}
          >
            <div className={`inline-flex items-center justify-center h-10 w-10 rounded-xl bg-white/70 dark:bg-slate-950/30 ${TONE_TEXT[r.tone]} mb-3`}>
              {r.icon}
            </div>
            <h3 className="font-display font-black text-ciDark dark:text-emerald-100">{r.title}</h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-5 flex-1">{r.desc}</p>
            <div className="mt-4 flex gap-2 flex-wrap">
              {r.formats.includes('pdf') && (
                <button
                  type="button"
                  disabled={generating === `${r.id}-pdf`}
                  onClick={() => handleDownload(r, 'pdf')}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold hover:border-ciOrange disabled:opacity-50"
                >
                  <FileText className="h-3.5 w-3.5" /> PDF
                </button>
              )}
              {r.formats.includes('xlsx') && (
                <button
                  type="button"
                  disabled={generating === `${r.id}-xlsx`}
                  onClick={() => handleDownload(r, 'xlsx')}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold hover:border-emerald-500 disabled:opacity-50"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" /> Excel
                </button>
              )}
              {r.formats.includes('csv') && (
                <button
                  type="button"
                  disabled={generating === `${r.id}-csv`}
                  onClick={() => handleDownload(r, 'csv')}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold hover:border-slate-500 disabled:opacity-50"
                >
                  <Download className="h-3.5 w-3.5" /> CSV
                </button>
              )}
            </div>
          </motion.article>
        ))}
      </div>

      <div className="card p-4 bg-emerald-50/40 border-emerald-200 text-emerald-900 text-xs">
        <strong>Génération automatique :</strong> les rapports journaliers et hebdomadaires
        peuvent être programmés par l'équipe INHP via Celery Beat pour un envoi par email
        au comité de pilotage. Contactez votre administrateur national pour activer cette
        option. Le canal {API_URL ? `(${API_URL})` : ''} est sécurisé par token signé.
      </div>
    </div>
  );
}
