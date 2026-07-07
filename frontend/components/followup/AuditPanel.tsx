'use client';

/**
 * AuditPanel — Phase 9F.
 *
 * Timeline unifiée des actions + accès données sensibles pour un cas
 * de suivi. La consultation exige un motif (RGPD).
 *
 * GET /api/v1/admin/followups/{travelerId}/audit/?reason=…
 *   → { results: AuditItem[], count, reason }
 *
 * Filtres locaux : type (action/access), agent, période (7j / 30j / tout).
 */

import { useEffect, useMemo, useState } from 'react';
import {
  ClipboardList, Filter, Loader2, RefreshCcw,
  User as UserIcon, ShieldCheck, Activity,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';

interface AuditItem {
  type: 'action' | 'access' | string;
  id: number;
  timestamp: string;
  actor_id: number | null;
  actor_name: string;
  label: string;
  details: Record<string, unknown>;
}

interface Props {
  travelerId: string;
}

type Period = '7' | '30' | 'all';

const TYPE_TONE: Record<string, string> = {
  action: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  access: 'bg-amber-100 text-amber-800 border-amber-200',
};

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

export function AuditPanel({ travelerId }: Props) {
  const [reason, setReason] = useState('Audit suivi médical');
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<AuditItem[] | null>(null);

  // Filtres
  const [filterType, setFilterType] = useState<'all' | 'action' | 'access'>('all');
  const [filterActor, setFilterActor] = useState<string>('all');
  const [filterPeriod, setFilterPeriod] = useState<Period>('30');

  const load = async () => {
    const r = reason.trim();
    if (!r) {
      toast.error('Un motif de consultation est requis.');
      return;
    }
    setLoading(true);
    try {
      const resp = await api.get<{ results: AuditItem[]; count: number }>(
        `/admin/followups/${travelerId}/audit/`,
        { params: { reason: r } },
      );
      setItems(resp.data?.results ?? []);
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setLoading(false);
    }
  };

  // Charge automatiquement la première fois si aucun fetch initial.
  // (le bouton "Recharger" permet d'actualiser ensuite)
  useEffect(() => {
    if (items === null && !loading) {
      // Démarrage différé pour laisser au user le contrôle de la raison
      // → on ne fetch PAS automatiquement, conformément aux exigences RGPD.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const actorOptions = useMemo(() => {
    if (!items) return [];
    const set = new Set<string>();
    for (const it of items) set.add(it.actor_name || '—');
    return Array.from(set).sort();
  }, [items]);

  const filtered = useMemo(() => {
    if (!items) return [];
    const periodMs = filterPeriod === 'all'
      ? Infinity
      : Number(filterPeriod) * 86_400_000;
    const cutoff = Date.now() - periodMs;
    return items.filter((it) => {
      if (filterType !== 'all' && it.type !== filterType) return false;
      if (filterActor !== 'all' && (it.actor_name || '—') !== filterActor) return false;
      if (periodMs !== Infinity) {
        try {
          const ts = new Date(it.timestamp).getTime();
          if (ts < cutoff) return false;
        } catch {
          /* keep */
        }
      }
      return true;
    });
  }, [items, filterType, filterActor, filterPeriod]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-violet-600" />
            <h2 className="font-display text-lg font-black text-ciDark">Audit & traçabilité</h2>
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Historique unifié des actions médicales et des accès aux données.
          </div>
        </div>
      </header>

      {/* Bloc raison + bouton charger */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 flex flex-wrap items-end gap-2 mb-4">
        <div className="flex-1 min-w-[200px]">
          <label className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1 block">
            Motif de la consultation (obligatoire — RGPD)
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={200}
            placeholder="Ex. Audit suivi médical"
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-violet-500 focus:ring-violet-500 outline-none"
          />
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading || !reason.trim()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 text-white px-3 py-1.5 text-xs font-bold hover:bg-violet-700 disabled:opacity-50"
        >
          {loading ? (
            <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Chargement…</>
          ) : items === null ? (
            <>Charger l'audit</>
          ) : (
            <><RefreshCcw className="h-3.5 w-3.5" /> Recharger</>
          )}
        </button>
      </div>

      {/* Filtres */}
      {items !== null && items.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-3 text-xs">
          <Filter className="h-3.5 w-3.5 text-slate-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as 'all' | 'action' | 'access')}
            className="rounded-lg border border-slate-200 px-2 py-1 text-xs"
          >
            <option value="all">Tous types</option>
            <option value="action">Actions</option>
            <option value="access">Accès</option>
          </select>
          <select
            value={filterActor}
            onChange={(e) => setFilterActor(e.target.value)}
            className="rounded-lg border border-slate-200 px-2 py-1 text-xs"
          >
            <option value="all">Tous agents</option>
            {actorOptions.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
          <select
            value={filterPeriod}
            onChange={(e) => setFilterPeriod(e.target.value as Period)}
            className="rounded-lg border border-slate-200 px-2 py-1 text-xs"
          >
            <option value="7">7 jours</option>
            <option value="30">30 jours</option>
            <option value="all">Tout l'historique</option>
          </select>
          <span className="ml-auto text-[11px] text-slate-500">
            {filtered.length} / {items.length} entrée(s)
          </span>
        </div>
      )}

      {/* Liste / états */}
      {items === null ? (
        <div className="py-8 text-center text-slate-400 text-sm">
          Saisissez une raison puis cliquez sur «&nbsp;Charger l'audit&nbsp;».
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-sm">
          Aucune entrée pour les filtres sélectionnés.
        </div>
      ) : (
        <ul className="space-y-2">
          {filtered.map((it) => {
            const tone = TYPE_TONE[it.type] ?? TYPE_TONE.action;
            const icon = it.type === 'access'
              ? <ShieldCheck className="h-3 w-3" />
              : <Activity className="h-3 w-3" />;
            const details = it.details || {};
            return (
              <li
                key={`${it.type}-${it.id}`}
                className="rounded-xl border border-slate-200 bg-white p-3"
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase ${tone}`}>
                        {icon} {it.type}
                      </span>
                      <span className="font-bold text-slate-800 text-sm">{it.label}</span>
                    </div>
                    <div className="mt-1 text-[11px] text-slate-500 flex flex-wrap gap-x-3 gap-y-0.5">
                      {it.type === 'action' && (details as { action_type?: string }).action_type && (
                        <span className="font-mono">
                          {String((details as { action_type?: string }).action_type)}
                        </span>
                      )}
                      {it.type === 'access' && (details as { resource?: string }).resource && (
                        <span className="font-mono">
                          {String((details as { resource?: string }).resource)}
                        </span>
                      )}
                      {(details as { description?: string }).description && (
                        <span className="text-slate-600 line-clamp-2">
                          {String((details as { description?: string }).description)}
                        </span>
                      )}
                      {(details as { reason?: string }).reason && (
                        <span className="italic">
                          motif : {String((details as { reason?: string }).reason)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-[10px] text-slate-500 text-right shrink-0">
                    <div className="inline-flex items-center gap-1">
                      <UserIcon className="h-3 w-3" /> {it.actor_name || '—'}
                    </div>
                    <div className="text-slate-400 mt-0.5">
                      {formatDateTime(it.timestamp)}
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default AuditPanel;
