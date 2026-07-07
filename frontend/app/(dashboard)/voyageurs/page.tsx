'use client';

/**
 * Liste paginée des voyageurs enregistrés.
 *
 * Consomme `GET /api/v1/travelers/` (TravelerViewSet) avec :
 *   - recherche libre (nom, public_id, téléphone, passeport, email)
 *   - filtres (statut santé, point d'entrée, date arrivée)
 *   - pagination DRF
 *
 * Actions par ligne : Détail (fiche complète), Itinéraire, Suivi médical, Message.
 */

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Users, Search, RefreshCcw, ChevronLeft, ChevronRight,
  Activity, MapPin, Send, Eye, Filter, X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import { SendMessageModal, type SendMessageTarget } from '@/components/notifications/SendMessageModal';

interface TravelerRow {
  id: number;
  public_id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  gender: string;
  nationality?: { code: string; name: string } | string | null;
  phone_mobile: string;
  whatsapp_phone?: string;
  email?: string;
  arrival_date: string | null;
  flight_number?: string;
  entry_point?: { id: number; name: string; code: string } | string | null;
  current_health_status: string;
  pass_number?: string;
  created_at: string;
}

interface ApiList {
  count: number;
  next: string | null;
  previous: string | null;
  results: TravelerRow[];
}

const HEALTH_STATUS_LABEL: Record<string, string> = {
  healthy: 'Sain',
  monitoring: 'Surveillance',
  suspect: 'Suspect',
  confirmed: 'Confirmé',
  recovered: 'Rétabli',
};

const HEALTH_STATUS_TONE: Record<string, string> = {
  healthy: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  monitoring: 'bg-sky-100 text-sky-800 border-sky-300',
  suspect: 'bg-amber-100 text-amber-800 border-amber-300',
  confirmed: 'bg-rose-100 text-rose-800 border-rose-300',
  recovered: 'bg-slate-100 text-slate-700 border-slate-300',
};

function unwrap(v: any, key = 'name'): string {
  if (!v) return '—';
  if (typeof v === 'string') return v;
  if (typeof v === 'object' && key in v) return v[key];
  return String(v);
}

export default function VoyageursListPage() {
  const [items, setItems] = useState<TravelerRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [healthFilter, setHealthFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [msgTarget, setMsgTarget] = useState<SendMessageTarget | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    const qs = new URLSearchParams();
    qs.set('page', String(page));
    qs.set('page_size', String(pageSize));
    if (search.trim()) qs.set('search', search.trim());
    if (healthFilter) qs.set('current_health_status', healthFilter);

    api.get<ApiList>(`/travelers/?${qs.toString()}`)
      .then((r) => {
        setItems(r.data.results ?? []);
        setTotalCount(r.data.count ?? 0);
      })
      .catch((e) => {
        const msg = extractApiError(e);
        setError(msg);
        toast.error(msg);
      })
      .finally(() => setLoading(false));
  };

  // Debounce recherche : 400ms
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); load(); }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, healthFilter]);

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [page]);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const stats = useMemo(() => {
    const byStatus: Record<string, number> = {};
    items.forEach((r) => {
      byStatus[r.current_health_status] = (byStatus[r.current_health_status] ?? 0) + 1;
    });
    return byStatus;
  }, [items]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Surveillance — voyageurs internationaux
          </span>
          <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100">
            Voyageurs
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
            Liste de tous les voyageurs enregistrés. Cliquez sur un nom pour ouvrir
            sa fiche complète, ou utilisez les actions de droite pour accéder à son
            suivi médical, son itinéraire ou lui envoyer un message.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40"
        >
          <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Actualiser
        </button>
      </header>

      {/* KPIs simples (sur la page courante) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Kpi label="Total filtré" value={totalCount} icon={<Users />} tone="emerald" />
        <Kpi label="Sain" value={stats.healthy ?? 0} icon={<Activity />} tone="emerald" />
        <Kpi label="Surveillance" value={stats.monitoring ?? 0} icon={<Activity />} tone="sky" />
        <Kpi label="Suspect" value={stats.suspect ?? 0} icon={<Activity />} tone="amber" />
        <Kpi label="Confirmé" value={stats.confirmed ?? 0} icon={<Activity />} tone="rose" />
      </div>

      {/* Filtres */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[220px]">
          <label className="block text-xs font-medium text-slate-500 mb-1">Recherche</label>
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Nom, public_id, téléphone, passeport, email…"
              className="w-full pl-9 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                aria-label="Effacer"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Statut santé</label>
          <select
            value={healthFilter}
            onChange={(e) => setHealthFilter(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="">Tous</option>
            <option value="healthy">Sain</option>
            <option value="monitoring">Surveillance</option>
            <option value="suspect">Suspect</option>
            <option value="confirmed">Confirmé</option>
            <option value="recovered">Rétabli</option>
          </select>
        </div>
        <div className="ml-auto text-xs text-slate-500 self-end">
          {totalCount} voyageur{totalCount > 1 ? 's' : ''} · page {page} / {totalPages}
        </div>
      </div>

      {error && (
        <div className="card p-6 text-rose-600 text-sm">{error}</div>
      )}

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800/40 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <Th>Voyageur</Th>
              <Th>Arrivée</Th>
              <Th>Point d'entrée</Th>
              <Th>Statut</Th>
              <Th>Pass</Th>
              <Th className="text-right">Actions</Th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className="p-10 text-center text-slate-400">Chargement…</td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={6} className="p-10 text-center text-slate-400">
                Aucun voyageur ne correspond aux filtres.
              </td></tr>
            )}
            {!loading && items.map((r) => {
              const name = r.full_name || `${r.first_name} ${r.last_name}`.trim();
              return (
                <tr key={r.public_id} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50/60 dark:hover:bg-slate-800/30">
                  <Td>
                    <Link
                      href={`/voyageurs/${r.public_id}`}
                      className="font-semibold text-slate-900 dark:text-slate-100 hover:text-ciOrange transition"
                    >
                      {name}
                    </Link>
                    <div className="text-xs text-slate-500">
                      {r.public_id} · {r.phone_mobile || '—'}
                    </div>
                  </Td>
                  <Td className="text-xs">
                    {r.arrival_date ? new Date(r.arrival_date).toLocaleDateString('fr-FR') : '—'}
                    {r.flight_number && <div className="text-slate-400">{r.flight_number}</div>}
                  </Td>
                  <Td className="text-xs">{unwrap(r.entry_point)}</Td>
                  <Td>
                    <span className={`px-2 py-1 rounded-md text-xs font-bold border ${
                      HEALTH_STATUS_TONE[r.current_health_status] ?? HEALTH_STATUS_TONE.healthy
                    }`}>
                      {HEALTH_STATUS_LABEL[r.current_health_status] ?? r.current_health_status}
                    </span>
                  </Td>
                  <Td className="text-xs font-mono text-slate-600">
                    {r.pass_number ?? '—'}
                  </Td>
                  <Td>
                    <div className="flex items-center justify-end gap-2 flex-wrap">
                      <Link
                        href={`/voyageurs/${r.public_id}`}
                        className="inline-flex items-center gap-1 text-xs text-sky-700 hover:underline font-semibold"
                        title="Voir la fiche complète"
                      >
                        <Eye className="h-3 w-3" /> Détail
                      </Link>
                      <Link
                        href={`/suivi-voyageurs/${r.public_id}`}
                        className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:underline font-semibold"
                        title="Voir le suivi médical"
                      >
                        <Activity className="h-3 w-3" /> Suivi
                      </Link>
                      <Link
                        href={`/voyageurs/${r.public_id}/itineraire`}
                        className="inline-flex items-center gap-1 text-xs text-ciOrange hover:underline font-semibold"
                        title="Itinéraire et contacts"
                      >
                        <MapPin className="h-3 w-3" /> Itinéraire
                      </Link>
                      <button
                        type="button"
                        onClick={() => setMsgTarget({
                          traveler_id: r.id,
                          traveler_public_id: r.public_id,
                          traveler_name: name,
                          phone: r.whatsapp_phone || r.phone_mobile || '',
                          email: r.email || '',
                          first_name: r.first_name,
                        })}
                        title="Envoyer un message"
                        className="inline-flex items-center gap-1 text-xs text-slate-700 hover:text-emerald-600 font-semibold"
                      >
                        <Send className="h-3 w-3" /> Message
                      </button>
                    </div>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* Pagination */}
        {!loading && totalCount > pageSize && (
          <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 px-4 py-3 text-sm">
            <div className="text-xs text-slate-500">
              Page {page} sur {totalPages}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <ChevronLeft className="h-3.5 w-3.5" /> Préc.
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Suiv. <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modale message */}
      {msgTarget && (
        <SendMessageModal
          target={msgTarget}
          open={!!msgTarget}
          onClose={() => setMsgTarget(null)}
        />
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Sous-composants                                                             */
/* -------------------------------------------------------------------------- */

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`text-left px-4 py-2 font-semibold ${className}`}>{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-3 align-top ${className}`}>{children}</td>;
}

function Kpi({
  label, value, icon, tone,
}: {
  label: string; value: number; icon: React.ReactNode;
  tone: 'emerald' | 'sky' | 'amber' | 'rose' | 'slate';
}) {
  const tones = {
    emerald: 'from-emerald-50 to-teal-50 text-emerald-700 border-emerald-200/60',
    sky: 'from-sky-50 to-blue-50 text-sky-700 border-sky-200/60',
    amber: 'from-amber-50 to-orange-50 text-amber-700 border-amber-200/60',
    rose: 'from-rose-50 to-pink-50 text-rose-700 border-rose-200/60',
    slate: 'from-slate-50 to-gray-50 text-slate-700 border-slate-200/60',
  } as const;
  return (
    <div className={`p-3 rounded-2xl border bg-gradient-to-br ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide font-bold opacity-80">{label}</span>
        <span className="opacity-50">{icon}</span>
      </div>
      <div className="mt-1 font-display text-2xl font-black tabular-nums">{value}</div>
    </div>
  );
}
