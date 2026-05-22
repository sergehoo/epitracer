'use client';

/**
 * /dashboard/checkins — Centre des check-ins sanitaires.
 *
 * Vue agrégée des DailyCheck (apps.quarantine) avec focus sur :
 * - check-ins reçus aujourd'hui (par feeling)
 * - répartition des symptômes signalés
 * - tableau filtrable par jour + symptômes
 *
 * Réutilise l'endpoint /admin/companion/followups/ qui expose déjà les
 * voyageurs en suivi actif avec leur dernier check-in.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Bell, CheckCircle2, MessageCircleQuestion, ThermometerSun, AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface FollowupRow {
  public_id: string;
  full_name: string;
  phone: string;
  entry_point: string | null;
  day_index: number;
  total_days: number;
  last_check_date: string | null;
  last_check_feeling: 'ok' | 'symptom' | 'assistance' | null;
  has_symptoms: boolean;
  last_location_at: string | null;
}

interface OverviewPayload {
  kpis: {
    active: number;
    checked_today: number;
    missed_48h: number;
    open_alerts: number;
    with_recent_location: number;
  };
  rows: FollowupRow[];
}

export default function CheckinsPage() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'ok' | 'symptom' | 'assistance' | 'missed'>('all');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<OverviewPayload>('/admin/companion/followups/');
      setData(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Compteurs par feeling (sur les rows du jour)
  const stats = useMemo(() => {
    if (!data) return { ok: 0, symptom: 0, assistance: 0, missed: 0 };
    const today = new Date().toISOString().slice(0, 10);
    return data.rows.reduce(
      (acc, r) => {
        if (r.last_check_date === today) {
          if (r.last_check_feeling === 'ok') acc.ok += 1;
          else if (r.last_check_feeling === 'symptom') acc.symptom += 1;
          else if (r.last_check_feeling === 'assistance') acc.assistance += 1;
        } else if (!r.last_check_date) {
          acc.missed += 1;
        } else {
          const days = (Date.now() - new Date(r.last_check_date).getTime()) / 86_400_000;
          if (days >= 2) acc.missed += 1;
        }
        return acc;
      },
      { ok: 0, symptom: 0, assistance: 0, missed: 0 },
    );
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    if (filter === 'all') return data.rows;
    const today = new Date().toISOString().slice(0, 10);
    return data.rows.filter((r) => {
      if (filter === 'missed') {
        if (!r.last_check_date) return true;
        return (Date.now() - new Date(r.last_check_date).getTime()) / 86_400_000 >= 2;
      }
      return r.last_check_date === today && r.last_check_feeling === filter;
    });
  }, [data, filter]);

  return (
    <div className="space-y-6">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Companion
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Centre des check-ins
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Aperçu des messages reçus aujourd'hui par les voyageurs en accompagnement.
          Cliquez sur une catégorie pour filtrer la liste.
        </p>
      </header>

      {/* Tuiles cliquables */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Tile icon={<CheckCircle2 />} label="Je vais bien" value={stats.ok}
          active={filter === 'ok'} tone="emerald"
          onClick={() => setFilter(filter === 'ok' ? 'all' : 'ok')} />
        <Tile icon={<ThermometerSun />} label="Symptôme déclaré" value={stats.symptom}
          active={filter === 'symptom'} tone="amber"
          onClick={() => setFilter(filter === 'symptom' ? 'all' : 'symptom')} />
        <Tile icon={<MessageCircleQuestion />} label="Assistance demandée" value={stats.assistance}
          active={filter === 'assistance'} tone="rose"
          onClick={() => setFilter(filter === 'assistance' ? 'all' : 'assistance')} />
        <Tile icon={<AlertCircle />} label="Manqués > 48h" value={stats.missed}
          active={filter === 'missed'} tone="slate"
          onClick={() => setFilter(filter === 'missed' ? 'all' : 'missed')} />
      </div>

      {/* Tableau */}
      <div className="card overflow-hidden">
        <header className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="font-semibold text-sm">
            {filter === 'all' ? 'Tous les voyageurs en suivi' : `Filtre : ${filter}`}
            <span className="text-slate-400 ml-2">({filtered.length})</span>
          </div>
          {filter !== 'all' && (
            <button onClick={() => setFilter('all')} className="text-xs text-ciOrange hover:underline">
              Effacer le filtre
            </button>
          )}
        </header>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-left">
              <tr>
                <Th>Voyageur</Th>
                <Th>Jour</Th>
                <Th>Check-in</Th>
                <Th>État</Th>
                <Th>Position</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={6} className="p-6 text-center text-slate-400">Chargement…</td></tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={6} className="p-8 text-center text-slate-400">Aucune ligne.</td></tr>
              )}
              {filtered.map((r) => (
                <tr key={r.public_id}
                    className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50">
                  <Td>
                    <div className="font-semibold">{r.full_name}</div>
                    <div className="text-xs text-slate-500">{r.public_id} · {r.phone || '—'}</div>
                  </Td>
                  <Td>
                    <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-xs font-bold">
                      J{r.day_index + 1}/{r.total_days + 1}
                    </span>
                  </Td>
                  <Td className="text-xs text-slate-600">
                    {r.last_check_date
                      ? new Date(r.last_check_date).toLocaleDateString('fr-FR')
                      : <span className="text-rose-700 font-semibold">aucun</span>}
                  </Td>
                  <Td>
                    <FeelingPill feeling={r.last_check_feeling} hasSymptoms={r.has_symptoms} />
                  </Td>
                  <Td className="text-xs text-slate-600">
                    {r.last_location_at ? formatDateTime(r.last_location_at) : '—'}
                  </Td>
                  <Td>
                    <Link href={`/voyageurs/${r.public_id}/itineraire`}
                          className="text-xs text-ciOrange hover:underline font-semibold">
                      Itinéraire →
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function FeelingPill({ feeling, hasSymptoms }: { feeling: string | null; hasSymptoms: boolean }) {
  if (!feeling) return <span className="text-slate-400 text-xs">—</span>;
  if (feeling === 'assistance') {
    return <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-700 text-xs font-bold">Aide demandée</span>;
  }
  if (feeling === 'symptom' || hasSymptoms) {
    return <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-700 text-xs font-bold">Symptôme</span>;
  }
  return <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 text-xs font-bold">OK</span>;
}

interface TileProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  active: boolean;
  tone: 'emerald' | 'amber' | 'rose' | 'slate';
  onClick: () => void;
}

const TONE: Record<TileProps['tone'], string> = {
  emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  amber: 'bg-amber-50 border-amber-200 text-amber-700',
  rose: 'bg-rose-50 border-rose-200 text-rose-700',
  slate: 'bg-slate-50 border-slate-200 text-slate-700',
};

function Tile({ icon, label, value, active, tone, onClick }: TileProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.98 }}
      className={`p-4 rounded-2xl border text-left transition ${TONE[tone]} ${
        active ? 'ring-2 ring-offset-2 ring-ciOrange shadow-lg' : 'hover:shadow-md'
      }`}
    >
      <div className="h-8 w-8 rounded-lg bg-white/70 grid place-items-center mb-2">
        {icon}
      </div>
      <div className="font-display text-2xl font-black">{value}</div>
      <div className="text-xs font-semibold mt-1">{label}</div>
    </motion.button>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-500">{children}</th>;
}
function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-3 ${className}`}>{children}</td>;
}
