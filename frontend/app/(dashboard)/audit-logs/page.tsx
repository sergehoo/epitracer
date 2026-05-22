'use client';

/**
 * /dashboard/audit-logs — Journaux d'accès aux données sensibles.
 *
 * Vue unifiée des :
 * - DataAccessLog (apps.companion) : consultations de localisations / contacts
 *   par les agents, avec motif et IP.
 * - AuditLog (apps.audit, si dispo) : autres événements d'audit.
 *
 * Pour le moment on alimente uniquement depuis companion.DataAccessLog
 * via /admin/companion/travelers/<id>/access-log/ qui retourne aussi
 * l'historique global si appelé sans id (à étendre si besoin).
 *
 * Réservé NATIONAL_ADMIN / MINISTRY / INHP (RBAC côté API).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, ShieldAlert, Eye, FileText } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

interface AccessRow {
  accessed_at: string;
  accessed_by: string;
  role: string;
  resource: string;
  reason: string;
  ip_address: string | null;
}

interface SearchPayload {
  traveler: { public_id: string };
  count: number;
  rows: AccessRow[];
}

export default function AuditLogsPage() {
  const [travelerId, setTravelerId] = useState<string>('');
  const [data, setData] = useState<SearchPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<SearchPayload>(
        `/admin/companion/travelers/${id.toUpperCase()}/access-log/`,
      );
      setData(data);
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        setError("Vous n'avez pas le droit de consulter ces journaux. Demandez l'accès à un administrateur national.");
      } else if (status === 404) {
        setError("Voyageur introuvable.");
      } else {
        setError(e instanceof Error ? e.message : "Erreur de chargement");
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    load(travelerId.trim());
  };

  const grouped = useMemo(() => {
    if (!data) return {};
    return data.rows.reduce<Record<string, AccessRow[]>>((acc, r) => {
      const key = r.resource;
      (acc[key] = acc[key] || []).push(r);
      return acc;
    }, {});
  }, [data]);

  return (
    <div className="space-y-6">
      <header>
        <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
          Sécurité & audit
        </span>
        <h1 className="font-display text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100 mt-1">
          Journaux d'accès aux données
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-3xl mt-1">
          Chaque consultation de localisation, contact ou pièce d'identité d'un voyageur
          est tracée ici. Cette page est réservée aux administrateurs nationaux et à l'INHP.
        </p>
      </header>

      <form onSubmit={submit} className="card p-4 flex items-center gap-3">
        <Search className="h-4 w-4 text-slate-400" />
        <input
          className="input flex-1 max-w-md"
          placeholder="Saisir l'identifiant voyageur (TRV-XXXXXXX)…"
          value={travelerId}
          onChange={(e) => setTravelerId(e.target.value)}
        />
        <button type="submit" className="btn-primary text-sm" disabled={loading || !travelerId.trim()}>
          Consulter
        </button>
      </form>

      {error && (
        <div className="card p-4 bg-rose-50 border-rose-200 text-rose-700 text-sm flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" /> {error}
        </div>
      )}

      {data && (
        <>
          <div className="card p-4">
            <div className="text-sm font-semibold">
              {data.count} consultation{data.count > 1 ? 's' : ''} pour <span className="text-ciOrange">{data.traveler.public_id}</span>
            </div>
          </div>

          {Object.entries(grouped).map(([resource, rows]) => (
            <section key={resource} className="card overflow-hidden">
              <header className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
                <Eye className="h-4 w-4 text-emerald-600" />
                <span className="font-semibold text-sm capitalize">{resource}</span>
                <span className="text-xs text-slate-400">({rows.length})</span>
              </header>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 dark:bg-slate-900 text-left">
                    <tr>
                      <Th>Date</Th>
                      <Th>Agent</Th>
                      <Th>Rôle</Th>
                      <Th>Motif</Th>
                      <Th>IP</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={i} className="border-t border-slate-100 dark:border-slate-800">
                        <Td className="text-xs text-slate-600">{formatDateTime(r.accessed_at)}</Td>
                        <Td>{r.accessed_by || '—'}</Td>
                        <Td><span className="text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">{r.role || '—'}</span></Td>
                        <Td className="text-xs text-slate-600">{r.reason || '—'}</Td>
                        <Td className="text-xs text-slate-500 font-mono">{r.ip_address || '—'}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </>
      )}

      <div className="card p-4 bg-amber-50 border-amber-200 text-amber-900 text-xs flex items-start gap-2">
        <FileText className="h-4 w-4 mt-0.5 shrink-0" />
        <p>
          Pour un export complet ou un audit forensique (toutes consultations sur une période,
          tentatives d'accès refusées, exports massifs), contactez l'équipe sécurité MSHPCMU.
          Les données sont conservées 5 ans conformément aux obligations légales.
        </p>
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-500">{children}</th>;
}
function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-3 ${className}`}>{children}</td>;
}
