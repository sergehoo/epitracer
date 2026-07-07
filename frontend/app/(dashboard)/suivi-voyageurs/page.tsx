'use client';

/**
 * Dashboard admin — Suivi des voyageurs accompagnés.
 *
 * - KPIs du jour
 * - Filtres recherche + check-in manqué
 * - Sélection multiple → envoi de message groupé (SMS / WhatsApp)
 * - Pagination client (20 par page)
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity, AlertTriangle, Bell, ChevronLeft, ChevronRight,
  Eye, MapPin, Search, Send, Users,
} from 'lucide-react';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { SendMessageModal, SendMessageTarget } from '@/components/notifications/SendMessageModal';
import { BulkSendMessageModal, BulkTarget } from '@/components/notifications/BulkSendMessageModal';

interface FollowupRow {
  public_id: string;
  full_name: string;
  phone: string;
  entry_point: string | null;
  arrival_date: string | null;
  confinement_city: string | null;
  confinement_commune: string | null;
  confinement_neighborhood: string | null;
  risk_level: 'low' | 'moderate' | 'high' | 'critical' | string | null;
  started_on: string;
  day_index: number;
  total_days: number;
  last_check_date: string | null;
  last_check_feeling: 'ok' | 'symptom' | 'assistance' | null;
  has_symptoms: boolean;
  last_location_at: string | null;
  current_health_status: string;
}

const RISK_OPTIONS: { value: string; label: string; tone: string }[] = [
  { value: '',         label: 'Tous niveaux',  tone: 'bg-slate-100 text-slate-700' },
  { value: 'critical', label: 'Critique',      tone: 'bg-rose-100 text-rose-700 ring-rose-300' },
  { value: 'high',     label: 'Élevé',         tone: 'bg-orange-100 text-orange-700 ring-orange-300' },
  { value: 'moderate', label: 'Modéré',        tone: 'bg-amber-100 text-amber-700 ring-amber-300' },
  { value: 'low',      label: 'Normal',        tone: 'bg-emerald-100 text-emerald-700 ring-emerald-300' },
];

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

const FEELING_LABELS: Record<string, string> = {
  ok: 'Tout va bien',
  symptom: 'Symptôme déclaré',
  assistance: 'Demande aide',
};

const PAGE_SIZE = 20;

export default function SuiviVoyageursPage() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [onlyMissed, setOnlyMissed] = useState(false);
  const [arrivalFrom, setArrivalFrom] = useState('');
  const [arrivalTo, setArrivalTo] = useState('');
  const [cityFilter, setCityFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [msgTarget, setMsgTarget] = useState<SendMessageTarget | null>(null);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<OverviewPayload>('/admin/companion/followups/');
      setData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Reset page + sélection quand les filtres changent
  useEffect(() => { setPage(1); }, [search, onlyMissed, arrivalFrom, arrivalTo, cityFilter, riskFilter]);

  // Liste unique des villes/communes/quartiers présents — pour le menu de filtre
  const cityOptions = useMemo(() => {
    if (!data) return [];
    const set = new Set<string>();
    data.rows.forEach((r) => {
      const key = [r.confinement_city, r.confinement_commune, r.confinement_neighborhood]
        .filter(Boolean)
        .join(' · ');
      if (key) set.add(key);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'fr'));
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    const fromTs = arrivalFrom ? new Date(arrivalFrom + 'T00:00:00').getTime() : null;
    const toTs = arrivalTo ? new Date(arrivalTo + 'T23:59:59').getTime() : null;
    return data.rows.filter((r) => {
      if (q) {
        const hay = `${r.public_id} ${r.full_name} ${r.entry_point ?? ''} ${r.phone ?? ''} ${r.confinement_city ?? ''} ${r.confinement_commune ?? ''} ${r.confinement_neighborhood ?? ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (onlyMissed) {
        if (!r.last_check_date) return true;
        const ageDays = (Date.now() - new Date(r.last_check_date).getTime()) / 86_400_000;
        if (ageDays < 2) return false;
      }
      // Filtre période d'arrivée
      if (fromTs || toTs) {
        if (!r.arrival_date) return false;
        const ts = new Date(r.arrival_date).getTime();
        if (fromTs && ts < fromTs) return false;
        if (toTs && ts > toTs) return false;
      }
      // Filtre ville/commune/quartier
      if (cityFilter) {
        const cityKey = [r.confinement_city, r.confinement_commune, r.confinement_neighborhood]
          .filter(Boolean)
          .join(' · ');
        if (cityKey !== cityFilter) return false;
      }
      // Filtre niveau de criticité
      if (riskFilter) {
        if ((r.risk_level || 'low').toLowerCase() !== riskFilter) return false;
      }
      return true;
    });
  }, [data, search, onlyMissed, arrivalFrom, arrivalTo, cityFilter, riskFilter]);

  const hasFilters = !!(search || onlyMissed || arrivalFrom || arrivalTo || cityFilter || riskFilter);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageRows = useMemo(
    () => filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [filtered, safePage],
  );

  const allPageSelected = pageRows.length > 0 && pageRows.every((r) => selected.has(r.public_id));
  const somePageSelected = pageRows.some((r) => selected.has(r.public_id));

  const togglePageSelection = () => {
    const next = new Set(selected);
    if (allPageSelected) {
      pageRows.forEach((r) => next.delete(r.public_id));
    } else {
      pageRows.forEach((r) => next.add(r.public_id));
    }
    setSelected(next);
  };

  const toggleRow = (publicId: string) => {
    const next = new Set(selected);
    next.has(publicId) ? next.delete(publicId) : next.add(publicId);
    setSelected(next);
  };

  const selectAllFiltered = () => {
    setSelected(new Set(filtered.map((r) => r.public_id)));
  };

  const clearSelection = () => setSelected(new Set());

  // Construit les cibles pour l'envoi groupé depuis la sélection
  const bulkTargets = useMemo<BulkTarget[]>(() => {
    if (!data) return [];
    return data.rows
      .filter((r) => selected.has(r.public_id))
      .map((r) => ({
        traveler_public_id: r.public_id,
        full_name: r.full_name,
        phone: r.phone,
        first_name: r.full_name?.split(' ')[0],
      }));
  }, [data, selected]);

  return (
    <div className="space-y-6">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Companion
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Suivi des voyageurs accompagnés
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Vue d'ensemble des voyageurs actuellement en période d'accompagnement sanitaire
          (21 jours). Les données de localisation sont consultées uniquement après
          consentement du voyageur ; chaque consultation est journalisée.
        </p>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Kpi icon={<Users className="h-5 w-5" />} label="Voyageurs actifs" value={data?.kpis.active ?? '—'} color="emerald" />
        <Kpi icon={<Bell className="h-5 w-5" />} label="Check-ins reçus aujourd'hui" value={data?.kpis.checked_today ?? '—'} color="emerald" />
        <Kpi icon={<AlertTriangle className="h-5 w-5" />} label="Manqués (>48h)" value={data?.kpis.missed_48h ?? '—'} color="amber" />
        <Kpi icon={<Activity className="h-5 w-5" />} label="Alertes ouvertes" value={data?.kpis.open_alerts ?? '—'} color="rose" />
        <Kpi icon={<MapPin className="h-5 w-5" />} label="Avec position (7j)" value={data?.kpis.with_recent_location ?? '—'} color="slate" />
      </div>

      {/* Filtres */}
      <div className="card p-4 space-y-3">
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
          <div className="relative flex-1">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              className="input pl-9"
              placeholder="Rechercher (ID, nom, point d'entrée, ville…)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <label className="inline-flex items-center gap-2 text-sm whitespace-nowrap">
            <input
              type="checkbox"
              checked={onlyMissed}
              onChange={(e) => setOnlyMissed(e.target.checked)}
            />
            Sans check-in depuis 48h
          </label>
        </div>

        {/* Ligne 2 — filtres avancés */}
        <div className="flex flex-wrap gap-3 items-center">
          {/* Période d'arrivée */}
          <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 dark:border-slate-700 px-2 py-1">
            <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold pl-1">
              Arrivée
            </span>
            <input
              type="date"
              value={arrivalFrom}
              max={arrivalTo || undefined}
              onChange={(e) => setArrivalFrom(e.target.value)}
              className="bg-transparent px-2 py-1 text-xs focus:outline-none"
              title="Date d'arrivée — début"
            />
            <span className="text-slate-400 text-xs">→</span>
            <input
              type="date"
              value={arrivalTo}
              min={arrivalFrom || undefined}
              onChange={(e) => setArrivalTo(e.target.value)}
              className="bg-transparent px-2 py-1 text-xs focus:outline-none"
              title="Date d'arrivée — fin"
            />
          </div>

          {/* Ville / commune de résidence en CI */}
          <select
            className="select max-w-[260px] text-sm"
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
          >
            <option value="">Toutes villes / quartiers</option>
            {cityOptions.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          {/* Niveau de criticité — pills */}
          <div className="inline-flex rounded-xl border border-slate-200 dark:border-slate-700 p-1">
            {RISK_OPTIONS.map((r) => (
              <button
                key={r.value || 'all'}
                type="button"
                onClick={() => setRiskFilter(r.value)}
                className={`px-3 py-1.5 text-xs rounded-lg font-bold transition ${
                  riskFilter === r.value
                    ? 'bg-ciDark text-white'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
                title={r.label}
              >
                {r.label}
              </button>
            ))}
          </div>

          {hasFilters && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                setOnlyMissed(false);
                setArrivalFrom('');
                setArrivalTo('');
                setCityFilter('');
                setRiskFilter('');
              }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              Réinitialiser
            </button>
          )}
        </div>
      </div>

      {/* Barre d'actions de sélection */}
      {selected.size > 0 && (
        <div className="card p-3 flex flex-wrap items-center justify-between gap-3 bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center justify-center h-7 w-7 rounded-full bg-emerald-600 text-white text-xs font-bold">
              {selected.size}
            </span>
            <span className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">
              voyageur(s) sélectionné(s)
            </span>
            <button
              type="button"
              onClick={selectAllFiltered}
              className="text-xs font-bold text-emerald-700 hover:underline"
            >
              Tout sélectionner ({filtered.length})
            </button>
            <button
              type="button"
              onClick={clearSelection}
              className="text-xs font-semibold text-slate-600 hover:underline"
            >
              Désélectionner
            </button>
          </div>
          <button
            type="button"
            onClick={() => setBulkOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-bold hover:bg-emerald-700"
          >
            <Send className="h-4 w-4" />
            Envoyer un message groupé
          </button>
        </div>
      )}

      {/* Tableau */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900 text-left">
              <tr>
                <th className="px-3 py-2 w-8">
                  <input
                    type="checkbox"
                    checked={allPageSelected}
                    ref={(el) => { if (el) el.indeterminate = !allPageSelected && somePageSelected; }}
                    onChange={togglePageSelection}
                    aria-label="Tout sélectionner sur cette page"
                  />
                </th>
                <Th>Voyageur</Th>
                <Th>Jour</Th>
                <Th>Dernier check-in</Th>
                <Th>État</Th>
                <Th>Point d'entrée</Th>
                <Th>Dernière position</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={8} className="p-6 text-center text-slate-400">Chargement…</td></tr>
              )}
              {!loading && error && (
                <tr><td colSpan={8} className="p-6 text-center text-rose-600">{error}</td></tr>
              )}
              {!loading && !error && pageRows.length === 0 && (
                <tr><td colSpan={8} className="p-8 text-center text-slate-400">Aucun voyageur ne correspond aux filtres.</td></tr>
              )}
              {pageRows.map((r) => {
                const isSelected = selected.has(r.public_id);
                return (
                <tr
                  key={r.public_id}
                  className={`border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 ${
                    isSelected ? 'bg-emerald-50/60 dark:bg-emerald-950/20' : ''
                  }`}
                >
                  <td className="px-3 py-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleRow(r.public_id)}
                      aria-label={`Sélectionner ${r.full_name}`}
                    />
                  </td>
                  <Td>
                    <Link
                      href={`/suivi-voyageurs/${r.public_id}`}
                      className="font-semibold hover:text-ciOrange transition"
                    >
                      {r.full_name}
                    </Link>
                    <div className="text-xs text-slate-500">{r.public_id} · {r.phone || '—'}</div>
                  </Td>
                  <Td>
                    <span className="px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold">
                      J{r.day_index + 1} / {r.total_days + 1}
                    </span>
                  </Td>
                  <Td>{r.last_check_date ? new Date(r.last_check_date).toLocaleDateString('fr-FR') : '—'}</Td>
                  <Td>
                    {r.last_check_feeling ? (
                      <span className={
                        r.last_check_feeling === 'assistance'
                          ? 'text-rose-700 font-semibold'
                          : r.last_check_feeling === 'symptom'
                          ? 'text-amber-700 font-semibold'
                          : 'text-emerald-700 font-semibold'
                      }>
                        {FEELING_LABELS[r.last_check_feeling]}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </Td>
                  <Td className="text-xs text-slate-600">{r.entry_point ?? '—'}</Td>
                  <Td className="text-xs text-slate-600">
                    {r.last_location_at ? formatDateTime(r.last_location_at) : '—'}
                  </Td>
                  <Td>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        href={`/suivi-voyageurs/${r.public_id}`}
                        className="inline-flex items-center gap-1 text-xs text-sky-700 hover:underline font-semibold"
                        title="Voir le détail du suivi"
                      >
                        <Eye className="h-3 w-3" /> Détail
                      </Link>
                      <Link
                        href={`/voyageurs/${r.public_id}/itineraire`}
                        className="text-xs text-ciOrange hover:underline font-semibold"
                      >
                        Itinéraire
                      </Link>
                      <button
                        type="button"
                        onClick={() => setMsgTarget({
                          traveler_public_id: r.public_id,
                          traveler_name: r.full_name,
                          phone: r.phone,
                          first_name: r.full_name?.split(' ')[0],
                        })}
                        title="Envoyer un message"
                        className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:underline font-semibold"
                      >
                        <Send className="h-3 w-3" /> Message
                      </button>
                    </div>
                  </Td>
                </tr>
              );})}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && !error && filtered.length > 0 && (
          <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 px-4 py-3 text-sm">
            <div className="text-xs text-slate-500">
              {filtered.length} voyageur(s) · page {safePage} / {totalPages}
              {selected.size > 0 && (
                <span className="ml-2 text-emerald-700 dark:text-emerald-400 font-semibold">
                  · {selected.size} sélectionné(s)
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={safePage === 1}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <ChevronLeft className="h-3.5 w-3.5" /> Préc.
              </button>
              {/* Numéros — limités à 5 visibles autour de la page courante */}
              {Array.from({ length: totalPages }).map((_, i) => {
                const num = i + 1;
                const showAlways = num === 1 || num === totalPages;
                const inWindow = Math.abs(num - safePage) <= 1;
                if (!showAlways && !inWindow) {
                  if (num === safePage - 2 || num === safePage + 2) {
                    return <span key={num} className="px-1 text-slate-400 text-xs">…</span>;
                  }
                  return null;
                }
                return (
                  <button
                    key={num}
                    onClick={() => setPage(num)}
                    className={`min-w-[32px] px-2 py-1 rounded-lg text-xs font-bold ${
                      num === safePage
                        ? 'bg-ciOrange text-white'
                        : 'border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    {num}
                  </button>
                );
              })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={safePage === totalPages}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Suiv. <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal envoi message individuel */}
      {msgTarget && (
        <SendMessageModal
          open={!!msgTarget}
          target={msgTarget}
          onClose={() => setMsgTarget(null)}
        />
      )}

      {/* Modal envoi groupé */}
      <BulkSendMessageModal
        open={bulkOpen}
        targets={bulkTargets}
        onClose={() => setBulkOpen(false)}
        onSent={(sent, failed) => {
          if (failed === 0) {
            // Tout est OK → on clear la sélection pour repartir propre
            setSelected(new Set());
          }
        }}
      />
    </div>
  );
}

function Kpi({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number | string; color: string }) {
  const colors: Record<string, string> = {
    emerald: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    amber: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    rose: 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300',
    slate: 'bg-slate-50 text-slate-700 dark:bg-slate-900 dark:text-slate-300',
  };
  return (
    <div className="card p-4">
      <div className={`inline-flex items-center justify-center h-10 w-10 rounded-xl mb-2 ${colors[color]}`}>
        {icon}
      </div>
      <div className="text-2xl font-display font-black text-ciDark dark:text-emerald-100">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-500">{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-3 ${className}`}>{children}</td>;
}
